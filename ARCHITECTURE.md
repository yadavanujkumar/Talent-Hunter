# Talent-Scout Architecture

## System Overview

Talent-Scout is an autonomous hiring agent built using LangGraph for orchestrating three specialized AI agents that handle the complete recruitment lifecycle.

```
┌─────────────────────────────────────────────────────────────────┐
│                        TALENT-SCOUT SYSTEM                       │
└─────────────────────────────────────────────────────────────────┘
                                │
                    ┌───────────┴───────────┐
                    │   Orchestrator        │
                    │   (Main Pipeline)     │
                    └───────────┬───────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
        ▼                       ▼                       ▼
┌──────────────┐       ┌──────────────┐       ┌──────────────┐
│   SCREENER   │       │  RECRUITER   │       │  SCHEDULER   │
│    AGENT     │──────>│    AGENT     │──────>│    AGENT     │
└──────────────┘       └──────────────┘       └──────────────┘
```

## Agent Workflows

### 1. Screener Agent (Resume Parsing & Ranking)

```
INPUT: Resume Folder + Job Description
│
├─> Parse Resumes (LangGraph Node)
│   │
│   ├─> Extract Text from PDFs (pdfplumber)
│   └─> Parse with LLM (GPT-4o/Gemini)
│       └─> Output: Structured JSON
│           ├─> Name, Email, Phone
│           ├─> Skills (Technical, Soft, Certifications)
│           ├─> Experience (Company, Role, Projects)
│           └─> Education
│
├─> Calculate Fit Scores (LangGraph Node)
│   │
│   └─> Vector Similarity (Cosine)
│       ├─> Resume → TF-IDF Vector
│       ├─> Job Description → TF-IDF Vector
│       └─> Score = Cosine Similarity × 100
│
└─> Save to Database (LangGraph Node)
    │
    └─> Filter: Score > Threshold (default: 75)
        └─> Store in Supabase
            └─> Trigger: New Candidate Event
                └─> Invoke Recruiter Agent
```

### 2. Recruiter Agent (Autonomous Outreach)

```
INPUT: Qualified Candidate
│
├─> Generate Personalized Email (LangGraph Node)
│   │
│   └─> LLM Prompt Engineering
│       ├─> Context: Resume Data
│       ├─> Context: Specific Projects
│       ├─> Context: Skills Match
│       └─> Output: Personalized Email Body
│
├─> Create Gmail Draft (LangGraph Node)
│   │
│   └─> Gmail API
│       ├─> Compose Email
│       ├─> Save as Draft
│       └─> Return: Draft ID
│
├─> Send Slack Notification (LangGraph Node)
│   │
│   └─> Slack API
│       ├─> Message: Draft Preview
│       ├─> Interactive Buttons:
│       │   ├─> ✅ Approve & Send
│       │   ├─> ✏️  Edit Draft
│       │   └─> ❌ Reject
│       └─> Wait for Human Approval
│
└─> On Approval → Send Email
    │
    └─> Gmail API: Send Draft
        └─> Update Database: status = "contacted"
```

### 3. Scheduler Agent (Interview Coordination)

```
INPUT: Inbox Monitoring (Periodic)
│
├─> Detect Intent (LangGraph Node)
│   │
│   └─> LLM Classification
│       ├─> Parse Email Reply
│       └─> Classify:
│           ├─> "interested"
│           ├─> "not_interested"
│           └─> "schedule_time"
│
├─> Route by Intent (LangGraph Conditional Edge)
│   │
│   ├─> IF "interested":
│   │   │
│   │   └─> Get Calendar Slots (LangGraph Node)
│   │       ├─> Google Calendar API
│   │       ├─> Find Free Slots (9 AM - 5 PM, Weekdays)
│   │       └─> Send Email with 3 Options
│   │
│   ├─> IF "schedule_time":
│   │   │
│   │   └─> Create Calendar Event (LangGraph Node)
│   │       ├─> Parse Selected Time
│   │       ├─> Google Calendar API
│   │       │   ├─> Create Event
│   │       │   └─> Add Google Meet Link
│   │       ├─> Send Confirmation Email
│   │       └─> Slack Notification: "Interview Scheduled"
│   │
│   └─> IF "not_interested":
│       │
│       └─> Update Database: status = "rejected"
│           └─> Slack Notification: "Candidate Declined"
```

## Technology Stack

### Core Framework
- **LangGraph**: State machine orchestration
- **LangChain**: LLM integration and prompt management

### AI/ML
- **OpenAI GPT-4o**: Primary LLM for parsing and generation
- **Google Gemini 1.5 Pro**: Alternative LLM option
- **scikit-learn**: TF-IDF vectorization and cosine similarity

### Data Processing
- **pdfplumber**: PDF text extraction
- **Pydantic**: Data validation and modeling

### Database
- **Supabase**: PostgreSQL database (managed)
- **psycopg2**: PostgreSQL driver (alternative)

### External APIs
- **Gmail API**: Email drafts and sending
- **Google Calendar API**: Event creation and scheduling
- **Slack API**: Notifications and approvals

