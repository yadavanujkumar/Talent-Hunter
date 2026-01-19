"""Database models and schema for Talent Scout."""
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field


class CandidateSkills(BaseModel):
    """Candidate skills extracted from resume."""
    technical_skills: List[str] = Field(default_factory=list)
    soft_skills: List[str] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list)


class CandidateExperience(BaseModel):
    """Candidate work experience."""
    company: str
    role: str
    duration: str
    description: Optional[str] = None
    projects: List[str] = Field(default_factory=list)


class CandidateEducation(BaseModel):
    """Candidate education."""
    institution: str
    degree: str
    field: str
    year: Optional[str] = None


class ResumeData(BaseModel):
    """Structured resume data extracted from PDF."""
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    skills: CandidateSkills
    experience: List[CandidateExperience] = Field(default_factory=list)
    education: List[CandidateEducation] = Field(default_factory=list)
    summary: Optional[str] = None
    total_years_experience: Optional[float] = None


class Candidate(BaseModel):
    """Candidate database model."""
    id: Optional[str] = None
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    resume_data: Dict[str, Any]
    fit_score: float
    job_description: str
    status: str = Field(default="screened")  # screened, contacted, interested, scheduled, hired, rejected
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    # Outreach tracking
    email_sent: bool = Field(default=False)
    email_draft_id: Optional[str] = None
    reply_received: bool = Field(default=False)
    
    # Interview tracking
    interview_scheduled: bool = Field(default=False)
    interview_time: Optional[datetime] = None
    calendar_event_id: Optional[str] = None


class JobDescription(BaseModel):
    """Job description model."""
    title: str
    company: str
    description: str
    required_skills: List[str] = Field(default_factory=list)
    preferred_skills: List[str] = Field(default_factory=list)
    experience_required: Optional[str] = None
    education_required: Optional[str] = None
