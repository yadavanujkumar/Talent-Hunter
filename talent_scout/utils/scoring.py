"""Utilities for calculating fit score using vector similarity."""
import logging
from typing import List
import json

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from talent_scout.database.models import ResumeData, JobDescription

logger = logging.getLogger(__name__)


def calculate_fit_score(resume_data: ResumeData, job_description: JobDescription) -> float:
    """Calculate fit score (0-100) using cosine similarity between resume and JD.
    
    Args:
        resume_data: Structured resume data
        job_description: Job description
        
    Returns:
        Fit score from 0 to 100
    """
    try:
        # Convert resume data to text representation
        resume_text = _resume_to_text(resume_data)
        
        # Convert job description to text representation
        jd_text = _job_description_to_text(job_description)
        
        # Calculate cosine similarity
        vectorizer = TfidfVectorizer(
            lowercase=True,
            stop_words='english',
            ngram_range=(1, 2)
        )
        
        # Fit and transform
        tfidf_matrix = vectorizer.fit_transform([resume_text, jd_text])
        
        # Calculate cosine similarity
        similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
        
        # Convert to 0-100 scale
        fit_score = round(similarity * 100, 2)
        
        logger.info(f"Calculated fit score: {fit_score}")
        return fit_score
        
    except Exception as e:
        logger.error(f"Error calculating fit score: {e}")
        raise


def _resume_to_text(resume_data: ResumeData) -> str:
    """Convert resume data to text for vector comparison."""
    parts = []
    
    # Skills
    if resume_data.skills:
        all_skills = (
            resume_data.skills.technical_skills + 
            resume_data.skills.soft_skills + 
            resume_data.skills.certifications
        )
        # Weight skills heavily by repeating them
        parts.extend(all_skills * 3)
    
    # Experience
    for exp in resume_data.experience:
        parts.append(exp.role)
        parts.append(exp.company)
        if exp.description:
            parts.append(exp.description)
        parts.extend(exp.projects)
    
    # Education
    for edu in resume_data.education:
        parts.append(edu.degree)
        parts.append(edu.field)
        parts.append(edu.institution)
    
    # Summary
    if resume_data.summary:
        parts.append(resume_data.summary)
    
    # Years of experience
    if resume_data.total_years_experience:
        parts.append(f"{resume_data.total_years_experience} years experience")
    
    return " ".join(parts)


def _job_description_to_text(job_description: JobDescription) -> str:
    """Convert job description to text for vector comparison."""
    parts = []
    
    # Title and company
    parts.append(job_description.title)
    parts.append(job_description.company)
    
    # Description
    parts.append(job_description.description)
    
    # Skills - weight heavily by repeating
    parts.extend(job_description.required_skills * 3)
    parts.extend(job_description.preferred_skills * 2)
    
    # Requirements
    if job_description.experience_required:
        parts.append(job_description.experience_required)
    
    if job_description.education_required:
        parts.append(job_description.education_required)
    
    return " ".join(parts)


def rank_candidates(resume_data_list: List[ResumeData], job_description: JobDescription) -> List[tuple]:
    """Rank multiple candidates by fit score.
    
    Args:
        resume_data_list: List of resume data
        job_description: Job description
        
    Returns:
        List of tuples (resume_data, fit_score) sorted by score descending
    """
    scored_candidates = []
    
    for resume_data in resume_data_list:
        fit_score = calculate_fit_score(resume_data, job_description)
        scored_candidates.append((resume_data, fit_score))
    
    # Sort by score descending
    scored_candidates.sort(key=lambda x: x[1], reverse=True)
    
    logger.info(f"Ranked {len(scored_candidates)} candidates")
    return scored_candidates
