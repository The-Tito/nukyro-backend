"""Operaciones del proveedor local de identidad que requieren consultar su estado."""

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class ProviderUnavailable(Exception):
    """El proveedor no pudo confirmar el estado de la identidad."""


class LocalIdentityProvider:
    def __init__(self, url: str, admin_key: str = ""):
        self.url = url.rstrip("/")
        self.admin_key = admin_key

    def _send(self, request: Request, *, absent_status: int) -> bool:
        try:
            with urlopen(request, timeout=5) as response:  # noqa: S310 (URL del operador)
                if response.status == 200:
                    return True
        except HTTPError as error:
            if error.code == absent_status:
                return False
        except (URLError, OSError):
            pass
        raise ProviderUnavailable

    def has_identity(self, token: str) -> bool:
        request = Request(
            f"{self.url}/subjects/status",
            method="POST",
            headers={"Authorization": f"Bearer {token}"},
        )
        return self._send(request, absent_status=404)

    def delete_identity(self, subject: str) -> None:
        request = Request(
            f"{self.url}/subjects",
            data=json.dumps({"sub": subject}).encode(),
            method="DELETE",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.admin_key}",
            },
        )
        self._send(request, absent_status=404)
