"""T-17 contra el emisor simulado real, en un contenedor aparte (D-34, ADR-008 §9)."""

import httpx
import pytest

from nukyro.identity import (
    InvalidToken,
    OidcSettings,
    OidcVerifier,
    WrongGroup,
    fetch_jwks,
)

from .conftest import compose

# Los valores por omisión de compose.yaml
ISSUER = "https://cognito-sim.example.test/nukyro-local"
AUDIENCE = "nukyro-local-client"


@pytest.fixture(scope="module")
def verifier(issuer_url):
    settings = OidcSettings(ISSUER, AUDIENCE, f"{issuer_url}/.well-known/jwks.json")
    return OidcVerifier.from_settings(settings)


def reason(verifier, token, **kw):
    with pytest.raises(InvalidToken) as info:
        verifier.verify(token, **kw)
    return info.value.reason


def test_el_token_del_emisor_se_verifica_con_sus_claves_publicadas(verifier, mint):
    who = verifier.verify(mint(sub="sub-it-1", email="a@example.test", nickname="Ana"))
    assert (who.sub, who.email, who.email_verified, who.nickname) == (
        "sub-it-1",
        "a@example.test",
        True,
        "Ana",
    )


def test_el_emisor_publica_solo_la_clave_publica(issuer_url):
    keys = fetch_jwks(f"{issuer_url}/.well-known/jwks.json")["keys"]
    assert len(keys) == 1 and keys[0]["kty"] == "RSA"
    assert not {"d", "p", "q", "dp", "dq", "qi"} & set(keys[0])  # nada de la parte privada


@pytest.mark.parametrize(
    ("spec", "expected"),
    [
        ({"signing": "forged"}, "signature"),
        ({"signing": "unknown_kid"}, "unknown_key"),
        ({"iss": "https://otro.example.test"}, "issuer"),
        ({"aud": "otro-cliente"}, "audience"),
        ({"token_use": "access"}, "token_use"),
        ({"iat_offset": -100, "lifetime": 50}, "expired"),
        ({"iat_offset": -4000, "lifetime": 3600}, "expired"),
        ({"iat_offset": -3601, "lifetime": 7200}, "too_old"),
        ({"lifetime": 7200}, "lifetime"),
        ({"omit": ["sub"]}, "malformed"),
    ],
)
def test_cada_token_defectuoso_se_rechaza(verifier, mint, spec, expected):
    assert reason(verifier, mint(**spec)) == expected


def test_el_grupo_admins_no_pasa_como_participante(verifier, mint):
    with pytest.raises(WrongGroup):
        verifier.verify(mint(groups=["admins"]))
    assert verifier.verify(mint(groups=["admins"]), admin=True).groups == ("admins",)


def test_el_emisor_inalcanzable_rechaza_sin_romper(mint):
    """Un token bien formado llega a pedir las claves; sin emisor se rechaza, no revienta."""
    settings = OidcSettings(ISSUER, AUDIENCE, "http://127.0.0.1:9/.well-known/jwks.json")
    assert reason(OidcVerifier.from_settings(settings), mint()) == "jwks_unavailable"


def test_la_imagen_de_la_api_no_contiene_el_emisor():
    """ADR-008 §9: el emisor no entra en la imagen de la API."""
    out = compose(
        "exec",
        "-T",
        "api",
        "sh",
        "-c",
        "find / -xdev \\( -name 'issuer.py' -o -name 'devtools' \\) 2>/dev/null; echo fin",
    )
    assert out.strip() == "fin"


def test_la_imagen_del_emisor_no_contiene_la_api():
    out = compose("exec", "-T", "issuer", "sh", "-c", "ls /app; test ! -e /app/src && echo sin-src")
    assert "issuer.py" in out and "sin-src" in out and "migrations" not in out


def test_el_emisor_no_es_alcanzable_por_la_API_publica(api_https):
    from ssl import create_default_context

    base, ca = api_https
    client = httpx.Client(base_url=base, verify=create_default_context(cafile=ca), timeout=10)
    for path in ("/.well-known/jwks.json", "/token", "/api/v1/token"):
        assert client.get(path).status_code in (404, 405)
    client.close()
