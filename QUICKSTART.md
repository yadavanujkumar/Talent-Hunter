# Quick Start Guide for Talent-Scout

This guide will help you get Talent-Scout up and running quickly.

## Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

## Step 2: Set Up Environment Variables

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Edit `.env` and fill in your credentials:

### LLM Configuration (Choose One)

**Option A: OpenAI**
```
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o
OPENAI_API_KEY=sk-your-key-here
```

**Option B: Google Gemini**
```
LLM_PROVIDER=google
LLM_MODEL=gemini-1.5-pro
GOOGLE_API_KEY=your-key-here
```

### Database Configuration (Supabase)

```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key-here
```

## Step 3: Set Up Google APIs

### Gmail API Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable Gmail API:
   - Navigate to "APIs & Services" > "Library"
   - Search for "Gmail API"
   - Click "Enable"
4. Create credentials:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - Choose "Desktop app"
   - Download the JSON file
5. Save the file as `credentials/gmail_credentials.json`

### Google Calendar API Setup

1. In the same Google Cloud project
2. Enable Google Calendar API:
   - Navigate to "APIs & Services" > "Library"
   - Search for "Google Calendar API"
   - Click "Enable"
3. Use the same OAuth credentials or create new ones
4. Save as `credentials/calendar_credentials.json`

**Note:** You can use the same credentials file for both Gmail and Calendar.

## Step 4: Set Up Supabase Database

1. Go to [supabase.com](https://supabase.com) and create a project
2. In the SQL Editor, run:

```sql
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

-- Create indexes for better performance
CREATE INDEX idx_candidates_status ON candidates(status);
CREATE INDEX idx_candidates_fit_score ON candidates(fit_score);
CREATE INDEX idx_candidates_email ON candidates(email);
```

3. Copy your project URL and anon key to `.env`

## Step 5: Set Up Slack (Optional)

1. Go to [api.slack.com/apps](https://api.slack.com/apps)
2. Click "Create New App" > "From scratch"
3. Add Bot Token Scopes:
   - `chat:write`
   - `chat:write.public`
4. Install app to workspace
5. Copy "Bot User OAuth Token" to `.env` as `SLACK_BOT_TOKEN`
6. Copy the channel ID where you want notifications to `.env` as `SLACK_CHANNEL_ID`

## Step 6: Create Job Description

Create a sample job description:

```bash
python -m talent_scout create-sample-jd --output job.json
```

Edit `job.json` to match your requirements.

## Step 7: Prepare Resumes

1. Create a folder for resumes:
```bash
mkdir resumes
```

2. Add PDF resumes to the folder

## Step 8: Run the Screener

```bash
python -m talent_scout screen \
  --resume-folder ./resumes \
  --job-description job.json \
  --create-drafts
```

## Step 9: First-Time Authentication

The first time you run the tool:

1. **Gmail/Calendar**: A browser window will open for OAuth authentication
   - Log in with your Google account
   - Grant the requested permissions
   - Tokens will be saved for future use

2. Check your Gmail drafts for the generated emails
3. Check Slack for approval notifications (if configured)

## Step 10: Approve and Send

Approve an email draft:

```bash
python -m talent_scout approve --candidate-id <uuid>
```

Or click "Approve & Send" in Slack!

## Step 11: Monitor for Replies

Set up a cron job or run manually:

```bash
python -m talent_scout monitor
```

## Troubleshooting

### "Module not found" errors
```bash
pip install -r requirements.txt --upgrade
```

### "Credentials not found" errors
Make sure credential files are in the `credentials/` directory:
```
credentials/
├── gmail_credentials.json
└── calendar_credentials.json
```

### Database connection errors
- Verify Supabase URL and key in `.env`
- Make sure the candidates table exists
- Check network connectivity

### LLM API errors
- Verify API keys are correct
- Check API quota/billing
- Ensure the model name is correct

## Next Steps

- Customize email templates in `talent_scout/agents/recruiter_agent.py`
- Adjust fit score threshold in `.env`
- Set up automated inbox monitoring with cron
- Integrate with your ATS or other tools

## Need Help?

Open an issue on GitHub or check the main README for more details.
