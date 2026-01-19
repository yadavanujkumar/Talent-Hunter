"""Scheduler Agent - Monitors inbox and coordinates interviews."""
import logging
from typing import Annotated, List
import re
import base64
from datetime import datetime

from langgraph.graph import StateGraph, END
from typing_extensions import TypedDict
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate

from talent_scout.database.models import Candidate
from talent_scout.database.db_manager import DatabaseManager
from talent_scout.api_integrations.gmail_client import GmailClient
from talent_scout.api_integrations.calendar_client import CalendarClient
from talent_scout.api_integrations.slack_client import SlackClient
from talent_scout.config import get_config

logger = logging.getLogger(__name__)


class SchedulerState(TypedDict):
    """State for the scheduler agent."""
    candidate_email: str
    message_text: str
    intent: str  # interested, not_interested, schedule_time
    candidate: Candidate
    available_slots: List[dict]
    selected_slot: dict
    calendar_event: dict
    error: str


def get_llm():
    """Get configured LLM instance."""
    config = get_config()
    
    if config.llm_provider == "openai":
        return ChatOpenAI(
            model=config.llm_model,
            api_key=config.openai_api_key,
            temperature=0
        )
    elif config.llm_provider == "google":
        return ChatGoogleGenerativeAI(
            model=config.llm_model,
            google_api_key=config.google_api_key,
            temperature=0
        )
    else:
        raise ValueError(f"Unsupported LLM provider: {config.llm_provider}")


def detect_intent_node(state: SchedulerState) -> SchedulerState:
    """Detect intent from candidate's email reply."""
    logger.info(f"Detecting intent from email...")
    
    try:
        llm = get_llm()
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an email intent classifier. Analyze the email and determine the sender's intent.
            
Classify into ONE of these categories:
- interested: The candidate is interested and wants to proceed
- not_interested: The candidate is not interested or declines
- schedule_time: The candidate is picking a specific time slot

Respond with ONLY the category name, nothing else."""),
            ("human", "Email text:\n\n{message_text}")
        ])
        
        message = prompt.format_messages(message_text=state["message_text"])
        response = llm.invoke(message)
        
        intent = response.content.strip().lower()
        state["intent"] = intent
        
        logger.info(f"Detected intent: {intent}")
        
    except Exception as e:
        logger.error(f"Error detecting intent: {e}")
        state["error"] = str(e)
    
    return state


def get_candidate_node(state: SchedulerState) -> SchedulerState:
    """Get candidate from database by email."""
    logger.info(f"Looking up candidate by email: {state['candidate_email']}")
    
    try:
        db_manager = DatabaseManager()
        
        # Get all contacted candidates and find by email
        candidates = db_manager.get_candidates_by_status("contacted")
        
        for candidate in candidates:
            if candidate.email and candidate.email.lower() == state["candidate_email"].lower():
                state["candidate"] = candidate
                logger.info(f"Found candidate: {candidate.name}")
                return state
        
        state["error"] = f"Candidate not found with email: {state['candidate_email']}"
        
    except Exception as e:
        logger.error(f"Error getting candidate: {e}")
        state["error"] = str(e)
    
    return state


def handle_interested_node(state: SchedulerState) -> SchedulerState:
    """Handle interested response - get calendar slots and send options."""
    logger.info(f"Handling interested response for {state['candidate'].name}...")
    
    try:
        candidate = state["candidate"]
        
        # Get available calendar slots
        calendar_client = CalendarClient()
        available_slots = calendar_client.get_free_slots(days_ahead=7, duration_minutes=60)
        
        state["available_slots"] = available_slots
        
        # Generate email with time options
        slot_text = "\n".join([
            f"{i+1}. {slot['display']}"
            for i, slot in enumerate(available_slots)
        ])
        
        email_body = f"""Hi {candidate.name},

Great to hear from you! I'm excited to discuss this opportunity with you.

Here are some available times for our interview:

{slot_text}

Please reply with the number that works best for you, and I'll send you a calendar invite with a Google Meet link.

Looking forward to speaking with you!

