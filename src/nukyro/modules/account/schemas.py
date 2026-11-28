"""Esquemas de la cuenta. La entrada es estricta; la identidad viene del token, no del cuerpo."""

from pydantic import BaseModel, ConfigDict, StrictBool


class LoginIn(BaseModel):
    """Casillas del registro (RF-074): valen para una cuenta nueva y sin marcar por omisión."""

    model_config = ConfigDict(extra="forbid", strict=True)
    newsletter_opt_in: StrictBool = False
    surveys_opt_in: StrictBool = False


class LoginOut(BaseModel):
    nickname: str
    has_participant: bool  # false: falta aceptar los documentos (POST /participants)
    linked: bool  # el progreso del navegador pasó a la cuenta


class AccountOut(BaseModel):
    nickname: str
    email: str
    newsletter_opt_in: bool
    surveys_opt_in: bool
