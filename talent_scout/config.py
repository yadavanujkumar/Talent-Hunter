"""Configuration management for Talent Scout application."""
import os
from typing import Optional
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Load environment variables
load_dotenv()


class Config(BaseModel):
    """Application configuration."""
    
    # LLM Configuration
    llm_provider: str = Field(default=os.getenv("LLM_PROVIDER", "openai"))
    llm_model: str = Field(default=os.getenv("LLM_MODEL", "gpt-4o"))
    openai_api_key: Optional[str] = Field(default=os.getenv("OPENAI_API_KEY"))
    google_api_key: Optional[str] = Field(default=os.getenv("GOOGLE_API_KEY"))
    
    # Database Configuration
    supabase_url: Optional[str] = Field(default=os.getenv("SUPABASE_URL"))
    supabase_key: Optional[str] = Field(default=os.getenv("SUPABASE_KEY"))
    database_url: Optional[str] = Field(default=os.getenv("DATABASE_URL"))
    
    # Gmail API
    gmail_credentials_path: str = Field(
        default=os.getenv("GMAIL_CREDENTIALS_PATH", "credentials/gmail_credentials.json")
    )
    gmail_token_path: str = Field(
        default=os.getenv("GMAIL_TOKEN_PATH", "credentials/gmail_token.json")
    )
    
    # Google Calendar API
    calendar_credentials_path: str = Field(
        default=os.getenv("CALENDAR_CREDENTIALS_PATH", "credentials/calendar_credentials.json")
    )
    calendar_token_path: str = Field(
        default=os.getenv("CALENDAR_TOKEN_PATH", "credentials/calendar_token.json")
    )
    
    # Slack Configuration
    slack_bot_token: Optional[str] = Field(default=os.getenv("SLACK_BOT_TOKEN"))
    slack_channel_id: Optional[str] = Field(default=os.getenv("SLACK_CHANNEL_ID"))
    
    # Application Settings
    fit_score_threshold: int = Field(default=int(os.getenv("FIT_SCORE_THRESHOLD", "75")))
    recruiter_email: str = Field(default=os.getenv("RECRUITER_EMAIL", "recruiter@example.com"))
    recruiter_name: str = Field(default=os.getenv("RECRUITER_NAME", "Recruiter"))
    
    class Config:
        """Pydantic config."""
        env_file = ".env"


def get_config() -> Config:
    """Get application configuration."""
    return Config()
