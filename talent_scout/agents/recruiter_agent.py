"""Recruiter Agent - Generates personalized emails and manages outreach."""
import logging
from typing import Annotated
import json

from langgraph.graph import StateGraph, END
from typing_extensions import TypedDict
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate

from talent_scout.database.models import Candidate
from talent_scout.database.db_manager import DatabaseManager
from talent_scout.api_integrations.gmail_client import GmailClient
from talent_scout.api_integrations.slack_client import SlackClient
from talent_scout.config import get_config

logger = logging.getLogger(__name__)


class RecruiterState(TypedDict):
    """State for the recruiter agent."""
    candidate: Candidate
    email_subject: str
    email_body: str
    draft_id: str
    approved: bool
    error: str


def get_llm():
    """Get configured LLM instance."""
    config = get_config()
    
    if config.llm_provider == "openai":
        return ChatOpenAI(
            model=config.llm_model,
            api_key=config.openai_api_key,
            temperature=0.7
        )
    elif config.llm_provider == "google":
        return ChatGoogleGenerativeAI(
            model=config.llm_model,
            google_api_key=config.google_api_key,
            temperature=0.7
        )
    else:
        raise ValueError(f"Unsupported LLM provider: {config.llm_provider}")


def generate_email_node(state: RecruiterState) -> RecruiterState:
    """Generate personalized email for candidate."""
    logger.info(f"Generating personalized email for {state['candidate'].name}...")
    
    try:
        candidate = state["candidate"]
        config = get_config()
        llm = get_llm()
        
        # Extract key information from resume
        resume_data = candidate.resume_data
        experience = resume_data.get("experience", [])
        skills = resume_data.get("skills", {})
        
        # Find notable projects
        notable_projects = []
        for exp in experience:
            if exp.get("projects"):
                notable_projects.extend(exp["projects"][:2])
        
        # Create prompt for personalized email
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert recruiter writing personalized cold outreach emails to candidates.
            
Write a warm, professional, and personalized email that:
1. References specific projects or achievements from their experience
2. Explains why they're a great fit for the role
3. Invites them to discuss the opportunity
4. Is concise (under 200 words)
5. Sounds genuine and personal, not templated

Use a friendly but professional tone."""),
            ("human", """Write a personalized outreach email for this candidate:

Candidate Name: {name}
Fit Score: {fit_score}
Key Skills: {skills}
Notable Projects: {projects}
Years of Experience: {experience}

Recruiter Name: {recruiter_name}
Recruiter Email: {recruiter_email}

Job Description:
{job_description}

Generate ONLY the email body (no subject line).""")
        ])
        
        # Format message
        message = prompt.format_messages(
            name=candidate.name,
            fit_score=candidate.fit_score,
            skills=", ".join(skills.get("technical_skills", [])[:5]),
            projects=", ".join(notable_projects[:3]) if notable_projects else "various interesting projects",
            experience=resume_data.get("total_years_experience", "several years"),
            recruiter_name=config.recruiter_name,
            recruiter_email=config.recruiter_email,
            job_description=candidate.job_description
        )
        
        # Generate email
        response = llm.invoke(message)
        email_body = response.content
        
        # Generate subject
        job_info = json.loads(candidate.job_description)
        email_subject = f"Exciting {job_info.get('title', 'Opportunity')} at {job_info.get('company', 'Our Company')}"
        
        state["email_subject"] = email_subject
        state["email_body"] = email_body
        
        logger.info(f"Generated personalized email for {candidate.name}")
        
    except Exception as e:
        logger.error(f"Error generating email: {e}")
        state["error"] = str(e)
    
    return state


def create_draft_node(state: RecruiterState) -> RecruiterState:
    """Create draft email in Gmail."""
    logger.info(f"Creating draft email for {state['candidate'].name}...")
    
    try:
        candidate = state["candidate"]
        
        if not candidate.email:
            state["error"] = "Candidate email not available"
            return state
        
        gmail_client = GmailClient()
        
        draft_id = gmail_client.create_draft(
            to=candidate.email,
            subject=state["email_subject"],
            body=state["email_body"]
        )
        
        state["draft_id"] = draft_id
        
        # Update database
        db_manager = DatabaseManager()
        db_manager.update_candidate(
            candidate.id,
            {"email_draft_id": draft_id}
        )
        
        logger.info(f"Created draft {draft_id} for {candidate.name}")
        
    except Exception as e:
        logger.error(f"Error creating draft: {e}")
        state["error"] = str(e)
    
    return state


def send_slack_notification_node(state: RecruiterState) -> RecruiterState:
    """Send Slack notification for approval."""
    logger.info(f"Sending Slack approval request for {state['candidate'].name}...")
    
    try:
        candidate = state["candidate"]
        
        slack_client = SlackClient()
        slack_client.send_approval_request(
            candidate_name=candidate.name,
            candidate_email=candidate.email or "N/A",
            draft_preview=state["email_body"],
            candidate_id=candidate.id
        )
        
        logger.info(f"Sent approval request for {candidate.name}")
        
    except Exception as e:
        logger.error(f"Error sending Slack notification: {e}")
        # Don't set error - continue even if Slack fails
    
    return state


def create_recruiter_agent():
    """Create the recruiter agent workflow."""
    workflow = StateGraph(RecruiterState)
    
    # Add nodes
    workflow.add_node("generate_email", generate_email_node)
    workflow.add_node("create_draft", create_draft_node)
    workflow.add_node("send_notification", send_slack_notification_node)
    
    # Add edges
    workflow.set_entry_point("generate_email")
    workflow.add_edge("generate_email", "create_draft")
    workflow.add_edge("create_draft", "send_notification")
    workflow.add_edge("send_notification", END)
    
    return workflow.compile()


def run_recruiter(candidate: Candidate) -> dict:
    """Run the recruiter agent for a candidate.
    
    Args:
        candidate: Candidate to create outreach for
        
    Returns:
        Result dict with draft_id and status
    """
    logger.info(f"Running Recruiter Agent for {candidate.name}...")
    
    agent = create_recruiter_agent()
    
    initial_state = {
        "candidate": candidate,
        "email_subject": "",
        "email_body": "",
        "draft_id": "",
        "approved": False,
        "error": ""
    }
    
    result = agent.invoke(initial_state)
    
    if result.get("error"):
        logger.error(f"Recruiter error: {result['error']}")
        raise Exception(result["error"])
    
    return {
        "draft_id": result["draft_id"],
        "email_subject": result["email_subject"],
        "email_body": result["email_body"]
    }


def approve_and_send_email(candidate_id: str) -> bool:
    """Approve and send email draft for a candidate.
    
    Args:
        candidate_id: Candidate ID
        
    Returns:
        True if successful
    """
    try:
        db_manager = DatabaseManager()
        candidate = db_manager.get_candidate(candidate_id)
        
        if not candidate or not candidate.email_draft_id:
            logger.error(f"No draft found for candidate {candidate_id}")
            return False
        
        # Send the draft
        gmail_client = GmailClient()
        gmail_client.send_draft(candidate.email_draft_id)
        
        # Update database
        db_manager.update_candidate(
            candidate_id,
            {
                "email_sent": True,
                "status": "contacted"
            }
        )
        
        # Send Slack notification
        slack_client = SlackClient()
        slack_client.send_notification(
            title="✅ Email Sent",
            message=f"Successfully sent email to *{candidate.name}* ({candidate.email})"
        )
        
        logger.info(f"Sent email to {candidate.name}")
        return True
        
    except Exception as e:
        logger.error(f"Error approving and sending email: {e}")
        return False
