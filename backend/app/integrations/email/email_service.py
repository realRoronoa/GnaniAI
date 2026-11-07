"""Email Notification Service for ArogyaScribe B2B Onboarding

Handles:
1. Instant alert to Platform Owner whenever a new clinic submits registration inquiry.
2. Welcome & credentials email to the new Organization Administrator upon approval.
3. Disk outbox logging under ./storage/email_outbox.log for transparency and offline development.
4. Production-ready SMTP dispatch (TLS) when SMTP settings are configured in .env.
"""
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import logging
import os
import smtplib
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailNotificationService:
    def __init__(self) -> None:
        self.smtp_host = getattr(settings, "SMTP_HOST", "")
        self.smtp_port = getattr(settings, "SMTP_PORT", 587)
        self.smtp_user = getattr(settings, "SMTP_USER", "")
        self.smtp_password = getattr(settings, "SMTP_PASSWORD", "")
        self.smtp_from = getattr(settings, "SMTP_FROM_EMAIL", "noreply@arogyascribe.in")
        self.owner_email = getattr(settings, "OWNER_NOTIFICATION_EMAIL", "owner@arogyascribe.in")
        self.outbox_dir = "./storage"
        self.outbox_log = os.path.join(self.outbox_dir, "email_outbox.log")

    def _log_to_outbox(self, to_email: str, subject: str, body_text: str) -> None:
        """Appends email notification to ./storage/email_outbox.log."""
        try:
            os.makedirs(self.outbox_dir, exist_ok=True)
            timestamp = datetime.now(timezone.utc).isoformat()
            divider = "=" * 70
            entry = f"\n{divider}\nTIMESTAMP: {timestamp}\nTO: {to_email}\nFROM: {self.smtp_from}\nSUBJECT: {subject}\n{divider}\n{body_text}\n{divider}\n"
            with open(self.outbox_log, "a", encoding="utf-8") as f:
                f.write(entry)
        except Exception as e:
            logger.warning("Failed to append email to local outbox log: %s", e)

    def _send_smtp(self, to_email: str, subject: str, body_text: str) -> None:
        """Dispatches email via configured SMTP server if credentials exist."""
        if not self.smtp_host or not self.smtp_user:
            logger.info("SMTP not configured. Email logged to disk outbox: %s", to_email)
            return

        try:
            msg = MIMEMultipart()
            msg["From"] = self.smtp_from
            msg["To"] = to_email
            msg["Subject"] = subject
            msg.attach(MIMEText(body_text, "plain", "utf-8"))

            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=15) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            logger.info("Outbound email successfully dispatched via SMTP to %s", to_email)
        except Exception as e:
            logger.error("Failed to send outbound email via SMTP to %s: %s", to_email, e)

    def send_owner_registration_alert(self, org_data: dict[str, Any]) -> None:
        """Sends an immediate alert to Platform Owner when a clinic submits registration."""
        subject = f"[ArogyaScribe Alert] New Clinic Registration: {org_data.get('name', 'New Clinic')}"
        now = datetime.now(timezone.utc).strftime("%d-%b-%Y %H:%M UTC")

        body_text = f"""
ArogyaScribe Platform Administration Alert:
A new healthcare organization has submitted an onboarding request.

--------------------------------------------------
ORGANIZATION DETAILS:
--------------------------------------------------
Clinic/Hospital Name : {org_data.get('name')}
Facility Type        : {org_data.get('org_type', 'CLINIC')}
City / Address       : {org_data.get('address', 'Not Specified')}

CONTACT PERSON:
Full Name            : {org_data.get('admin_full_name')}
Work Email           : {org_data.get('contact_email')}
Phone Number         : {org_data.get('contact_phone', 'Not Specified')}

REQUESTED PLAN & COMMERCIALS:
Requested Tier       : {org_data.get('requested_plan', 'PROFESSIONAL')}
Billing Cycle        : {org_data.get('requested_billing_cycle', 'MONTHLY')}
Coupon Code Applied  : {org_data.get('coupon_code', 'None')}

Submission Time      : {now}
Status               : PENDING PLATFORM OWNER REVIEW
--------------------------------------------------

NEXT STEPS:
1. Connect with the clinic administrator to verify clinical requirements.
2. Open Platform Owner Console -> Organizations.
3. Review and click "Connect & Approve Organization" to activate their subscription and provision their Admin account.
"""
        self._log_to_outbox(self.owner_email, subject, body_text)
        self._send_smtp(self.owner_email, subject, body_text)

    def send_customer_approval_welcome(
        self,
        admin_email: str,
        admin_name: str,
        org_name: str,
        plan_name: str,
        temp_password: str,
    ) -> None:
        """Sends welcome credentials email to new Org Admin upon Platform Owner approval."""
        subject = f"Welcome to ArogyaScribe - {org_name} is Now Active!"
        body_text = f"""
Dear {admin_name},

Congratulations! Your organization account for {org_name} has been reviewed and approved by the ArogyaScribe Platform Team.

--------------------------------------------------
YOUR CLINIC CONSOLE CREDENTIALS:
--------------------------------------------------
Organization Name : {org_name}
Subscription Plan : {plan_name} (Active)
Sign-in URL       : https://app.arogyascribe.in/login (or http://localhost:5173/login)
Work Email        : {admin_email}
Temporary Password: {temp_password}
--------------------------------------------------

IMPORTANT SECURITY NOTICE:
Please sign in and change your password immediately upon your first login.
As the Organization Administrator, you can now add doctors, configure receptionists, and manage clinic consultation quotas from your Organization Console.

Thank you for partnering with ArogyaScribe.
Sovereign Ambient AI Clinical Scribing for India.
"""
        self._log_to_outbox(admin_email, subject, body_text)
        self._send_smtp(admin_email, subject, body_text)


# Global singleton instance
email_service = EmailNotificationService()

