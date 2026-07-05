"""Email notification service. Logs instead of sending when SMTP is not configured."""
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import settings

logger = logging.getLogger(__name__)


def send_email(to: str, subject: str, body_html: str) -> bool:
    """Send an email. Returns True on success. Never raises."""
    if not settings.smtp_user or not settings.smtp_password:
        logger.info("SMTP not configured — would send to %s: %s", to, subject)
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.email_from
        msg["To"] = to
        msg.attach(MIMEText(body_html, "html"))
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
            server.starttls()
            server.login(settings.smtp_user, settings.smtp_password)
            server.sendmail(settings.email_from, [to], msg.as_string())
        return True
    except Exception:
        logger.exception("Failed to send email to %s", to)
        return False


def notify_review_required(to: str, document_filename: str, risk_level: str, flag_count: int) -> bool:
    subject = f"[FraudGuard] Invoice needs review — {risk_level.upper()} risk"
    body = f"""
    <h2>Invoice flagged for review</h2>
    <p><strong>{document_filename}</strong> was flagged with
    <strong>{flag_count}</strong> fraud indicator(s) at
    <strong>{risk_level}</strong> risk level.</p>
    <p>Please log in to FraudGuard to review it before payment is released.</p>
    """
    return send_email(to, subject, body)
