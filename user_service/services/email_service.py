from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import aiosmtplib
import structlog
from jinja2 import Environment, FileSystemLoader

from core.config import settings

logger = structlog.getLogger(__name__)

_templates = Environment(
    loader=FileSystemLoader(Path(__file__).resolve().parent.parent / "templates"),
    autoescape=True,
)


async def _send(to_email: str, subject: str, html: str) -> None:
    if not settings.email.configured:
        logger.warning("Email not configured, skipping send", to=to_email, subject=subject)
        return

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = f"{settings.email.from_name} <{settings.email.from_email}>"
    message["To"] = to_email
    message.attach(MIMEText(html, "html"))
    try:
        await aiosmtplib.send(
            message,
            hostname=settings.email.host,
            port=settings.email.port,
            username=settings.email.username,
            password=settings.email.password,
            start_tls=settings.email.use_tls,
        )
        logger.info("Email sent", to=to_email, subject=subject)
    except Exception:
        logger.exception("Failed to send email", to=to_email, subject=subject)


async def send_verification_email(to_email: str) -> None:
    from core.security import create_token

    token = create_token(to_email, "verify")
    verify_url = f"{settings.app.domain.rstrip('/')}/auth/verify?token={token}"
    html = _templates.get_template("email/verify.html").render(
        app_name=settings.app.title,
        verify_url=verify_url,
        expire_hours=settings.jwt.verify_token_expire_hours,
    )
    await _send(to_email, "Confirm your email", html)


async def send_reset_password_email(to_email: str) -> None:
    from core.security import create_token

    token = create_token(to_email, "reset")
    reset_url = f"{settings.app.domain.rstrip('/')}/auth/reset-password?token={token}"
    html = _templates.get_template("email/reset_password.html").render(
        app_name=settings.app.title,
        reset_url=reset_url,
        expire_hours=settings.jwt.reset_token_expire_hours,
    )
    await _send(to_email, "Reset your password", html)
