#!/usr/bin/env python3
"""
Test script to validate Talent-Scout installation and configuration.
Run this to check if all dependencies and configurations are set up correctly.
"""
import sys
import os
from pathlib import Path

def test_imports():
    """Test if all required packages can be imported."""
    print("Testing package imports...")
    
    packages = [
        ('langgraph', 'LangGraph'),
        ('langchain', 'LangChain'),
        ('openai', 'OpenAI'),
        ('google.generativeai', 'Google Generative AI'),
        ('sklearn', 'scikit-learn'),
        ('pdfplumber', 'pdfplumber'),
        ('supabase', 'Supabase'),
        ('googleapiclient', 'Google API Client'),
        ('slack_sdk', 'Slack SDK'),
        ('dotenv', 'python-dotenv'),
        ('pydantic', 'Pydantic'),
    ]
    
    failed = []
    for module_name, display_name in packages:
        try:
            __import__(module_name)
            print(f"  ✅ {display_name}")
        except ImportError as e:
            print(f"  ❌ {display_name}: {e}")
            failed.append(display_name)
    
    if failed:
        print(f"\n❌ Failed to import: {', '.join(failed)}")
        print("   Run: pip install -r requirements.txt")
        return False
    
    print("\n✅ All packages imported successfully!")
    return True


def test_talent_scout_modules():
    """Test if Talent-Scout modules can be imported."""
    print("\nTesting Talent-Scout modules...")
    
    modules = [
        'talent_scout.config',
        'talent_scout.database.models',
        'talent_scout.database.db_manager',
        'talent_scout.utils.resume_parser',
        'talent_scout.utils.scoring',
        'talent_scout.api_integrations.gmail_client',
        'talent_scout.api_integrations.calendar_client',
        'talent_scout.api_integrations.slack_client',
        'talent_scout.agents.screener_agent',
        'talent_scout.agents.recruiter_agent',
        'talent_scout.agents.scheduler_agent',
        'talent_scout.orchestrator',
        'talent_scout.cli',
    ]
    
    failed = []
    for module_name in modules:
        try:
            __import__(module_name)
            print(f"  ✅ {module_name}")
        except Exception as e:
            print(f"  ❌ {module_name}: {e}")
            failed.append(module_name)
    
    if failed:
        print(f"\n❌ Failed to import Talent-Scout modules: {', '.join(failed)}")
        return False
    
    print("\n✅ All Talent-Scout modules loaded successfully!")
    return True


def test_env_file():
    """Check if .env file exists."""
    print("\nChecking environment configuration...")
    
    env_path = Path('.env')
    if not env_path.exists():
        print("  ⚠️  .env file not found")
        print("     Run: cp .env.example .env")
        print("     Then edit .env with your API keys")
        return False
    
    print("  ✅ .env file exists")
    return True


def test_config():
    """Test configuration loading."""
    print("\nTesting configuration...")
    
    try:
        from talent_scout.config import get_config
        config = get_config()
        
        print(f"  LLM Provider: {config.llm_provider}")
        print(f"  LLM Model: {config.llm_model}")
        
        warnings = []
        
        if config.llm_provider == "openai" and not config.openai_api_key:
            warnings.append("OpenAI API key not set")
        
        if config.llm_provider == "google" and not config.google_api_key:
            warnings.append("Google API key not set")
        
        if not config.supabase_url or not config.supabase_key:
            warnings.append("Supabase credentials not set")
        
        if not config.slack_bot_token:
            warnings.append("Slack token not set (optional)")
        
        if warnings:
            print("\n  ⚠️  Configuration warnings:")
            for warning in warnings:
                print(f"     - {warning}")
        else:
            print("\n  ✅ Configuration looks good!")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Error loading configuration: {e}")
        return False


def test_credentials_directory():
    """Check if credentials directory exists."""
    print("\nChecking credentials directory...")
    
    creds_dir = Path('credentials')
    if not creds_dir.exists():
        print("  ⚠️  credentials/ directory not found")
        print("     Run: mkdir credentials")
        return False
    
    print("  ✅ credentials/ directory exists")
    
    gmail_creds = creds_dir / 'gmail_credentials.json'
    calendar_creds = creds_dir / 'calendar_credentials.json'
    
    if not gmail_creds.exists():
        print("  ⚠️  credentials/gmail_credentials.json not found")
        print("     Download OAuth credentials from Google Cloud Console")
    else:
        print("  ✅ Gmail credentials found")
    
    if not calendar_creds.exists():
        print("  ⚠️  credentials/calendar_credentials.json not found")
        print("     Download OAuth credentials from Google Cloud Console")
    else:
        print("  ✅ Calendar credentials found")
    
    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("Talent-Scout Installation Test")
    print("=" * 60)
    
    results = []
    
    results.append(("Package Imports", test_imports()))
    results.append(("Talent-Scout Modules", test_talent_scout_modules()))
    results.append(("Environment File", test_env_file()))
    results.append(("Configuration", test_config()))
    results.append(("Credentials Directory", test_credentials_directory()))
    
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")
    
    all_passed = all(result[1] for result in results)
    
    if all_passed:
        print("\n🎉 All tests passed! Talent-Scout is ready to use.")
        print("\nNext steps:")
        print("  1. Create a job description: python -m talent_scout create-sample-jd")
        print("  2. Add PDF resumes to a folder")
        print("  3. Run screening: python -m talent_scout screen --resume-folder ./resumes --job-description job.json")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please address the issues above.")
        print("   See QUICKSTART.md for detailed setup instructions.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
