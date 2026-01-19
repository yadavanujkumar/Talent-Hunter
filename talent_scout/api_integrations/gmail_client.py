"""Gmail API integration for sending emails."""
import logging
import os
import base64
from typing import Optional
from email.mime.text import MIMEText

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from talent_scout.config import get_config

logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/gmail.compose', 
          'https://www.googleapis.com/auth/gmail.modify']


class GmailClient:
    """Gmail API client for sending emails."""
    
    def __init__(self):
        """Initialize Gmail client."""
        self.config = get_config()
        self.service = None
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Gmail API."""
        creds = None
        
        # Check if token file exists
        if os.path.exists(self.config.gmail_token_path):
            creds = Credentials.from_authorized_user_file(
                self.config.gmail_token_path, SCOPES
            )
        
        # If no valid credentials, let user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(self.config.gmail_credentials_path):
                    raise FileNotFoundError(
                        f"Gmail credentials file not found at {self.config.gmail_credentials_path}. "
                        "Please download OAuth 2.0 credentials from Google Cloud Console."
                    )
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.config.gmail_credentials_path, SCOPES
                )
                creds = flow.run_local_server(port=0)
            
            # Save credentials for next run
            os.makedirs(os.path.dirname(self.config.gmail_token_path), exist_ok=True)
            with open(self.config.gmail_token_path, 'w') as token:
                token.write(creds.to_json())
        
        self.service = build('gmail', 'v1', credentials=creds)
        logger.info("Authenticated with Gmail API")
    
    def create_draft(self, to: str, subject: str, body: str) -> str:
        """Create a draft email.
        
        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body (plain text)
            
        Returns:
            Draft ID
        """
        try:
            message = MIMEText(body)
            message['to'] = to
            message['subject'] = subject
            message['from'] = self.config.recruiter_email
            
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            
            draft = self.service.users().drafts().create(
                userId='me',
                body={'message': {'raw': raw_message}}
            ).execute()
            
            draft_id = draft['id']
            logger.info(f"Created draft email for {to} (Draft ID: {draft_id})")
            return draft_id
            
        except Exception as e:
            logger.error(f"Error creating draft: {e}")
            raise
    
    def send_draft(self, draft_id: str) -> bool:
        """Send a draft email.
        
        Args:
            draft_id: Draft ID to send
            
        Returns:
            True if successful
        """
        try:
            self.service.users().drafts().send(
                userId='me',
                body={'id': draft_id}
            ).execute()
            
            logger.info(f"Sent draft {draft_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending draft: {e}")
            raise
    
    def send_email(self, to: str, subject: str, body: str) -> bool:
        """Send an email directly.
        
        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body (plain text)
            
        Returns:
            True if successful
        """
        try:
            message = MIMEText(body)
            message['to'] = to
            message['subject'] = subject
            message['from'] = self.config.recruiter_email
            
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            
            self.service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()
            
            logger.info(f"Sent email to {to}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            raise
    
    def get_recent_messages(self, max_results: int = 10) -> list:
        """Get recent messages from inbox.
        
        Args:
            max_results: Maximum number of messages to retrieve
            
        Returns:
            List of message objects
        """
        try:
            results = self.service.users().messages().list(
                userId='me',
                maxResults=max_results,
                labelIds=['INBOX']
            ).execute()
            
            messages = results.get('messages', [])
            
            detailed_messages = []
            for message in messages:
                msg = self.service.users().messages().get(
                    userId='me',
                    id=message['id'],
                    format='full'
                ).execute()
                detailed_messages.append(msg)
            
            logger.info(f"Retrieved {len(detailed_messages)} recent messages")
            return detailed_messages
            
        except Exception as e:
            logger.error(f"Error getting messages: {e}")
            raise
