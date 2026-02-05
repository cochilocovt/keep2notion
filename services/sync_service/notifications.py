"""Notification utilities for critical errors."""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


class NotificationService:
    """Handles sending notifications for critical errors."""
    
    def __init__(self):
        """Initialize notification service."""
        self.notification_enabled = os.getenv("ENABLE_NOTIFICATIONS", "false").lower() == "true"
        self.notification_webhook = os.getenv("NOTIFICATION_WEBHOOK_URL")
    
    async def send_critical_error_notification(
        self,
        job_id: str,
        user_id: str,
        error_message: str,
        context: Optional[dict] = None
    ):
        """
        Send notification for critical errors.
        
        In production, this would integrate with services like:
        - AWS SNS
        - Slack webhooks
        - Email via SES
        - PagerDuty
        
        Args:
            job_id: The sync job ID
            user_id: The user ID
            error_message: The error message
            context: Optional additional context
        """
        if not self.notification_enabled:
            logger.info(f"Notifications disabled, skipping notification for job {job_id}")
            return
        
        notification_message = (
            f"Critical Error in Sync Job\n"
            f"Job ID: {job_id}\n"
            f"User ID: {user_id}\n"
            f"Error: {error_message}\n"
        )
        
        if context:
            notification_message += f"Context: {context}\n"
        
        logger.warning(f"CRITICAL ERROR NOTIFICATION: {notification_message}")
        
        # In production, implement actual notification sending here
        # For example:
        # - Send to AWS SNS topic
        # - Post to Slack webhook
        # - Send email via AWS SES
        # - Create PagerDuty incident
        
        if self.notification_webhook:
            try:
                import httpx
                async with httpx.AsyncClient() as client:
                    await client.post(
                        self.notification_webhook,
                        json={
                            "text": notification_message,
                            "job_id": job_id,
                            "user_id": user_id,
                            "error": error_message
                        },
                        timeout=10.0
                    )
                logger.info(f"Notification sent for job {job_id}")
            except Exception as e:
                logger.error(f"Failed to send notification: {e}")
