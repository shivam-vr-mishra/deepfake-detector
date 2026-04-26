"""Email service using aiosmtplib.

Notes for Gmail users:
  Regular Google account passwords no longer work for SMTP since May 2022.
  You must:
    1. Enable 2-Step Verification on the Google account.
    2. Generate an "App Password" at https://myaccount.google.com/apppasswords
    3. Use that 16-character password (without spaces) as ``SMTP_PASSWORD``.
"""
from __future__ import annotations

from email.message import EmailMessage

import aiosmtplib

from app.core.config import settings
from app.core.logging import get_logger

log = get_logger(__name__)


def smtp_config_summary() -> dict[str, object]:
    """Best-effort, non-secret summary of the active SMTP configuration.

    Useful for /health, startup logs and the smtp_test CLI.
    """
    user = settings.smtp_user or ""
    pw = settings.smtp_password or ""
    masked = (
        f"{pw[:2]}***{pw[-2:]} (len={len(pw)})" if len(pw) >= 4 else "<unset>"
        if not pw
        else "<too-short>"
    )
    return {
        "configured": bool(user and pw),
        "host": settings.smtp_host,
        "port": settings.smtp_port,
        "user": user,
        "password": masked,
        "from": settings.smtp_from,
        "tls": settings.smtp_tls,
    }


async def send_email(
    *, to: str, subject: str, body: str, html: str | None = None
) -> None:
    """Send a single email. Errors are logged with full context and re-raised
    so callers (or BackgroundTasks) see the failure rather than silently
    losing it."""
    if not settings.smtp_user or not settings.smtp_password:
        log.warning(
            "email.skipped_no_smtp",
            to=to,
            subject=subject,
            reason="SMTP_USER or SMTP_PASSWORD is empty",
        )
        return

    msg = EmailMessage()
    msg["From"] = settings.smtp_from
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    if html:
        msg.add_alternative(html, subtype="html")

    try:
        await aiosmtplib.send(
            msg,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user,
            password=settings.smtp_password,
            start_tls=settings.smtp_tls,
        )
        log.info("email.sent", to=to, subject=subject, host=settings.smtp_host)
    except aiosmtplib.SMTPAuthenticationError as exc:
        log.error(
            "email.send_failed.auth",
            to=to,
            host=settings.smtp_host,
            port=settings.smtp_port,
            user=settings.smtp_user,
            error=str(exc),
            hint=(
                "SMTP authentication rejected. For Gmail, you MUST use an "
                "App Password (16 characters, generated at "
                "https://myaccount.google.com/apppasswords) — your regular "
                "Google account password will not work."
            ),
        )
    except aiosmtplib.SMTPConnectError as exc:
        log.error(
            "email.send_failed.connect",
            to=to,
            host=settings.smtp_host,
            port=settings.smtp_port,
            error=str(exc),
            hint=(
                "Could not connect to SMTP server. Check SMTP_HOST/SMTP_PORT "
                "and that outbound traffic to that port is allowed."
            ),
        )
    except Exception as exc:
        log.exception(
            "email.send_failed",
            to=to,
            host=settings.smtp_host,
            port=settings.smtp_port,
            error_type=type(exc).__name__,
            error=str(exc),
        )


def build_email_verification_email(
    verify_link: str, full_name: str | None = None
) -> tuple[str, str]:
    """Plain-text + HTML versions of the verification email."""
    greeting = f"Hi {full_name}," if full_name else "Hi,"
    minutes = settings.email_verification_expire_minutes
    if minutes % (60 * 24) == 0:
        validity = f"{minutes // (60 * 24)} day(s)"
    elif minutes % 60 == 0:
        validity = f"{minutes // 60} hour(s)"
    else:
        validity = f"{minutes} minutes"

    text = (
        f"{greeting}\n\n"
        "Welcome to DeepFake Detector! Please verify your email address to "
        "activate your account.\n\n"
        f"Verification link (valid for {validity}):\n\n"
        f"{verify_link}\n\n"
        "If you did not create this account, you can safely ignore this email."
    )
    html = f"""\
<html><body style="font-family:Inter,Arial,sans-serif;background:#f8fafc;
                  padding:24px;color:#0f172a">
  <div style="max-width:560px;margin:0 auto;background:#fff;border-radius:14px;
              padding:32px;box-shadow:0 4px 20px rgba(15,23,42,.06)">
    <h2 style="margin:0 0 8px 0">Verify your email</h2>
    <p style="margin:0 0 16px 0;color:#475569">{greeting}</p>
    <p style="margin:0 0 20px 0;color:#475569">
      Welcome to <strong>DeepFake Detector</strong>! Confirm your email
      address to activate your account.
    </p>
    <p style="text-align:center;margin:24px 0">
      <a href="{verify_link}"
         style="background:linear-gradient(135deg,#6366f1,#d946ef);
                color:white;font-weight:600;padding:12px 22px;
                border-radius:10px;text-decoration:none;display:inline-block">
        Verify my email
      </a>
    </p>
    <p style="color:#64748b;font-size:13px;margin:8px 0 0">
      Or paste this link in your browser:<br/>
      <a href="{verify_link}" style="color:#4f46e5;word-break:break-all">
        {verify_link}
      </a>
    </p>
    <p style="color:#94a3b8;font-size:12px;margin-top:24px">
      This link expires in {validity}. If you didn't create an account,
      you can safely ignore this email.
    </p>
  </div>
</body></html>"""
    return text, html


def build_password_reset_email(reset_link: str) -> tuple[str, str]:
    text = (
        "You requested a password reset for DeepFake Detector.\n\n"
        f"Click the link below to reset your password (valid for "
        f"{settings.password_reset_expire_minutes} minutes):\n\n"
        f"{reset_link}\n\n"
        "If you didn't request this, you can safely ignore this email."
    )
    html = f"""\
<html><body style="font-family:Inter,Arial,sans-serif">
<h2>DeepFake Detector — Password Reset</h2>
<p>Click the button below to reset your password
(valid for {settings.password_reset_expire_minutes} minutes):</p>
<p><a href="{reset_link}"
      style="background:#6366f1;color:white;padding:10px 18px;
             border-radius:8px;text-decoration:none;">
   Reset password</a></p>
<p>If you didn't request this, you can ignore this email.</p>
</body></html>"""
    return text, html