Best regards,
{get_config().recruiter_name}"""
        
        # Send email
        gmail_client = GmailClient()
        gmail_client.send_email(
            to=candidate.email,
            subject=f"Re: Interview Times",
            body=email_body
        )
        
        # Update database
        db_manager = DatabaseManager()
        db_manager.update_candidate(
            candidate.id,
            {
                "status": "interested",
                "reply_received": True
            }
        )
        
        # Send Slack notification
        slack_client = SlackClient()
        slack_client.send_notification(
            title="📧 Candidate Interested",
            message=f"*{candidate.name}* replied with interest! Sent available time slots."
        )
        
        logger.info(f"Sent time slot options to {candidate.name}")
        
    except Exception as e:
        logger.error(f"Error handling interested response: {e}")
        state["error"] = str(e)
    
    return state


def handle_schedule_time_node(state: SchedulerState) -> SchedulerState:
    """Handle time selection - create calendar event."""
    logger.info(f"Handling schedule time for {state['candidate'].name}...")
    
    try:
        candidate = state["candidate"]
        message_text = state["message_text"]
        
        # Extract slot number from message
        match = re.search(r'\b([1-3])\b', message_text)
        
        if not match:
            # Try to get available slots again
            calendar_client = CalendarClient()
            available_slots = calendar_client.get_free_slots(days_ahead=7, duration_minutes=60)
            
            if available_slots:
                selected_slot = available_slots[0]
            else:
                state["error"] = "No available slots found"
                return state
        else:
            slot_number = int(match.group(1)) - 1
            
            # Get the slot (in practice, we'd retrieve from database or previous state)
            calendar_client = CalendarClient()
            available_slots = calendar_client.get_free_slots(days_ahead=7, duration_minutes=60)
            
            if slot_number < len(available_slots):
                selected_slot = available_slots[slot_number]
            else:
                selected_slot = available_slots[0]
        
        # Create calendar event
        job_info = candidate.job_description
        
        event = calendar_client.create_event(
            summary=f"Interview: {candidate.name}",
            start_time=selected_slot['start'],
            end_time=selected_slot['end'],
            attendee_email=candidate.email,
            description=f"Interview with {candidate.name} for position"
        )
        
        state["calendar_event"] = event
        
        # Extract meet link
        meet_link = event.get('hangoutLink', 'Will be provided')
        
        # Send confirmation email
        gmail_client = GmailClient()
        gmail_client.send_email(
            to=candidate.email,
            subject=f"Interview Scheduled - {selected_slot['display']}",
            body=f"""Hi {candidate.name},

Perfect! I've scheduled our interview for {selected_slot['display']}.

You should receive a calendar invite shortly. Here's the Google Meet link:
{meet_link}

Looking forward to our conversation!

