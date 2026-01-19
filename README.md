# Talent-Scout: Autonomous Hiring Agent 🤖

An AI-powered autonomous hiring agent that orchestrates the end-to-end recruitment lifecycle using LangGraph. Talent-Scout automates resume screening, personalized outreach, and interview scheduling using advanced LLMs and intelligent workflow orchestration.

## 🌟 Features

### 1. **Resume Parsing & Ranking (The Screener)**
- 📄 Parses PDF resumes and extracts structured data (Skills, Experience, Education)
- 🎯 Calculates fit scores (0-100) using Cosine Similarity against job descriptions
- 💾 Automatically stores qualified candidates (Score > 75) in Supabase database
- 🔍 Supports GPT-4o and Gemini 1.5 Pro for intelligent extraction

### 2. **Autonomous Outreach (The Recruiter)**
- ✉️ Generates personalized cold emails referencing specific projects
- 📧 Creates draft emails in Gmail for human review
- 💬 Sends Slack notifications for human-in-the-loop approval
- 🚀 Sends approved emails via Gmail API

### 3. **Interview Coordination (The Scheduler)**
- 📨 Monitors inbox for candidate replies
- 🧠 Detects intent (Interested/Not Interested/Schedule Time)
- 📅 Checks Google Calendar for available slots
- 🔗 Creates calendar invites with Google Meet links
- 🔔 Sends real-time Slack notifications

## 🏗️ Architecture

Built with a modern AI-native stack:
- **LangGraph**: Workflow orchestration and state management
- **LangChain**: LLM integration and prompt engineering
- **OpenAI/Gemini**: Advanced language models for parsing and generation
- **Supabase**: PostgreSQL database for candidate management
- **Gmail API**: Email draft creation and sending
- **Google Calendar API**: Interview scheduling automation
- **Slack API**: Human-in-the-loop notifications

## 📋 Prerequisites

- Python 3.8+
- OpenAI API key or Google Gemini API key
- Supabase account and project
- Google Cloud project with Gmail and Calendar APIs enabled
- Slack workspace with bot token (optional but recommended)

## 🚀 Installation

1. **Clone the repository:**
```bash
git clone https://github.com/yadavanujkumar/Talent-Hunter.git
cd Talent-Hunter
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Set up environment variables:**
```bash
cp .env.example .env
# Edit .env with your API keys and configuration
```

4. **Configure Google APIs:**

   a. Go to [Google Cloud Console](https://console.cloud.google.com/)
   
   b. Create a new project or select existing one
   
   c. Enable Gmail API and Google Calendar API
   
   d. Create OAuth 2.0 credentials (Desktop application)
   
   e. Download credentials and save to `credentials/gmail_credentials.json` and `credentials/calendar_credentials.json`

5. **Set up Supabase:**

   a. Create a Supabase project at [supabase.com](https://supabase.com)
   
   b. Run this SQL in the SQL Editor:
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
   ```
   
   c. Copy your project URL and anon key to `.env`

6. **Configure Slack (Optional):**

   a. Create a Slack app at [api.slack.com/apps](https://api.slack.com/apps)
   
   b. Add Bot Token Scopes: `chat:write`, `chat:write.public`
   
   c. Install app to workspace and copy Bot User OAuth Token to `.env`

## 📖 Usage

### Create a Sample Job Description

```bash
python -m talent_scout create-sample-jd --output job_description.json
```

Edit the generated file to match your job requirements.

### Screen Resumes and Create Drafts

```bash
python -m talent_scout screen \
  --resume-folder ./resumes \
  --job-description job_description.json \
  --create-drafts
```

This will:
1. Parse all PDF resumes in the folder
2. Calculate fit scores against the job description
3. Save qualified candidates (score > 75) to database
4. Generate personalized emails for each candidate
5. Create Gmail drafts
6. Send Slack notifications for approval

### Approve and Send Email

After reviewing drafts in Gmail and receiving Slack notification:

```bash
python -m talent_scout approve --candidate-id <candidate-uuid>
```

Or approve via Slack interactive buttons!

### Monitor Inbox for Replies

Run periodically (e.g., via cron job) to check for candidate responses:

```bash
python -m talent_scout monitor
```

This will:
1. Check inbox for replies from contacted candidates
2. Detect intent (interested/not interested/schedule time)
3. Send available time slots if interested
4. Create calendar event if time selected
5. Send confirmation emails with Meet links

## 🎯 Example Workflow

1. **Screening Phase:**
   ```bash
   python -m talent_scout screen --resume-folder ./resumes --job-description job.json --create-drafts
   ```
   Output:
   ```
   ✅ Found 5 qualified candidates
   ✅ Created 5 email drafts
   ```

2. **Review & Approve:**
   - Check Gmail drafts
   - Review Slack notifications
   - Click "Approve & Send" in Slack or use CLI

3. **Monitoring:**
   ```bash
   python -m talent_scout monitor
   ```
   Output:
   ```
   📧 Candidate Interested: John Doe
   📅 Sent available time slots
   ```

4. **Scheduling:**
   - Candidate replies with time selection
   - System creates calendar event with Google Meet
   - Sends confirmation to candidate
   - Notifies recruiter via Slack

## 📁 Project Structure

```
Talent-Hunter/
├── talent_scout/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py                    # Command-line interface
│   ├── config.py                 # Configuration management
│   ├── orchestrator.py           # Main pipeline orchestration
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── screener_agent.py    # Resume screening & ranking
│   │   ├── recruiter_agent.py   # Personalized outreach
│   │   └── scheduler_agent.py   # Interview coordination
│   ├── database/
│   │   ├── __init__.py
│   │   ├── models.py            # Data models
│   │   └── db_manager.py        # Database operations
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── resume_parser.py     # PDF parsing & LLM extraction
│   │   └── scoring.py           # Fit score calculation
│   └── api_integrations/
│       ├── __init__.py
│       ├── gmail_client.py      # Gmail API wrapper
│       ├── calendar_client.py   # Google Calendar API wrapper
│       └── slack_client.py      # Slack API wrapper
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## 🔧 Configuration

Edit `.env` to customize:

- **LLM Provider**: Choose between OpenAI (`gpt-4o`) or Google (`gemini-1.5-pro`)
- **Fit Score Threshold**: Adjust minimum score for qualification (default: 75)
- **Recruiter Info**: Set your name and email for personalization
- **Database**: Configure Supabase or PostgreSQL connection
- **APIs**: Set up Gmail, Calendar, and Slack credentials

## 🛡️ Security Best Practices

- Never commit `.env` file or API credentials
- Store credentials in `credentials/` directory (already in .gitignore)
- Use OAuth 2.0 for Google APIs (not API keys)
- Restrict API scopes to minimum required
- Regularly rotate API keys and tokens

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [LangGraph](https://github.com/langchain-ai/langgraph) for workflow orchestration
- Powered by [LangChain](https://github.com/langchain-ai/langchain) for LLM integration
- Uses [Supabase](https://supabase.com) for database management

## 📞 Support

For issues, questions, or suggestions, please open an issue on GitHub.

---

**Made with ❤️ by the Talent-Scout team**