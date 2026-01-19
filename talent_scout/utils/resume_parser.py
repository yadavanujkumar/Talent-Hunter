"""Utilities for parsing PDF resumes and extracting structured data."""
import logging
from typing import Optional
import json

import pdfplumber
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser

from talent_scout.config import get_config
from talent_scout.database.models import ResumeData, CandidateSkills, CandidateExperience, CandidateEducation

logger = logging.getLogger(__name__)


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text content from a PDF file."""
    try:
        text = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        
        logger.info(f"Extracted {len(text)} characters from {pdf_path}")
        return text.strip()
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {e}")
        raise


def get_llm():
    """Get configured LLM instance."""
    config = get_config()
    
    if config.llm_provider == "openai":
        if not config.openai_api_key:
            raise ValueError("OpenAI API key not configured")
        return ChatOpenAI(
            model=config.llm_model,
            api_key=config.openai_api_key,
            temperature=0
        )
    elif config.llm_provider == "google":
        if not config.google_api_key:
            raise ValueError("Google API key not configured")
        return ChatGoogleGenerativeAI(
            model=config.llm_model,
            google_api_key=config.google_api_key,
            temperature=0
        )
    else:
        raise ValueError(f"Unsupported LLM provider: {config.llm_provider}")


def parse_resume_with_llm(resume_text: str) -> ResumeData:
    """Parse resume text using LLM to extract structured data."""
    try:
        llm = get_llm()
        
        # Create output parser
        parser = PydanticOutputParser(pydantic_object=ResumeData)
        
        # Create prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert resume parser. Extract structured information from the resume text.
            
Be thorough and accurate. Extract:
- Full name
- Contact information (email, phone)
- Technical and soft skills
- Work experience with companies, roles, durations, and notable projects
- Education details
- Professional summary
- Estimated total years of professional experience

{format_instructions}"""),
            ("human", "Resume text:\n\n{resume_text}")
        ])
        
        # Format prompt
        formatted_prompt = prompt.format_messages(
            format_instructions=parser.get_format_instructions(),
            resume_text=resume_text
        )
        
        # Get response from LLM
        response = llm.invoke(formatted_prompt)
        
        # Parse response
        resume_data = parser.parse(response.content)
        
        logger.info(f"Successfully parsed resume for {resume_data.name}")
        return resume_data
        
    except Exception as e:
        logger.error(f"Error parsing resume with LLM: {e}")
        raise


def parse_resume(pdf_path: str) -> ResumeData:
    """Main function to parse a PDF resume into structured data."""
    # Extract text from PDF
    resume_text = extract_text_from_pdf(pdf_path)
    
    # Parse with LLM
    resume_data = parse_resume_with_llm(resume_text)
    
    return resume_data
