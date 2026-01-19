#!/usr/bin/env python3
"""Command-line interface for Talent Scout."""
import argparse
import logging
import sys
import json
from pathlib import Path

from talent_scout.database.models import JobDescription
from talent_scout.orchestrator import run_full_pipeline, run_inbox_monitoring
from talent_scout.agents.recruiter_agent import approve_and_send_email

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_job_description(jd_path: str) -> JobDescription:
    """Load job description from JSON file."""
    with open(jd_path, 'r') as f:
        jd_data = json.load(f)
    
    return JobDescription(**jd_data)


def cmd_screen(args):
    """Run screening and ranking."""
    logger.info("Starting screening process...")
    
    # Load job description
    job_description = load_job_description(args.job_description)
    
    # Run pipeline
    results = run_full_pipeline(
        resume_folder=args.resume_folder,
        job_description=job_description,
        auto_draft=args.create_drafts
    )
    
    # Print summary
    print("\n" + "=" * 60)
    print("SCREENING RESULTS")
    print("=" * 60)
    
    for candidate in results['qualified_candidates']:
        print(f"\n✅ {candidate.name}")
        print(f"   Score: {candidate.fit_score}")
        print(f"   Email: {candidate.email or 'N/A'}")
        print(f"   Status: {candidate.status}")
    
    if results['drafts_created']:
        print("\n" + "=" * 60)
        print("DRAFTS CREATED")
        print("=" * 60)
        for draft in results['drafts_created']:
            print(f"✉️  {draft['candidate_name']} - Draft ID: {draft['draft_id']}")
    
    print("\n✨ Process complete! Check Gmail for drafts and Slack for approval requests.")


def cmd_monitor(args):
    """Monitor inbox for candidate replies."""
    logger.info("Starting inbox monitoring...")
    
    run_inbox_monitoring()
    
    print("\n✅ Inbox monitoring complete!")


def cmd_approve(args):
    """Approve and send an email draft."""
    logger.info(f"Approving and sending email for candidate {args.candidate_id}...")
    
    success = approve_and_send_email(args.candidate_id)
    
    if success:
        print(f"\n✅ Email sent successfully for candidate {args.candidate_id}")
    else:
        print(f"\n❌ Failed to send email for candidate {args.candidate_id}")
        sys.exit(1)


def cmd_create_sample_jd(args):
    """Create a sample job description file."""
    sample_jd = {
        "title": "Senior Software Engineer",
        "company": "Tech Innovations Inc.",
        "description": "We are seeking a talented Senior Software Engineer to join our team. The ideal candidate will have strong experience in backend development, cloud technologies, and leading technical projects.",
        "required_skills": [
            "Python",
            "Django",
            "AWS",
            "PostgreSQL",
            "REST APIs",
            "Docker",
            "Kubernetes"
        ],
        "preferred_skills": [
            "React",
            "TypeScript",
            "GraphQL",
            "Terraform",
            "CI/CD"
        ],
        "experience_required": "5+ years of professional software development experience",
        "education_required": "Bachelor's degree in Computer Science or related field"
    }
    
    output_path = args.output or "sample_job_description.json"
    
    with open(output_path, 'w') as f:
        json.dump(sample_jd, f, indent=2)
    
    print(f"\n✅ Sample job description created: {output_path}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Talent Scout - Autonomous Hiring Agent',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Screen resumes and create drafts
  python -m talent_scout.cli screen --resume-folder ./resumes --job-description job.json --create-drafts
  
  # Monitor inbox for replies
  python -m talent_scout.cli monitor
  
  # Approve and send an email
  python -m talent_scout.cli approve --candidate-id <uuid>
  
  # Create sample job description
  python -m talent_scout.cli create-sample-jd
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Screen command
    screen_parser = subparsers.add_parser('screen', help='Screen resumes and rank candidates')
    screen_parser.add_argument(
        '--resume-folder',
        required=True,
        help='Path to folder containing PDF resumes'
    )
    screen_parser.add_argument(
        '--job-description',
        required=True,
        help='Path to job description JSON file'
    )
    screen_parser.add_argument(
        '--create-drafts',
        action='store_true',
        help='Automatically create email drafts for qualified candidates'
    )
    screen_parser.set_defaults(func=cmd_screen)
    
    # Monitor command
    monitor_parser = subparsers.add_parser('monitor', help='Monitor inbox for candidate replies')
    monitor_parser.set_defaults(func=cmd_monitor)
    
    # Approve command
    approve_parser = subparsers.add_parser('approve', help='Approve and send email draft')
    approve_parser.add_argument(
        '--candidate-id',
        required=True,
        help='Candidate UUID to approve'
    )
    approve_parser.set_defaults(func=cmd_approve)
    
    # Create sample JD command
    sample_parser = subparsers.add_parser('create-sample-jd', help='Create sample job description file')
    sample_parser.add_argument(
        '--output',
        help='Output file path (default: sample_job_description.json)'
    )
    sample_parser.set_defaults(func=cmd_create_sample_jd)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    try:
        args.func(args)
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
