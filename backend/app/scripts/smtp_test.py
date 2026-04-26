"""Quick SMTP connectivity / credentials sanity check.

Run inside the backend container:

  docker compose exec backend python -m app.scripts.smtp_test you@example.com

It performs four progressively-deeper checks and prints a clear PASS/FAIL
with hints. The recipient defaults to ``SMTP_USER`` (i.e. send-to-self).
"""
from __future__ import annotations

import asyncio
import socket
import sys
from typing import Optional

import aiosmtplib

from app.core.config import settings
from app.services.email import send_email, smtp_config_summary


def _print(label: str, ok: bool, detail: str = "") -> None:
    icon = "[ OK ]" if ok else "[FAIL]"
    line = f"{icon}  {label}"
    if detail:
        line += f"  -- {detail}"
    print(line)


async def run(recipient: Optional[str] = None) -> int:
    target = (recipient or settings.smtp_user or "").strip()

    print("=" * 64)
    print(" SMTP smoke test")
    print("=" * 64)
    cfg = smtp_config_summary()
    for k, v in cfg.items():
        print(f"  {k:<10} {v}")
    print(f"  recipient  {target or '<none>'}")
    print("-" * 64)

    if not cfg["configured"]:
        _print(
            "config",
            False,
            "SMTP_USER or SMTP_PASSWORD is empty -- set both in .env",
        )
        return 2
    _print("config", True, "user + password are set")

    if not target:
        _print(
            "recipient",
            False,
            "Pass an email address as the first arg, e.g. "
            "`python -m app.scripts.smtp_test you@example.com`",
        )
        return 2
    _print("recipient", True, target)

    # 1) DNS resolution -----------------------------------------------------
    try:
        infos = socket.getaddrinfo(settings.smtp_host, settings.smtp_port)
        ip = infos[0][4][0] if infos else "?"
        _print("dns", True, f"{settings.smtp_host} -> {ip}")
    except socket.gaierror as exc:
        _print("dns", False, f"could not resolve {settings.smtp_host}: {exc}")
        return 3

    # 2) TCP connect + STARTTLS handshake ----------------------------------
    smtp = aiosmtplib.SMTP(
        hostname=settings.smtp_host,
        port=settings.smtp_port,
        timeout=15,
        start_tls=False,
    )
    try:
        await smtp.connect()
        _print("connect", True, f"connected to {settings.smtp_host}:{settings.smtp_port}")
    except Exception as exc:
        _print("connect", False, f"{type(exc).__name__}: {exc}")
        return 4

    try:
        if settings.smtp_tls:
            await smtp.starttls()
            _print("starttls", True, "TLS upgrade succeeded")
    except Exception as exc:
        _print("starttls", False, f"{type(exc).__name__}: {exc}")
        await smtp.quit()
        return 5

    # 3) AUTH ---------------------------------------------------------------
    try:
        await smtp.login(settings.smtp_user, settings.smtp_password)
        _print("auth", True, f"logged in as {settings.smtp_user}")
    except aiosmtplib.SMTPAuthenticationError as exc:
        _print(
            "auth",
            False,
            f"SMTPAuthenticationError: {exc}\n"
            "        For Gmail you MUST use an App Password "
            "(https://myaccount.google.com/apppasswords) -- a regular Google\n"
            "        account password will be rejected.",
        )
        await smtp.quit()
        return 6
    except Exception as exc:
        _print("auth", False, f"{type(exc).__name__}: {exc}")
        await smtp.quit()
        return 6
    finally:
        try:
            await smtp.quit()
        except Exception:
            pass

    # 4) Actually send a test message --------------------------------------
    try:
        await send_email(
            to=target,
            subject="DeepFake Detector - SMTP test",
            body=(
                "This is a test message from the smtp_test script.\n\n"
                "If you can read this, the verification email pipeline is "
                "working end-to-end."
            ),
            html=(
                "<p>This is a test message from the <b>smtp_test</b> "
                "script.</p><p>If you can read this, the verification email "
                "pipeline is working end-to-end.</p>"
            ),
        )
        _print("send", True, f"queued message to {target}")
    except Exception as exc:
        _print("send", False, f"{type(exc).__name__}: {exc}")
        return 7

    print("-" * 64)
    print("All checks passed. Look in the recipient's inbox (and Spam).")
    return 0


def main() -> None:
    recipient = sys.argv[1] if len(sys.argv) > 1 else None
    sys.exit(asyncio.run(run(recipient)))


if __name__ == "__main__":
    main()