### Development
- **python-dotenv**: Environment configuration
- **pytest**: Testing framework
- **black**: Code formatting

## Data Flow

```
┌─────────────┐
│   Resumes   │ (PDF Files)
│   Folder    │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  LLM Parse  │ (GPT-4o/Gemini)
│  Extraction │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Structured │ (JSON Schema)
│    Data     │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Fit Score  │ (Cosine Similarity)
│ Calculation │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Supabase   │ (PostgreSQL)
│  Database   │
└──────┬──────┘
       │
       ├──────────────────┐
       │                  │
       ▼                  ▼
┌─────────────┐    ┌─────────────┐
│    Gmail    │    │    Slack    │
│   Drafts    │    │ Notifications│
└──────┬──────┘    └─────────────┘
       │
       ▼
┌─────────────┐
│   Inbox     │
│ Monitoring  │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Google    │
│  Calendar   │
└─────────────┘
```

## State Management

### LangGraph State Objects

```python
# Screener State
{
    "resume_folder": str,
    "job_description": JobDescription,
    "processed_resumes": List[dict],
    "qualified_candidates": List[Candidate],
    "error": str
}

# Recruiter State
{
    "candidate": Candidate,
    "email_subject": str,
    "email_body": str,
    "draft_id": str,
    "approved": bool,
    "error": str
}

# Scheduler State
{
    "candidate_email": str,
    "message_text": str,
    "intent": str,  # interested/not_interested/schedule_time
    "candidate": Candidate,
    "available_slots": List[dict],
    "selected_slot": dict,
    "calendar_event": dict,
    "error": str
}
```

## Database Schema

```sql
CREATE TABLE candidates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    email TEXT,
    phone TEXT,
    resume_data JSONB NOT NULL,  -- Full structured resume
    fit_score FLOAT NOT NULL,     -- 0-100 score
    job_description TEXT NOT NULL,
    status TEXT DEFAULT 'screened', -- Workflow state
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- Outreach tracking
    email_sent BOOLEAN DEFAULT FALSE,
    email_draft_id TEXT,
    reply_received BOOLEAN DEFAULT FALSE,
    
    -- Interview tracking
    interview_scheduled BOOLEAN DEFAULT FALSE,
    interview_time TIMESTAMP,
    calendar_event_id TEXT
);

-- Status values:
-- 'screened'  → Parsed and scored
-- 'contacted' → Email sent
-- 'interested' → Candidate replied positively
-- 'scheduled' → Interview booked
-- 'rejected'  → Candidate declined
-- 'hired'     → Candidate hired
```

## API Integration Patterns

### OAuth 2.0 Flow (Gmail & Calendar)
```
1. User initiates action
2. Check for stored token
3. If no token or expired:
   ├─> Open browser for OAuth consent
   ├─> User grants permissions
   └─> Save refresh token
4. Use API with token
```

### Slack Interactive Buttons
```
1. Send message with action buttons
2. Slack webhook receives button click
3. Parse action_id and value
4. Execute corresponding function
5. Update message with result
```

## Scoring Algorithm

```python
def calculate_fit_score(resume, job_description):
    # 1. Convert to text representations
    resume_text = extract_weighted_features(resume)
    jd_text = extract_weighted_features(job_description)
    
    # 2. Vectorize using TF-IDF
    vectorizer = TfidfVectorizer(
        stop_words='english',
        ngram_range=(1, 2)  # Unigrams and bigrams
    )
    vectors = vectorizer.fit_transform([resume_text, jd_text])
    
    # 3. Calculate cosine similarity
    similarity = cosine_similarity(vectors[0], vectors[1])
    
    # 4. Scale to 0-100
    return similarity * 100
```

**Feature Weighting:**
- Skills: 3x weight (repeated 3 times)
- Required Skills in JD: 3x weight
- Preferred Skills in JD: 2x weight
- Experience descriptions: 1x weight
- Education: 1x weight

## Security Considerations

1. **API Keys**: Stored in `.env`, never committed
2. **OAuth Tokens**: Stored locally, refresh automatically
3. **Database**: Row-level security in Supabase
4. **Email Access**: Read-only for monitoring, compose-only for sending
5. **Slack**: Bot token with minimal scopes

## Scalability

- **Parallel Resume Processing**: Can process resumes concurrently
- **Async Email Operations**: Non-blocking draft creation
- **Database Indexing**: Optimized queries on status and score
- **Caching**: Token caching for API efficiency
- **Rate Limiting**: Respects API limits with backoff

## Error Handling

- **Graceful Degradation**: Continue on individual resume failures
- **Retry Logic**: Automatic retry for transient API errors
- **Logging**: Comprehensive logging at all stages
- **Notifications**: Slack alerts for critical errors

## Future Enhancements

- [ ] Web dashboard for candidate management
- [ ] Advanced ML models for scoring
- [ ] Multi-language support
- [ ] Interview feedback integration
- [ ] Candidate relationship management
- [ ] Analytics and reporting
- [ ] Webhook support for ATS integration
