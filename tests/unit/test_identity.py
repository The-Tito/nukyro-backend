"""Verificador de tokens de identidad (T-17, D-34, D-35): cada rechazo y el caso válido."""

import base64
import hashlib
import hmac
import json
import time

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm

from nukyro.config import load_oidc_settings
from nukyro.identity import (
    ADMIN_GROUP,
    InvalidToken,
    JwksCache,
    OidcSettings,
    OidcVerifier,
    WrongGroup,
)

ISS, AUD, KID = "https://emisor.example.test/pool", "cliente-1", "k1"
NOW = 1_800_000_000.0


def make_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


KEY, OTHER = make_key(), make_key()


def jwks_of(key, kid=KID):
    jwk = json.loads(RSAAlgorithm.to_jwk(key.public_key()))
    return {"keys": [{**jwk, "kid": kid, "use": "sig", "alg": "RS256"}]}


def token(key=KEY, kid=KID, alg="RS256", **over):
    claims = {
        "sub": "sub-1",
        "iss": ISS,
        "aud": AUD,
        "token_use": "id",
        "iat": int(NOW),
        "exp": int(NOW) + 3600,
        "email": "a@example.test",
        "email_verified": True,
        "nickname": "Ana",
    }
    claims.update(over)
    claims = {k: v for k, v in claims.items() if v is not None}
    return jwt.encode(claims, key, algorithm=alg, headers={"kid": kid} if kid else {})


@pytest.fixture
def verifier():
    settings = OidcSettings(issuer=ISS, audience=AUD, jwks_url="http://x/jwks.json")
    return OidcVerifier(settings, lambda force=False: jwks_of(KEY), clock=lambda: NOW)


def reason(verifier, tok, **kw):
    with pytest.raises(InvalidToken) as info:
        verifier.verify(tok, **kw)
    return info.value.reason


def test_un_token_valido_devuelve_la_identidad(verifier):
    who = verifier.verify(token())
    assert (who.sub, who.email, who.email_verified, who.nickname) == (
        "sub-1",
        "a@example.test",
        True,
        "Ana",
    )
    assert who.groups == ()


def test_firma_de_otra_clave(verifier):
    assert reason(verifier, token(key=OTHER)) == "signature"


def test_token_alterado(verifier):
    head, body, sig = token().split(".")
    assert reason(verifier, f"{head}.{body}x.{sig}") in ("signature", "malformed")


def test_emisor_distinto(verifier):
    assert reason(verifier, token(iss="https://otro.example.test")) == "issuer"


def test_audiencia_distinta(verifier):
    assert reason(verifier, token(aud="otro-cliente")) == "audience"


def test_un_token_de_acceso_no_sirve(verifier):
    assert reason(verifier, token(token_use="access")) == "token_use"
    assert reason(verifier, token(token_use=None)) == "token_use"


def test_token_vencido(verifier):
    assert reason(verifier, token(iat=int(NOW) - 3000, exp=int(NOW) - 1)) == "expired"


def test_el_vencimiento_no_tiene_tolerancia(verifier):
    ok = token(iat=int(NOW) - 100, exp=int(NOW) + 1)
    assert verifier.verify(ok).sub == "sub-1"
    assert reason(verifier, token(iat=int(NOW) - 100, exp=int(NOW))) == "expired"


def test_token_demasiado_antiguo_aunque_no_haya_vencido(verifier):
    """D-35: un token anterior a una hora no se acepta aunque su exp sea posterior."""
    old = token(iat=int(NOW) - 3600, exp=int(NOW) - 3600 + 7200)
    assert reason(verifier, old) in ("too_old", "lifetime")


def test_vida_mayor_de_una_hora(verifier):
    assert reason(verifier, token(exp=int(NOW) + 3601)) == "lifetime"


def test_emitido_en_el_futuro(verifier):
    assert (
        reason(verifier, token(iat=int(NOW) + 600, exp=int(NOW) + 1200)) == "issued_in_the_future"
    )


def test_una_hora_exacta_de_edad_ya_no_sirve(verifier):
    assert reason(verifier, token(iat=int(NOW) - 3600, exp=int(NOW) + 1)) == "too_old"
    assert verifier.verify(token(iat=int(NOW) - 3599, exp=int(NOW) + 1)).sub == "sub-1"


@pytest.mark.parametrize("claim", ["sub", "iss", "aud", "exp", "iat"])
def test_faltan_datos_obligatorios(verifier, claim):
    assert reason(verifier, token(**{claim: None})) in ("malformed", "issuer", "audience")


def test_algoritmo_none(verifier):
    claims = {
        "sub": "s",
        "iss": ISS,
        "aud": AUD,
        "token_use": "id",
        "iat": int(NOW),
        "exp": int(NOW) + 60,
    }
    unsigned = jwt.encode(claims, None, algorithm="none", headers={"kid": KID})
    assert reason(verifier, unsigned) == "algorithm"


def test_hs256_con_la_clave_publica_como_secreto(verifier):
    """Confusión de algoritmo: HMAC con la clave pública de secreto (se arma a mano)."""
    pem = KEY.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    )

    def b64(data: bytes) -> bytes:
        return base64.urlsafe_b64encode(data).rstrip(b"=")

    head = b64(json.dumps({"alg": "HS256", "typ": "JWT", "kid": KID}).encode())
    claims = {
        "sub": "s",
        "iss": ISS,
        "aud": AUD,
        "token_use": "id",
        "iat": int(NOW),
        "exp": int(NOW) + 60,
    }
    body = b64(json.dumps(claims).encode())
    sig = b64(hmac.new(pem, head + b"." + body, hashlib.sha256).digest())
    assert reason(verifier, (head + b"." + body + b"." + sig).decode()) == "algorithm"


