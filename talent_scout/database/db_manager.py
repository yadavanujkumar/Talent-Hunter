"""Database connection and operations for Talent Scout."""
import logging
from typing import List, Optional
from datetime import datetime
import json

from supabase import create_client, Client

from talent_scout.config import get_config
from talent_scout.database.models import Candidate

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database operations for candidates."""
    
    def __init__(self):
        """Initialize database connection."""
        config = get_config()
        
        if config.supabase_url and config.supabase_key:
            self.client: Client = create_client(config.supabase_url, config.supabase_key)
            self.table_name = "candidates"
            logger.info("Connected to Supabase database")
        else:
            raise ValueError("Database credentials not configured. Set SUPABASE_URL and SUPABASE_KEY.")
    
    def create_table(self):
        """Create candidates table if it doesn't exist.
        
        Note: For Supabase, you should create the table via the dashboard or SQL editor:
        
        CREATE TABLE candidates (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            name TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            resume_data JSONB NOT NULL,
            fit_score FLOAT NOT NULL,
            job_description TEXT NOT NULL,
            status TEXT DEFAULT 'screened',
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW(),
            email_sent BOOLEAN DEFAULT FALSE,
            email_draft_id TEXT,
            reply_received BOOLEAN DEFAULT FALSE,
            interview_scheduled BOOLEAN DEFAULT FALSE,
            interview_time TIMESTAMP,
            calendar_event_id TEXT
        );
        """
        logger.info("Table creation should be done via Supabase dashboard")
    
    def save_candidate(self, candidate: Candidate) -> Candidate:
        """Save a candidate to the database."""
        try:
            candidate_dict = {
                "name": candidate.name,
                "email": candidate.email,
                "phone": candidate.phone,
                "resume_data": candidate.resume_data,
                "fit_score": candidate.fit_score,
                "job_description": candidate.job_description,
                "status": candidate.status,
                "email_sent": candidate.email_sent,
                "email_draft_id": candidate.email_draft_id,
                "reply_received": candidate.reply_received,
                "interview_scheduled": candidate.interview_scheduled,
                "interview_time": candidate.interview_time.isoformat() if candidate.interview_time else None,
                "calendar_event_id": candidate.calendar_event_id,
            }
            
            response = self.client.table(self.table_name).insert(candidate_dict).execute()
            
            if response.data:
                saved_data = response.data[0]
                candidate.id = saved_data.get("id")
                candidate.created_at = datetime.fromisoformat(saved_data.get("created_at").replace("Z", "+00:00"))
                logger.info(f"Saved candidate: {candidate.name} (ID: {candidate.id})")
                return candidate
            else:
                raise Exception("Failed to save candidate")
                
        except Exception as e:
            logger.error(f"Error saving candidate: {e}")
            raise
    
    def update_candidate(self, candidate_id: str, updates: dict) -> bool:
        """Update a candidate record."""
        try:
            updates["updated_at"] = datetime.utcnow().isoformat()
            response = self.client.table(self.table_name).update(updates).eq("id", candidate_id).execute()
            
            if response.data:
                logger.info(f"Updated candidate {candidate_id}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error updating candidate: {e}")
            raise
    
    def get_candidate(self, candidate_id: str) -> Optional[Candidate]:
        """Get a candidate by ID."""
        try:
            response = self.client.table(self.table_name).select("*").eq("id", candidate_id).execute()
            
            if response.data:
                data = response.data[0]
                return Candidate(
                    id=data.get("id"),
                    name=data.get("name"),
                    email=data.get("email"),
                    phone=data.get("phone"),
                    resume_data=data.get("resume_data"),
                    fit_score=data.get("fit_score"),
                    job_description=data.get("job_description"),
                    status=data.get("status"),
                    created_at=datetime.fromisoformat(data.get("created_at").replace("Z", "+00:00")) if data.get("created_at") else None,
                    updated_at=datetime.fromisoformat(data.get("updated_at").replace("Z", "+00:00")) if data.get("updated_at") else None,
                    email_sent=data.get("email_sent", False),
                    email_draft_id=data.get("email_draft_id"),
                    reply_received=data.get("reply_received", False),
                    interview_scheduled=data.get("interview_scheduled", False),
                    interview_time=datetime.fromisoformat(data.get("interview_time").replace("Z", "+00:00")) if data.get("interview_time") else None,
                    calendar_event_id=data.get("calendar_event_id"),
                )
            return None
            
        except Exception as e:
            logger.error(f"Error getting candidate: {e}")
            raise
    
    def get_candidates_by_status(self, status: str) -> List[Candidate]:
        """Get all candidates with a specific status."""
        try:
            response = self.client.table(self.table_name).select("*").eq("status", status).execute()
            
            candidates = []
            for data in response.data:
                candidates.append(Candidate(
                    id=data.get("id"),
                    name=data.get("name"),
                    email=data.get("email"),
                    phone=data.get("phone"),
                    resume_data=data.get("resume_data"),
                    fit_score=data.get("fit_score"),
                    job_description=data.get("job_description"),
                    status=data.get("status"),
                    created_at=datetime.fromisoformat(data.get("created_at").replace("Z", "+00:00")) if data.get("created_at") else None,
                    updated_at=datetime.fromisoformat(data.get("updated_at").replace("Z", "+00:00")) if data.get("updated_at") else None,
                    email_sent=data.get("email_sent", False),
                    email_draft_id=data.get("email_draft_id"),
                    reply_received=data.get("reply_received", False),
                    interview_scheduled=data.get("interview_scheduled", False),
                    interview_time=datetime.fromisoformat(data.get("interview_time").replace("Z", "+00:00")) if data.get("interview_time") else None,
                    calendar_event_id=data.get("calendar_event_id"),
                ))
            
            return candidates
            
        except Exception as e:
            logger.error(f"Error getting candidates by status: {e}")
            raise
    
    def get_qualified_candidates(self, threshold: float = 75) -> List[Candidate]:
        """Get all candidates with fit score above threshold."""
        try:
            response = self.client.table(self.table_name).select("*").gte("fit_score", threshold).execute()
            
            candidates = []
            for data in response.data:
                candidates.append(Candidate(
                    id=data.get("id"),
                    name=data.get("name"),
                    email=data.get("email"),
                    phone=data.get("phone"),
                    resume_data=data.get("resume_data"),
                    fit_score=data.get("fit_score"),
                    job_description=data.get("job_description"),
                    status=data.get("status"),
                    created_at=datetime.fromisoformat(data.get("created_at").replace("Z", "+00:00")) if data.get("created_at") else None,
                    updated_at=datetime.fromisoformat(data.get("updated_at").replace("Z", "+00:00")) if data.get("updated_at") else None,
                    email_sent=data.get("email_sent", False),
                    email_draft_id=data.get("email_draft_id"),
                    reply_received=data.get("reply_received", False),
                    interview_scheduled=data.get("interview_scheduled", False),
                    interview_time=datetime.fromisoformat(data.get("interview_time").replace("Z", "+00:00")) if data.get("interview_time") else None,
                    calendar_event_id=data.get("calendar_event_id"),
                ))
            
            return candidates
            
        except Exception as e:
            logger.error(f"Error getting qualified candidates: {e}")
            raise
