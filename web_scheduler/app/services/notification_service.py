from __future__ import annotations

import requests

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def _normalize_recipients(csv_text: str | None) -> list[str]:
    out: list[str] = []
    for token in (csv_text or "").split(","):
        t = token.strip()
        if not t:
            continue
        if "@" not in t:
            t = f"{t}@samsung.com"
        out.append(t)
    # unique
    return sorted(set(out))


def send_mail_html(subject: str, html_body: str, recipients_csv: str | None) -> None:
    settings = get_settings()
    recipients = _normalize_recipients(recipients_csv)

    if not recipients:
        logger.info("mail skip: recipients empty")
        return

    if not settings.mail_enabled:
        logger.info("mail disabled. subject=%s recipients=%s", subject, ",".join(recipients))
        return

    if not settings.mail_api_url or not settings.mail_token or not settings.mail_system_id or not settings.mail_sender_id:
        logger.warning("mail config missing. subject=%s", subject)
        return

    payload = {
        "subject": subject,
        "contents": html_body,
        "contentType": "HTML",
        "docSecuType": "PERSONAL",
        "sender": {"emailAddress": f"{settings.mail_sender_id}@samsung.com"},
        "recipients": [{"emailAddress": r, "recipientType": "TO"} for r in recipients],
    }

    headers = {
        "Authorization": settings.mail_token,
        "System-ID": settings.mail_system_id,
        "Content-Type": "application/json",
    }

    try:
        r = requests.post(settings.mail_api_url, json=payload, headers=headers, timeout=20)
        if not (200 <= r.status_code < 300):
            logger.warning("mail send failed status=%s body=%s", r.status_code, r.text[:500])
        else:
            logger.info("mail sent. subject=%s recipients=%s", subject, len(recipients))
    except Exception as exc:
        logger.warning("mail send exception: %s", exc)
