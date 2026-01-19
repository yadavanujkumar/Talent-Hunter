"""Resume Screener Agent - Parses and ranks candidates."""
import logging
import os
from pathlib import Path
from typing import List, Annotated
import json

from langgraph.graph import StateGraph, END
from typing_extensions import TypedDict

from talent_scout.utils.resume_parser import parse_resume
from talent_scout.utils.scoring import calculate_fit_score
from talent_scout.database.models import JobDescription, Candidate, ResumeData
from talent_scout.database.db_manager import DatabaseManager
from talent_scout.config import get_config

logger = logging.getLogger(__name__)


class ScreenerState(TypedDict):
    """State for the screener agent."""
    resume_folder: str
    job_description: JobDescription
    processed_resumes: Annotated[List[dict], "List of processed resume data"]
    qualified_candidates: Annotated[List[Candidate], "Candidates above threshold"]
    error: str


def parse_resumes_node(state: ScreenerState) -> ScreenerState:
    """Parse all resumes in the folder."""
    logger.info("Starting resume parsing...")
    
    resume_folder = Path(state["resume_folder"])
    if not resume_folder.exists():
        state["error"] = f"Resume folder not found: {resume_folder}"
        return state
    
    processed_resumes = []
    
    # Find all PDF files
    pdf_files = list(resume_folder.glob("*.pdf"))
    logger.info(f"Found {len(pdf_files)} PDF resumes")
    
    for pdf_file in pdf_files:
        try:
            logger.info(f"Parsing {pdf_file.name}...")
            resume_data = parse_resume(str(pdf_file))
            
            processed_resumes.append({
                "file_name": pdf_file.name,
                "resume_data": resume_data
            })
            
        except Exception as e:
            logger.error(f"Error parsing {pdf_file.name}: {e}")
            continue
    
    state["processed_resumes"] = processed_resumes
    logger.info(f"Successfully parsed {len(processed_resumes)} resumes")
    
    return state


def calculate_scores_node(state: ScreenerState) -> ScreenerState:
    """Calculate fit scores for all candidates."""
    logger.info("Calculating fit scores...")
    
    config = get_config()
    job_description = state["job_description"]
    qualified_candidates = []
    
    for item in state["processed_resumes"]:
        resume_data: ResumeData = item["resume_data"]
        
        try:
            # Calculate fit score
            fit_score = calculate_fit_score(resume_data, job_description)
            
            logger.info(f"{resume_data.name}: Fit Score = {fit_score}")
            
            # Check if qualified
            if fit_score >= config.fit_score_threshold:
                candidate = Candidate(
                    name=resume_data.name,
                    email=resume_data.email,
                    phone=resume_data.phone,
                    resume_data=resume_data.model_dump(),
                    fit_score=fit_score,
                    job_description=job_description.model_dump_json(),
                    status="screened"
                )
                qualified_candidates.append(candidate)
                
        except Exception as e:
            logger.error(f"Error calculating score for {resume_data.name}: {e}")
            continue
    
    state["qualified_candidates"] = qualified_candidates
    logger.info(f"Found {len(qualified_candidates)} qualified candidates")
    
    return state


def save_to_database_node(state: ScreenerState) -> ScreenerState:
    """Save qualified candidates to database."""
    logger.info("Saving qualified candidates to database...")
    
    try:
        db_manager = DatabaseManager()
        
        for candidate in state["qualified_candidates"]:
            saved_candidate = db_manager.save_candidate(candidate)
            logger.info(f"Saved {saved_candidate.name} to database (ID: {saved_candidate.id})")
        
        logger.info(f"Successfully saved {len(state['qualified_candidates'])} candidates")
        
    except Exception as e:
        logger.error(f"Error saving to database: {e}")
        state["error"] = str(e)
    
    return state


def create_screener_agent():
    """Create the screener agent workflow."""
    workflow = StateGraph(ScreenerState)
    
    # Add nodes
    workflow.add_node("parse_resumes", parse_resumes_node)
    workflow.add_node("calculate_scores", calculate_scores_node)
    workflow.add_node("save_to_database", save_to_database_node)
    
    # Add edges
    workflow.set_entry_point("parse_resumes")
    workflow.add_edge("parse_resumes", "calculate_scores")
    workflow.add_edge("calculate_scores", "save_to_database")
    workflow.add_edge("save_to_database", END)
    
    return workflow.compile()


def run_screener(resume_folder: str, job_description: JobDescription) -> List[Candidate]:
    """Run the screener agent.
    
    Args:
        resume_folder: Path to folder containing PDF resumes
        job_description: Job description to match against
        
    Returns:
        List of qualified candidates
    """
    logger.info("Running Screener Agent...")
    
    agent = create_screener_agent()
    
    initial_state = {
        "resume_folder": resume_folder,
        "job_description": job_description,
        "processed_resumes": [],
        "qualified_candidates": [],
        "error": ""
    }
    
    result = agent.invoke(initial_state)
    
    if result.get("error"):
        logger.error(f"Screener error: {result['error']}")
        raise Exception(result["error"])
    
    return result["qualified_candidates"]
