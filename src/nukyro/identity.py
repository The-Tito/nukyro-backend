"""Verificación de tokens de identidad de Cognito (D-34, RF-074, RF-075).

La API solo acepta el token de identidad (`token_use=id`) firmado con RS256 por el emisor
configurado. Los motivos del rechazo se distinguen para las pruebas, pero la API los responde
todos igual: nunca se repite el token ni se dice qué falló.
"""

import json
import threading
import time
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass

import jwt
from jwt.algorithms import RSAAlgorithm

ALGORITHM = "RS256"  # ninguna otra: ni "none" ni HS*, que permitirían firmar con la clave pública
MAX_LIFETIME = 3600  # D-35: exp − iat de 1 hora o menos
MAX_AGE = 3600  # D-35: iat de hace menos de 1 hora
CLOCK_SKEW = 30  # tolerancia entre relojes, solo para un `iat` ligeramente futuro
MAX_TOKEN_LENGTH = 8192
ADMIN_GROUP = "admins"  # ADR-002 §7: quien administra no es participante
JWKS_REFRESH_MIN_INTERVAL = 60  # una clave desconocida no dispara más de una descarga por minuto
JWKS_TTL = 3600


class InvalidToken(Exception):
    """El token no es válido (firma, emisor, audiencia, tipo, vencimiento, edad o forma)."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


class WrongGroup(InvalidToken):
    """El token es válido, pero su grupo no corresponde a este uso."""


@dataclass(frozen=True)
class Identity:
    sub: str
    email: str | None
    email_verified: bool
    nickname: str | None
    groups: tuple[str, ...]
    issued_at: int


@dataclass(frozen=True)
class OidcSettings:
    issuer: str
    audience: str
    jwks_url: str


JwksProvider = Callable[[bool], dict]  # (forzar descarga) -> {"keys": [...]}


def fetch_jwks(url: str, timeout: float = 5.0) -> dict:
    with urllib.request.urlopen(url, timeout=timeout) as response:  # noqa: S310 (URL del operador)
        return json.load(response)


class JwksCache:
    """Claves públicas del emisor, con caducidad y una descarga mínima ante un `kid` nuevo."""

    def __init__(self, fetch: Callable[[], dict], clock: Callable[[], float] = time.time):
        self._fetch, self._clock = fetch, clock
        self._keys: dict | None = None
        self._loaded_at = 0.0
        self._lock = threading.Lock()

    def __call__(self, force: bool = False) -> dict:
        with self._lock:
            now = self._clock()
            expired = self._keys is None or now - self._loaded_at >= JWKS_TTL
            allowed = self._keys is None or now - self._loaded_at >= JWKS_REFRESH_MIN_INTERVAL
            if expired or (force and allowed):
                self._keys = self._fetch()
                self._loaded_at = now
            return self._keys


class OidcVerifier:
    def __init__(
        self,
        settings: OidcSettings,
        jwks: JwksProvider,
        clock: Callable[[], float] = time.time,
    ):
        self._settings, self._jwks, self._clock = settings, jwks, clock

    @classmethod
    def from_settings(cls, settings: OidcSettings) -> "OidcVerifier":
        cache = JwksCache(lambda: fetch_jwks(settings.jwks_url))
        return cls(settings, cache)

    def _key(self, kid: str):
        for force in (False, True):  # si el kid no está, se vuelve a pedir el conjunto una vez
            try:
                keys = self._jwks(force).get("keys", [])
            except Exception as exc:
                raise InvalidToken("jwks_unavailable") from exc
            for jwk in keys:
                if jwk.get("kid") == kid and jwk.get("kty") == "RSA":
                    try:
                        return RSAAlgorithm.from_jwk(json.dumps(jwk))
                    except Exception as exc:
                        raise InvalidToken("unknown_key") from exc
        raise InvalidToken("unknown_key")

    def verify(self, token: str, *, admin: bool = False) -> Identity:
        """Valida el token. Con `admin=False` rechaza a quien está en el grupo `admins`; con
        `admin=True` exige estar en él."""
        if not token or len(token) > MAX_TOKEN_LENGTH:
            raise InvalidToken("malformed")
        try:
            header = jwt.get_unverified_header(token)
        except jwt.PyJWTError as exc:
            raise InvalidToken("malformed") from exc
        # El algoritmo lo fija el servidor, nunca el encabezado del token
        if header.get("alg") != ALGORITHM:
            raise InvalidToken("algorithm")
        kid = header.get("kid")
        if not isinstance(kid, str) or not kid:
            raise InvalidToken("unknown_key")
        key = self._key(kid)
        now = self._clock()
        try:
            claims = jwt.decode(
                token,
                key,
                algorithms=[ALGORITHM],
                issuer=self._settings.issuer,
                audience=self._settings.audience,
                options={
                    "require": ["exp", "iat", "iss", "aud", "sub"],
                    "verify_exp": False,
                    "verify_iat": False,
                },
            )
        except jwt.InvalidSignatureError as exc:
            raise InvalidToken("signature") from exc
        except jwt.InvalidIssuerError as exc:
            raise InvalidToken("issuer") from exc
        except jwt.InvalidAudienceError as exc:
            raise InvalidToken("audience") from exc
        except jwt.PyJWTError as exc:
            raise InvalidToken("malformed") from exc
        # El vencimiento y la edad se comparan con el reloj inyectado (las pruebas lo mueven)
        exp, iat = claims["exp"], claims["iat"]
        if not all(isinstance(v, int | float) and not isinstance(v, bool) for v in (exp, iat)):
            raise InvalidToken("malformed")
        if claims.get("token_use") != "id":
            raise InvalidToken("token_use")
        if now >= exp:  # sin tolerancia: D-35 cuenta con que ningún token vive más de 1 hora
            raise InvalidToken("expired")
        if iat > now + CLOCK_SKEW:
            raise InvalidToken("issued_in_the_future")
        if now - iat >= MAX_AGE:  # D-35
            raise InvalidToken("too_old")
        if exp - iat > MAX_LIFETIME:  # D-35
            raise InvalidToken("lifetime")
        sub = claims["sub"]
        if not isinstance(sub, str) or not sub or len(sub) > 128:
            raise InvalidToken("malformed")
        groups = claims.get("cognito:groups", [])
        if not isinstance(groups, list) or not all(isinstance(g, str) for g in groups):
            raise InvalidToken("malformed")
        if (ADMIN_GROUP in groups) != admin:
            raise WrongGroup("group")
        email, nickname = claims.get("email"), claims.get("nickname")
        return Identity(
            sub=sub,
            email=email if isinstance(email, str) else None,
            email_verified=claims.get("email_verified") is True,
            nickname=nickname if isinstance(nickname, str) else None,
            groups=tuple(groups),
            issued_at=int(iat),
        )
