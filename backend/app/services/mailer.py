"""Verification mail (guide §6.2, P-01): an `EmailSender` with an SMTP implementation.

With SMTP settings (host + username) every environment, local included, sends real mail
through STARTTLS (Gmail: smtp.gmail.com:587 with an app password). Without them nothing is
sent and the request fails (503): no code is ever written to a log. Automatic tests inject
their own recording sender instead.
"""

import logging
import smtplib
import ssl
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import formataddr
from typing import Protocol

from app.config import settings

logger = logging.getLogger(__name__)

SUBJECTS = {
    "signup": "[KickTab] 회원가입 인증번호",
    "password_reset": "[KickTab] 비밀번호 찾기 인증번호",
}
PURPOSE_TEXT = {"signup": "회원가입", "password_reset": "비밀번호 찾기"}


class EmailSendError(Exception):
    """The message could not be handed to the mail server."""


class EmailSender(Protocol):
    def send_code(self, to: str, purpose: str, code: str) -> None: ...


def code_message(sender: str, to: str, purpose: str, code: str) -> EmailMessage:
    message = EmailMessage()
    message["Subject"] = SUBJECTS[purpose]
    message["From"] = formataddr(("KickTab", sender))
    message["To"] = to
    message.set_content(
        f"KickTab {PURPOSE_TEXT[purpose]} 인증번호입니다.\n\n"
        f"인증번호: {code}\n\n"
        "인증번호는 10분 동안 유효하며, 다시 받으면 이전 번호는 사용할 수 없습니다.\n"
        "요청하지 않으셨다면 이 메일을 무시해 주세요.\n"
    )
    return message


@dataclass(frozen=True)
class SmtpSender:
    host: str
    port: int
    username: str
    password: str
    sender: str
    timeout: float = 20.0

    def send_code(self, to: str, purpose: str, code: str) -> None:
        message = code_message(self.sender, to, purpose, code)
        try:
            with smtplib.SMTP(self.host, self.port, timeout=self.timeout) as smtp:
                smtp.starttls(context=ssl.create_default_context())
                smtp.login(self.username, self.password)
                smtp.send_message(message)
        except (smtplib.SMTPException, OSError) as exc:
            # The exception text may echo server replies; log its type only.
            logger.warning("Verification mail failed: %s", type(exc).__name__)
            raise EmailSendError from None


class UnconfiguredSender:
    """SMTP is not set up: refuse instead of pretending the mail went out."""

    def send_code(self, to: str, purpose: str, code: str) -> None:
        logger.error("Verification mail not sent: SMTP is not configured")
        raise EmailSendError


def smtp_configured() -> bool:
    return bool(settings.smtp_host and settings.smtp_username)


def get_email_sender() -> EmailSender:
    """FastAPI dependency. Tests override it with a recording sender."""
    if not smtp_configured():
        return UnconfiguredSender()
    # An app password pasted as "abcd efgh ijkl mnop" still works (spaces removed).
    password = "".join(settings.smtp_password.get_secret_value().split())
    return SmtpSender(
        host=settings.smtp_host,
        port=settings.smtp_port,
        username=settings.smtp_username,
        password=password,
        sender=settings.email_from or settings.smtp_username,
    )