def test_kid_desconocido_o_ausente(verifier):
    assert reason(verifier, token(kid="otro")) == "unknown_key"
    assert reason(verifier, token(kid=None)) == "unknown_key"


@pytest.mark.parametrize("junk", ["", "a.b.c", "no-es-un-token", "x" * 9000])
def test_basura(verifier, junk):
    assert reason(verifier, junk) == "malformed"


def test_el_grupo_admins_no_es_participante(verifier):
    admin = token(**{"cognito:groups": [ADMIN_GROUP]})
    with pytest.raises(WrongGroup):
        verifier.verify(admin)
    assert verifier.verify(admin, admin=True).groups == (ADMIN_GROUP,)


def test_un_participante_no_es_administrador(verifier):
    with pytest.raises(WrongGroup):
        verifier.verify(token(), admin=True)
    with pytest.raises(WrongGroup):
        verifier.verify(token(**{"cognito:groups": ["otro"]}), admin=True)


def test_grupos_mal_formados(verifier):
    assert reason(verifier, token(**{"cognito:groups": "admins"})) == "malformed"
    assert reason(verifier, token(**{"cognito:groups": [1]})) == "malformed"


def test_sub_invalido(verifier):
    assert reason(verifier, token(sub="x" * 129)) == "malformed"


def test_email_verified_solo_con_true_literal(verifier):
    assert verifier.verify(token(email_verified="true")).email_verified is False
    assert verifier.verify(token(email_verified=None)).email_verified is False


def test_el_motivo_no_incluye_el_token(verifier):
    tok = token(key=OTHER)
    with pytest.raises(InvalidToken) as info:
        verifier.verify(tok)
    assert tok not in str(info.value) and tok not in repr(info.value)


def test_jwks_caido_es_rechazo_no_error():
    def broken(force=False):
        raise OSError("sin red")

    settings = OidcSettings(issuer=ISS, audience=AUD, jwks_url="x")
    v = OidcVerifier(settings, broken, clock=lambda: NOW)
    assert reason(v, token()) == "jwks_unavailable"


def test_una_clave_nueva_se_descarga_una_vez():
    """Rotación: un kid desconocido fuerza una descarga; sigue limitada a una por minuto."""
    time_now = [1000.0]
    sets = [
        jwks_of(KEY, "viejo"),
        {"keys": jwks_of(KEY, "viejo")["keys"] + jwks_of(OTHER, "nuevo")["keys"]},
    ]
    calls = []

    def fetch():
        calls.append(time_now[0])
        return sets[min(len(calls) - 1, 1)]

    cache = JwksCache(fetch, clock=lambda: time_now[0])
    settings = OidcSettings(issuer=ISS, audience=AUD, jwks_url="x")
    v = OidcVerifier(settings, cache, clock=lambda: NOW)
    assert v.verify(token(key=KEY, kid="viejo")).sub == "sub-1"  # descarga 1
    time_now[0] += 5
    assert reason(v, token(key=OTHER, kid="nuevo")) == "unknown_key"  # fuerza, pero < 1 min
    assert len(calls) == 1
    time_now[0] += 61
    assert v.verify(token(key=OTHER, kid="nuevo")).sub == "sub-1"  # ahora sí
    assert len(calls) == 2
    # Un kid inexistente repetido no multiplica las descargas
    for _ in range(5):
        reason(v, token(key=OTHER, kid="fantasma"))
    assert len(calls) <= 3


def test_la_cache_expira_por_tiempo():
    now = [0.0]
    calls = []
    cache = JwksCache(lambda: calls.append(1) or {"keys": []}, clock=lambda: now[0])
    cache()
    cache()
    assert len(calls) == 1
    now[0] += 3601
    cache()
    assert len(calls) == 2


def test_configuracion_oidc():
    env = {"NUKYRO_OIDC_ISSUER": "https://e.example.test/p/", "NUKYRO_OIDC_AUDIENCE": "c"}
    s = load_oidc_settings(env)
    assert (s.issuer, s.audience) == ("https://e.example.test/p", "c")
    assert s.jwks_url == "https://e.example.test/p/.well-known/jwks.json"
    assert (
        load_oidc_settings({**env, "NUKYRO_OIDC_JWKS_URL": "http://i:8080/j"}).jwks_url
        == "http://i:8080/j"
    )


@pytest.mark.parametrize("missing", ["NUKYRO_OIDC_ISSUER", "NUKYRO_OIDC_AUDIENCE"])
def test_faltar_el_emisor_o_la_audiencia_impide_arrancar(missing):
    env = {"NUKYRO_OIDC_ISSUER": "https://e.example.test/p", "NUKYRO_OIDC_AUDIENCE": "c"}
    del env[missing]
    with pytest.raises(RuntimeError, match=missing):
        load_oidc_settings(env)


def test_el_reloj_real_se_usa_por_omision():
    settings = OidcSettings(issuer=ISS, audience=AUD, jwks_url="x")
    v = OidcVerifier(settings, lambda force=False: jwks_of(KEY))
    now = int(time.time())
    assert v.verify(token(iat=now, exp=now + 600)).sub == "sub-1"
