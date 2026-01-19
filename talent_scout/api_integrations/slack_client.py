"""Slack API integration for notifications."""
import logging
from typing import Optional

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from talent_scout.config import get_config

logger = logging.getLogger(__name__)


class SlackClient:
    """Slack API client for sending notifications."""
    
    def __init__(self):
        """Initialize Slack client."""
        self.config = get_config()
        
        if not self.config.slack_bot_token:
            logger.warning("Slack bot token not configured. Notifications will be skipped.")
            self.client = None
        else:
            self.client = WebClient(token=self.config.slack_bot_token)
            logger.info("Initialized Slack client")
    
    def send_message(self, message: str, channel: Optional[str] = None) -> bool:
        """Send a message to Slack channel.
        
        Args:
            message: Message text
            channel: Channel ID (uses default from config if not provided)
            
        Returns:
            True if successful
        """
        if not self.client:
            logger.warning("Slack client not configured. Skipping message.")
            return False
        
        try:
            channel_id = channel or self.config.slack_channel_id
            
            response = self.client.chat_postMessage(
                channel=channel_id,
                text=message
            )
            
            logger.info(f"Sent Slack message to {channel_id}")
            return True
            
        except SlackApiError as e:
            logger.error(f"Error sending Slack message: {e}")
            return False
    
    def send_approval_request(
        self, 
        candidate_name: str, 
        candidate_email: str,
        draft_preview: str,
        candidate_id: str
    ) -> bool:
        """Send an approval request with interactive buttons.
        
        Args:
            candidate_name: Candidate name
            candidate_email: Candidate email
            draft_preview: Preview of the email draft
            candidate_id: Candidate ID for callback
            
        Returns:
            True if successful
        """
        if not self.client:
            logger.warning("Slack client not configured. Skipping approval request.")
            return False
        
        try:
            channel_id = self.config.slack_channel_id
            
            # Create message with blocks for interactive buttons
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"📧 Email Draft Ready for {candidate_name}"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Candidate:* {candidate_name}\n*Email:* {candidate_email}"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Draft Preview:*\n```{draft_preview[:500]}...```"
                    }
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "✅ Approve & Send"
                            },
                            "style": "primary",
                            "value": f"approve_{candidate_id}",
                            "action_id": "approve_email"
                        },
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "✏️ Edit Draft"
                            },
                            "value": f"edit_{candidate_id}",
                            "action_id": "edit_email"
                        },
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "❌ Reject"
                            },
                            "style": "danger",
                            "value": f"reject_{candidate_id}",
                            "action_id": "reject_email"
                        }
                    ]
                }
            ]
            
            response = self.client.chat_postMessage(
                channel=channel_id,
                text=f"Email draft ready for {candidate_name}. Approve?",
                blocks=blocks
            )
            
            logger.info(f"Sent approval request for {candidate_name}")
            return True
            
        except SlackApiError as e:
            logger.error(f"Error sending approval request: {e}")
            return False
    
    def send_notification(self, title: str, message: str) -> bool:
        """Send a formatted notification.
        
        Args:
            title: Notification title
            message: Notification message
            
        Returns:
            True if successful
        """
        if not self.client:
            logger.warning("Slack client not configured. Skipping notification.")
            return False
        
        try:
            channel_id = self.config.slack_channel_id
            
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": title
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": message
                    }
                }
            ]
            
            response = self.client.chat_postMessage(
                channel=channel_id,
                text=title,
                blocks=blocks
            )
            
            logger.info(f"Sent notification: {title}")
            return True
            
        except SlackApiError as e:
            logger.error(f"Error sending notification: {e}")
            return False
