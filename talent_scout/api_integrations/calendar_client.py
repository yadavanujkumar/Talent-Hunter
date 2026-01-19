"""Google Calendar API integration for scheduling interviews."""
import logging
import os
from datetime import datetime, timedelta
from typing import List, Optional

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from talent_scout.config import get_config

logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/calendar']


class CalendarClient:
    """Google Calendar API client."""
    
    def __init__(self):
        """Initialize Calendar client."""
        self.config = get_config()
        self.service = None
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Google Calendar API."""
        creds = None
        
        # Check if token file exists
        if os.path.exists(self.config.calendar_token_path):
            creds = Credentials.from_authorized_user_file(
                self.config.calendar_token_path, SCOPES
            )
        
        # If no valid credentials, let user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(self.config.calendar_credentials_path):
                    raise FileNotFoundError(
                        f"Calendar credentials file not found at {self.config.calendar_credentials_path}. "
                        "Please download OAuth 2.0 credentials from Google Cloud Console."
                    )
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.config.calendar_credentials_path, SCOPES
                )
                creds = flow.run_local_server(port=0)
            
            # Save credentials for next run
            os.makedirs(os.path.dirname(self.config.calendar_token_path), exist_ok=True)
            with open(self.config.calendar_token_path, 'w') as token:
                token.write(creds.to_json())
        
        self.service = build('calendar', 'v3', credentials=creds)
        logger.info("Authenticated with Google Calendar API")
    
    def get_free_slots(self, days_ahead: int = 7, duration_minutes: int = 60) -> List[dict]:
        """Get available time slots in the calendar.
        
        Args:
            days_ahead: Number of days to look ahead
            duration_minutes: Duration of meeting slot
            
        Returns:
            List of available time slots with start and end times
        """
        try:
            # Get current time and end time
            now = datetime.utcnow()
            time_min = now.isoformat() + 'Z'
            time_max = (now + timedelta(days=days_ahead)).isoformat() + 'Z'
            
            # Get busy times
            body = {
                "timeMin": time_min,
                "timeMax": time_max,
                "items": [{"id": "primary"}]
            }
            
            events_result = self.service.freebusy().query(body=body).execute()
            busy_times = events_result['calendars']['primary']['busy']
            
            # Generate potential slots (9 AM - 5 PM on weekdays)
            available_slots = []
            current_date = now.date()
            
            for day_offset in range(days_ahead):
                check_date = current_date + timedelta(days=day_offset)
                
                # Skip weekends
                if check_date.weekday() >= 5:
                    continue
                
                # Check slots from 9 AM to 5 PM
                for hour in range(9, 17):
                    slot_start = datetime.combine(check_date, datetime.min.time()).replace(hour=hour)
                    slot_end = slot_start + timedelta(minutes=duration_minutes)
                    
                    # Skip past slots
                    if slot_start < now:
                        continue
                    
                    # Check if slot overlaps with busy times
                    is_free = True
                    for busy in busy_times:
                        busy_start = datetime.fromisoformat(busy['start'].replace('Z', '+00:00'))
                        busy_end = datetime.fromisoformat(busy['end'].replace('Z', '+00:00'))
                        
                        if (slot_start < busy_end and slot_end > busy_start):
                            is_free = False
                            break
                    
                    if is_free:
                        available_slots.append({
                            'start': slot_start.isoformat() + 'Z',
                            'end': slot_end.isoformat() + 'Z',
                            'display': slot_start.strftime('%A, %B %d at %I:%M %p')
                        })
                
                # Limit to 3 slots
                if len(available_slots) >= 3:
                    break
            
            logger.info(f"Found {len(available_slots)} available slots")
            return available_slots[:3]
            
        except Exception as e:
            logger.error(f"Error getting free slots: {e}")
            raise
    
    def create_event(
        self, 
        summary: str, 
        start_time: str, 
        end_time: str, 
        attendee_email: str,
        description: Optional[str] = None
    ) -> dict:
        """Create a calendar event with Google Meet link.
        
        Args:
            summary: Event title
            start_time: Start time (ISO format with Z)
            end_time: End time (ISO format with Z)
            attendee_email: Attendee email address
            description: Event description
            
        Returns:
            Event object with meet link
        """
        try:
            event = {
                'summary': summary,
                'description': description or '',
                'start': {
                    'dateTime': start_time,
                    'timeZone': 'UTC',
                },
                'end': {
                    'dateTime': end_time,
                    'timeZone': 'UTC',
                },
                'attendees': [
                    {'email': attendee_email},
                ],
                'conferenceData': {
                    'createRequest': {
                        'requestId': f"meet-{datetime.utcnow().timestamp()}",
                        'conferenceSolutionKey': {'type': 'hangoutsMeet'}
                    }
                },
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'email', 'minutes': 24 * 60},
                        {'method': 'popup', 'minutes': 30},
                    ],
                },
            }
            
            event = self.service.events().insert(
                calendarId='primary',
                body=event,
                conferenceDataVersion=1,
                sendUpdates='all'
            ).execute()
            
            logger.info(f"Created calendar event: {event.get('id')}")
            return event
            
        except Exception as e:
            logger.error(f"Error creating event: {e}")
            raise