Best regards,
{get_config().recruiter_name}"""
        )
        
        # Update database
        db_manager = DatabaseManager()
        db_manager.update_candidate(
            candidate.id,
            {
                "status": "scheduled",
                "interview_scheduled": True,
                "interview_time": datetime.fromisoformat(selected_slot['start'].replace('Z', '+00:00')),
                "calendar_event_id": event.get('id')
            }
        )
        
        # Send Slack notification
        slack_client = SlackClient()
        slack_client.send_notification(
            title="📅 Interview Scheduled",
            message=f"*{candidate.name}* interview scheduled for {selected_slot['display']}\nMeet link: {meet_link}"
        )
        
        logger.info(f"Created calendar event for {candidate.name}")
        
    except Exception as e:
        logger.error(f"Error scheduling interview: {e}")
        state["error"] = str(e)
    
    return state


def handle_not_interested_node(state: SchedulerState) -> SchedulerState:
    """Handle not interested response."""
    logger.info(f"Handling not interested response...")
    
    try:
        candidate = state["candidate"]
        
        # Update database
        db_manager = DatabaseManager()
        db_manager.update_candidate(
            candidate.id,
            {
                "status": "rejected",
                "reply_received": True
            }
        )
        
        # Send Slack notification
        slack_client = SlackClient()
        slack_client.send_notification(
            title="❌ Candidate Not Interested",
            message=f"*{candidate.name}* declined the opportunity."
        )
        
        logger.info(f"Marked {candidate.name} as not interested")
        
    except Exception as e:
        logger.error(f"Error handling not interested: {e}")
        state["error"] = str(e)
    
    return state


def route_by_intent(state: SchedulerState) -> str:
    """Route to appropriate handler based on intent."""
    intent = state.get("intent", "")
    
    if intent == "interested":
        return "handle_interested"
    elif intent == "schedule_time":
        return "handle_schedule_time"
    elif intent == "not_interested":
        return "handle_not_interested"
    else:
        return END


def create_scheduler_agent():
    """Create the scheduler agent workflow."""
    workflow = StateGraph(SchedulerState)
    
    # Add nodes
    workflow.add_node("detect_intent", detect_intent_node)
    workflow.add_node("get_candidate", get_candidate_node)
    workflow.add_node("handle_interested", handle_interested_node)
    workflow.add_node("handle_schedule_time", handle_schedule_time_node)
    workflow.add_node("handle_not_interested", handle_not_interested_node)
    
    # Add edges
    workflow.set_entry_point("detect_intent")
    workflow.add_edge("detect_intent", "get_candidate")
    workflow.add_conditional_edges(
        "get_candidate",
        route_by_intent,
        {
            "handle_interested": "handle_interested",
            "handle_schedule_time": "handle_schedule_time",
            "handle_not_interested": "handle_not_interested",
            END: END
        }
    )
    workflow.add_edge("handle_interested", END)
    workflow.add_edge("handle_schedule_time", END)
    workflow.add_edge("handle_not_interested", END)
    
    return workflow.compile()


def process_candidate_reply(candidate_email: str, message_text: str) -> dict:
    """Process a reply from a candidate.
    
    Args:
        candidate_email: Candidate's email address
        message_text: Text of the email message
        
    Returns:
        Result dict with status
    """
    logger.info(f"Processing reply from {candidate_email}...")
    
    agent = create_scheduler_agent()
    
    initial_state = {
        "candidate_email": candidate_email,
        "message_text": message_text,
        "intent": "",
        "candidate": None,
        "available_slots": [],
        "selected_slot": {},
        "calendar_event": {},
        "error": ""
    }
    
    result = agent.invoke(initial_state)
    
    if result.get("error"):
        logger.error(f"Scheduler error: {result['error']}")
        raise Exception(result["error"])
    
    return {
        "intent": result["intent"],
        "status": "processed"
    }


def monitor_inbox():
    """Monitor inbox for replies from candidates.
    
    This function should be called periodically to check for new messages.
    """
    logger.info("Monitoring inbox for candidate replies...")
    
    try:
        gmail_client = GmailClient()
        messages = gmail_client.get_recent_messages(max_results=20)
        
        db_manager = DatabaseManager()
        contacted_candidates = db_manager.get_candidates_by_status("contacted")
        interested_candidates = db_manager.get_candidates_by_status("interested")
        
        all_candidates = contacted_candidates + interested_candidates
        candidate_emails = {c.email.lower(): c for c in all_candidates if c.email}
        
        for message in messages:
            # Extract sender email
            headers = message.get('payload', {}).get('headers', [])
            from_header = next((h['value'] for h in headers if h['name'] == 'From'), None)
            
            if not from_header:
                continue
            
            # Extract email address
            email_match = re.search(r'<(.+?)>', from_header)
            sender_email = email_match.group(1) if email_match else from_header
            sender_email = sender_email.lower()
            
            # Check if from a candidate we contacted
            if sender_email in candidate_emails:
                # Extract message text
                parts = message.get('payload', {}).get('parts', [])
                message_text = ""
                
                if parts:
                    for part in parts:
                        if part.get('mimeType') == 'text/plain':
                            data = part.get('body', {}).get('data', '')
                            if data:
                                message_text = base64.urlsafe_b64decode(data).decode('utf-8')
                                break
                
                if not message_text:
                    # Try getting from body directly
                    data = message.get('payload', {}).get('body', {}).get('data', '')
                    if data:
                        message_text = base64.urlsafe_b64decode(data).decode('utf-8')
                
                if message_text:
                    logger.info(f"Found reply from {sender_email}")
                    process_candidate_reply(sender_email, message_text)
        
        logger.info("Inbox monitoring complete")
        
    except Exception as e:
        logger.error(f"Error monitoring inbox: {e}")
