"""Background scheduler for lead notifications and maintenance tasks"""
import os
import logging
from datetime import datetime, timedelta, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def send_daily_leads_email():
    """Send daily email with new leads to commercial team"""
    try:
        import aiosmtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        leads_email = os.getenv("LEADS_EMAIL", "")
        if not leads_email:
            logger.warning("LEADS_EMAIL not configured, skipping lead notification")
            return

        # Query new leads from database
        from .db import SyncSession, Contacto
        with SyncSession() as session:
            # Get leads from last 24 hours without notification sent
            today = datetime.now(timezone.utc)
            new_leads = session.query(Contacto).filter(
                Contacto.creado_en >= (today - timedelta(days=1)),
                # Filter: leads that haven't received email yet (add 'notified_at' column later)
            ).all()

            if not new_leads:
                logger.info("No new leads to notify today")
                return

            # Build email
            msg = MIMEMultipart()
            msg['Subject'] = f"Daily Leads Report - {today.strftime('%Y-%m-%d')}"
            msg['From'] = os.getenv("SMTP_USERNAME", "")
            msg['To'] = leads_email

            body = "New Leads:\n\n"
            for lead in new_leads:
                body += f"- {lead.nombre} ({lead.telefono}): {lead.area or 'Sin área'}\n"

            msg.attach(MIMEText(body, 'plain'))

            # Send email with retry (3 retries)
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    async with aiosmtplib.SMTP(
                        hostname=os.getenv("SMTP_SERVER", "smtp.gmail.com"),
                        port=int(os.getenv("SMTP_PORT", 587)),
                        use_tls=True
                    ) as smtp:
                        await smtp.login(
                            os.getenv("SMTP_USERNAME", ""),
                            os.getenv("SMTP_PASSWORD", "")
                        )
                        await smtp.send_message(msg)
                        logger.info(f"Daily leads email sent to {leads_email} ({len(new_leads)} leads)")
                        return
                except Exception as e:
                    logger.warning(f"Attempt {attempt + 1}/{max_retries} failed: {e}")
                    if attempt == max_retries - 1:
                        logger.error(f"Failed to send leads email after {max_retries} retries")
                        raise

    except Exception as e:
        logger.error(f"Error in send_daily_leads_email: {e}")


def start_scheduler():
    """Start the background scheduler"""
    if scheduler.running:
        logger.info("Scheduler already running")
        return

    # Schedule daily lead notification (default 8:00 AM)
    lead_hour = int(os.getenv("LEAD_NOTIFICATION_HOUR", 8))
    lead_minute = int(os.getenv("LEAD_NOTIFICATION_MINUTE", 0))

    scheduler.add_job(
        send_daily_leads_email,
        trigger=CronTrigger(hour=lead_hour, minute=lead_minute),
        id='daily_leads_notification',
        name='Send daily leads email notification',
        replace_existing=True
    )

    try:
        scheduler.start()
        logger.info(f"Scheduler started. Daily lead notification: {lead_hour:02d}:{lead_minute:02d}")
    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}")


def stop_scheduler():
    """Stop the background scheduler"""
    if scheduler.running:
        scheduler.shutdown(wait=True)
        logger.info("Scheduler stopped")
