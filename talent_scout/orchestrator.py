"""Main orchestration module for Talent Scout."""
import logging
from typing import List

from talent_scout.database.models import JobDescription, Candidate
from talent_scout.agents.screener_agent import run_screener
from talent_scout.agents.recruiter_agent import run_recruiter
from talent_scout.agents.scheduler_agent import monitor_inbox

logger = logging.getLogger(__name__)


def run_full_pipeline(resume_folder: str, job_description: JobDescription, auto_draft: bool = True) -> dict:
    """Run the full recruitment pipeline.
    
    Args:
        resume_folder: Path to folder with PDF resumes
        job_description: Job description to match
        auto_draft: Whether to automatically create drafts for qualified candidates
        
    Returns:
        Dictionary with results
    """
    logger.info("Starting full Talent Scout pipeline...")
    
    results = {
        "screened_candidates": [],
        "qualified_candidates": [],
        "drafts_created": []
    }
    
    try:
        # Phase 1: Screen and rank candidates
        logger.info("=" * 60)
        logger.info("PHASE 1: SCREENING & RANKING")
        logger.info("=" * 60)
        
        qualified_candidates = run_screener(resume_folder, job_description)
        results["qualified_candidates"] = qualified_candidates
        
        logger.info(f"\n✅ Found {len(qualified_candidates)} qualified candidates")
        
        # Phase 2: Create outreach for qualified candidates
        if auto_draft and qualified_candidates:
            logger.info("\n" + "=" * 60)
            logger.info("PHASE 2: PERSONALIZED OUTREACH")
            logger.info("=" * 60)
            
            for candidate in qualified_candidates:
                try:
                    logger.info(f"\nProcessing {candidate.name} (Score: {candidate.fit_score})...")
                    
                    draft_result = run_recruiter(candidate)
                    results["drafts_created"].append({
                        "candidate_name": candidate.name,
                        "draft_id": draft_result["draft_id"]
                    })
                    
                    logger.info(f"✅ Created draft for {candidate.name}")
                    
                except Exception as e:
                    logger.error(f"Failed to create draft for {candidate.name}: {e}")
                    continue
            
            logger.info(f"\n✅ Created {len(results['drafts_created'])} email drafts")
        
        logger.info("\n" + "=" * 60)
        logger.info("PIPELINE COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Qualified Candidates: {len(results['qualified_candidates'])}")
        logger.info(f"Drafts Created: {len(results['drafts_created'])}")
        logger.info("\nNext steps:")
        logger.info("1. Review email drafts in Gmail")
        logger.info("2. Approve drafts via Slack notifications")
        logger.info("3. Run inbox monitoring to handle replies")
        
        return results
        
    except Exception as e:
        logger.error(f"Pipeline error: {e}")
        raise


def run_inbox_monitoring():
    """Run the inbox monitoring agent.
    
    This should be run periodically to check for candidate replies.
    """
    logger.info("Starting inbox monitoring...")
    
    try:
        monitor_inbox()
        logger.info("✅ Inbox monitoring complete")
        
    except Exception as e:
        logger.error(f"Inbox monitoring error: {e}")
        raise
