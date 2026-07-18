"""Email service abstraction — Resend (production) and Console (local dev)."""

from abc import ABC, abstractmethod

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class EmailService(ABC):
    """Abstract email service interface."""

    @abstractmethod
    async def send_otp(self, email: str, code: str) -> None:
        """Send an OTP code to the given email."""
        ...


class ResendEmailService(EmailService):
    """Production email service using Resend API."""

    RESEND_API_URL = "https://api.resend.com/emails"

    def __init__(self) -> None:
        settings = get_settings()
        self._api_key = settings.RESEND_API_KEY
        self._from_email = settings.RESEND_FROM_EMAIL

    async def send_otp(self, email: str, code: str) -> None:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.RESEND_API_URL,
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "from": self._from_email,
                        "to": [email],
                        "subject": f"Your login code: {code}",
                        "html": (
                            f"<h2>Your login code</h2>"
                            f"<p style='font-size:32px;font-weight:bold;letter-spacing:8px'>{code}</p>"
                            f"<p>This code expires in 10 minutes.</p>"
                            f"<p>If you didn't request this, ignore this email.</p>"
                        ),
                    },
                )
                response.raise_for_status()
                logger.info("OTP email sent via Resend", email=email)
            except httpx.HTTPStatusError as e:
                logger.error(
                    "Failed to send OTP via Resend",
                    email=email,
                    status_code=e.response.status_code,
                    response_body=e.response.text,
                )
                raise
            except Exception as e:
                logger.error("Unexpected error sending OTP via Resend", email=email, error=str(e))
                raise


class ConsoleEmailService(EmailService):
    """Development email service — prints OTP to console."""

    async def send_otp(self, email: str, code: str) -> None:
        logger.info(
            "=== LOCAL DEV OTP ===",
            email=email,
            code=code,
        )


def get_email_service() -> EmailService:
    """Factory: return the appropriate email backend based on config."""
    settings = get_settings()
    if settings.is_local or not settings.RESEND_API_KEY:
        return ConsoleEmailService()
    return ResendEmailService()
