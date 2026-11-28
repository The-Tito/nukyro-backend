"""Emisor de identidad SIMULADO para el entorno local y las pruebas (D-15, D-34).

No es Cognito. Imita lo que la API verifica de un token de identidad de Cognito (RS256, JWKS,
token_use, cognito:groups) y deja pedir tokens defectuosos a propósito para probar los rechazos.
Vive en su propio contenedor y NUNCA entra en la imagen de la API (ADR-008 §9). La clave se genera
al arrancar y no se guarda: no hay ninguna clave privada en el repositorio ni en una imagen.
"""

import hmac
import json
import os
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm

ISSUER = os.environ["NUKYRO_OIDC_ISSUER"].rstrip("/")
AUDIENCE = os.environ["NUKYRO_OIDC_AUDIENCE"]
PUBLISHED_KID = "sim-1"
UNPUBLISHED_KID = "sim-unpublished"
ADMIN_KEY = os.environ.get("NUKYRO_LOCAL_IDENTITY_ADMIN_KEY", "")
SUBJECTS = {}
SUBJECTS_LOCK = threading.Lock()


def _key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


MAIN, OTHER = _key(), _key()  # OTHER nunca se publica: sirve para firmas falsas


def jwks() -> dict:
    jwk = json.loads(RSAAlgorithm.to_jwk(MAIN.public_key()))
    return {"keys": [{**jwk, "kid": PUBLISHED_KID, "use": "sig", "alg": "RS256"}]}


def mint(spec: dict) -> str:
    """Emite un token válido por omisión. Los campos opcionales permiten probar los rechazos."""
    now = int(time.time()) + int(spec.get("iat_offset", 0))
    claims = {
        "sub": spec.get("sub") or str(uuid.uuid4()),
        "iss": spec.get("iss", ISSUER),
        "aud": spec.get("aud", AUDIENCE),
        "token_use": spec.get("token_use", "id"),
        "iat": now,
        "auth_time": now,
        "exp": now + int(spec.get("lifetime", 3600)),
        "email": spec.get("email", "persona@example.test"),
        "email_verified": spec.get("email_verified", True),
        "nickname": spec.get("nickname", "Persona de prueba"),
    }
    claims["cognito:username"] = claims["sub"]
    with SUBJECTS_LOCK:
        claims["sim_subject_generation"] = SUBJECTS.setdefault(claims["sub"], uuid.uuid4().hex)
    if spec.get("groups"):
        claims["cognito:groups"] = list(spec["groups"])
    for name in spec.get("omit", []):
        claims.pop(name, None)
    signing = spec.get("signing", "main")
    if signing == "forged":  # firma de otra clave bajo el kid publicado
        key, kid = OTHER, PUBLISHED_KID
    elif signing == "unknown_kid":  # firmado con una clave que el emisor no publica
        key, kid = OTHER, UNPUBLISHED_KID
    else:
        key, kid = MAIN, PUBLISHED_KID
    return jwt.encode(claims, key, algorithm="RS256", headers={"kid": kid})


class Handler(BaseHTTPRequestHandler):
    def _send(self, status: int, body: dict) -> None:
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/healthz":
            self._send(200, {"status": "ok"})
        elif self.path == "/.well-known/jwks.json":
            self._send(200, jwks())
        else:
            self._send(404, {"error": "not_found"})

    def do_POST(self):
        if self.path == "/subjects/status":
            return self._subject_status()
        if self.path != "/token":
            return self._send(404, {"error": "not_found"})
        try:
            length = int(self.headers.get("Content-Length") or 0)
            spec = json.loads(self.rfile.read(length) or b"{}")
            if not isinstance(spec, dict):
                raise ValueError
            self._send(200, {"id_token": mint(spec)})
        except (ValueError, TypeError):
            self._send(400, {"error": "bad_request"})

    def _subject_status(self):
        authorization = self.headers.get("Authorization", "")
        if not authorization.startswith("Bearer "):
            return self._send(404, {"error": "not_found"})
        try:
            claims = jwt.decode(
                authorization[7:],
                MAIN.public_key(),
                algorithms=["RS256"],
                issuer=ISSUER,
                audience=AUDIENCE,
                options={"verify_iat": False},
            )
            with SUBJECTS_LOCK:
                generation = SUBJECTS.get(claims["sub"])
                active = generation is not None and generation == claims["sim_subject_generation"]
        except (KeyError, jwt.PyJWTError):
            active = False
        if active:
            return self._send(200, {"status": "active"})
        return self._send(404, {"error": "not_found"})

    def do_DELETE(self):
        if self.path != "/subjects":
            return self._send(404, {"error": "not_found"})
        auth = self.headers.get("Authorization", "")
        if not ADMIN_KEY or not hmac.compare_digest(auth.encode(), f"Bearer {ADMIN_KEY}".encode()):
            return self._send(403, {"error": "forbidden"})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 1024:
                raise ValueError
            subject = json.loads(self.rfile.read(length))["sub"]
            if not isinstance(subject, str):
                raise ValueError
        except (ValueError, TypeError, KeyError):
            return self._send(400, {"error": "bad_request"})
        with SUBJECTS_LOCK:
            removed = SUBJECTS.pop(subject, None)
        if removed is None:
            return self._send(404, {"error": "not_found"})
        return self._send(200, {"status": "deleted"})

    def log_message(self, *args):  # sin registros: los tokens no deben quedar en logs
        pass


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
