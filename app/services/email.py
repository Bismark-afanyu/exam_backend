import logging

import resend

from app.core.config import settings

logger = logging.getLogger(__name__)


def send_password_reset_email(to_email: str, reset_link: str) -> None:
    """Sends a password reset email via Resend."""
    if not settings.RESEND_API_KEY or not settings.RESEND_FROM_EMAIL:
        logger.warning("Resend not configured — skipping email to %s. Reset link: %s", to_email, reset_link)
        return

    resend.api_key = settings.RESEND_API_KEY

    params: resend.Emails.SendParams = {
        "from": settings.RESEND_FROM_EMAIL,
        "to": [to_email],
        "subject": "Reset your password — Ŋwà'",
        "html": f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin:0;padding:0;background-color:#f8fafc;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
  <div style="max-width:480px;margin:40px auto;background:#ffffff;border-radius:16px;border:1px solid #e2e8f0;overflow:hidden;">
    <div style="background-color:#059669;padding:24px 32px;">
      <h1 style="margin:0;color:#ffffff;font-size:20px;font-weight:700;">Ŋwà'</h1>
    </div>
    <div style="padding:32px;">
      <h2 style="margin:0 0 12px;color:#0f172a;font-size:18px;font-weight:700;">Reset your password</h2>
      <p style="margin:0 0 24px;color:#64748b;font-size:14px;line-height:1.6;">
        You requested a password reset. Click the button below to set a new password. This link expires in 1 hour.
      </p>
      <a href="{reset_link}" style="display:inline-block;padding:12px 32px;background-color:#059669;color:#ffffff;font-size:14px;font-weight:600;text-decoration:none;border-radius:10px;">
        Reset Password
      </a>
      <p style="margin:24px 0 0;color:#94a3b8;font-size:12px;line-height:1.6;">
        If you didn't request this, you can safely ignore this email.
      </p>
    </div>
  </div>
</body>
</html>
""",
    }

    try:
        resend.Emails.send(params)
        logger.info("Password reset email sent to %s", to_email)
    except Exception:
        logger.exception("Failed to send password reset email to %s", to_email)
        raise
