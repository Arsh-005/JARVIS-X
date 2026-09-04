# JARVIS-X

### Agentic AI Assistant with RAG, Voice, Multi-Agent Workflows & Production LLM Routing

JARVIS-X is a full-stack **Agentic AI Engineering project** built with Python and FastAPI.

It goes beyond a standard chatbot by combining conversational AI, document-grounded retrieval, agentic execution, multi-agent review workflows, voice interaction, persistent architecture components, provider abstraction, reliability mechanisms, and production deployment into a single AI assistant platform.

The project is designed as an advanced AI engineering capstone demonstrating practical concepts used in modern LLM applications: **RAG, agents, context engineering, tool orchestration, multi-agent systems, model routing, reliability engineering, API design, testing, security boundaries, and deployment.**

> JARVIS-X is an engineering portfolio project and production-oriented reference implementation. A real enterprise deployment would require organization-specific identity, infrastructure, compliance, monitoring, backup, security, and scaling policies.

---

## 🚀 Live Demo

**JARVIS-X is publicly deployed on Render:**

https://jarvis-x-spjn.onrender.com

> The current deployment uses Render's free infrastructure. The first request after inactivity may take longer while the service starts.

---
## Screenshots

### Main Chat

![JARVIS-X Chat Interface](screenshots/jarvis-chat.png)

### Document RAG

![JARVIS-X RAG](screenshots/jarvis-rag.png)

### Multi-Agent Studio

![JARVIS-X Multi-Agent Studio](screenshots/jarvis-multi-agent.png)

### Mobile Interface

<p align="center">
  <img src="screenshots/jarvis-mobile.png" width="350" alt="JARVIS-X Mobile Interface">
</p>
# ✨ Core Features

## 🤖 Conversational AI

JARVIS-X provides a ChatGPT-style conversational interface backed by a modular LLM provider architecture.

Features include:

- Multi-turn conversations
- Session-based interaction
- Markdown/code rendering
- Code-copy functionality
- Gemini production routing
- Provider abstraction
- Error handling
- Retry logic
- Exponential backoff
- Model fallback

---

## 🧠 Agent Mode

JARVIS-X includes an explicit agent execution architecture designed around the:

```text
Reason → Act → Observe
```

pattern.

The agent runtime architecture supports concepts such as:

- Agent state
- Multi-step execution
- Tool invocation
- Tool-result observations
- Execution budgets
- Iteration limits
- Termination conditions
- Loop detection
- Checkpoints
- Controlled tool execution

This allows JARVIS-X to move beyond single LLM calls toward structured agentic workflows.

---

## 👥 Multi-Agent Studio

JARVIS-X includes a dedicated **Multi-Agent Review workflow**.

A goal can be analyzed through coordinated AI roles such as:

```text
User Goal
    ↓
Supervisor
    ↓
Specialist
    ↓
Critic / Reviewer
    ↓
Structured Final Review
```

The frontend renders the workflow output in a dedicated review interface instead of exposing raw API JSON.

Potential use cases include:

- Architecture reviews
- Security reviews
- Technical planning
- Project evaluation
- Product analysis
- AI system design reviews

---

## 📚 Retrieval-Augmented Generation (RAG)

JARVIS-X can ingest documents and use retrieved information as context for LLM responses.

Supported document/code formats include:

```text
PDF
DOCX
TXT
Markdown
JSON
CSV
Python
JavaScript
TypeScript
HTML
CSS
YAML
XML
```

The retrieval architecture includes concepts for:

- Document ingestion
- Chunking
- Embeddings
- Semantic retrieval
- Hybrid retrieval
- Reranking
- Context construction
- Knowledge-grounded generation

Documents uploaded through the interface can automatically participate in the knowledge workflow.

---

## 🎙️ Voice Interaction

JARVIS-X supports browser-based voice interaction.

### Speech Input

Users can speak prompts using supported browser speech-recognition capabilities.

### Text-to-Speech

Assistant responses can be spoken through browser speech synthesis.

Voice controls include:

- Microphone input
- Listening state
- Speech status
- Speaker enable/disable
- Automatic assistant speech

---

## 📎 File & Media Handling

The interface supports drag-and-drop, file selection, and clipboard-based attachment workflows.

Implemented handling includes:

- Documents
- Source-code files
- Structured data
- Audio
- Video storage/upload

Audio files can be routed through the speech transcription endpoint.

> Image upload is intentionally disabled in the current frontend release.

> Video upload/storage is supported, but semantic video-frame understanding is not currently enabled.

---

# ⚡ Reliable LLM Routing

The production deployment uses a modular LLM abstraction rather than coupling the entire application directly to one model implementation.

JARVIS-X includes support for:

- Gemini provider
- OpenAI-compatible provider
- Local provider/fallback architecture
- Configurable model selection
- Request timeout handling
- Retryable HTTP failures
- Exponential backoff
- Jitter
- Model fallback

For Gemini routing, transient failures such as rate limiting and temporary provider/server errors can be retried before moving through configured fallback models.

This improves resilience compared with a single unprotected API call.

---

# 🧠 Memory & Context Architecture

JARVIS-X contains architecture for multiple forms of AI memory and contextual state.

Conceptually:

```text
                     Agent Runtime
                          │
              ┌───────────┴───────────┐
              │                       │
       Working Context          Memory Manager
                                      │
                         ┌────────────┼────────────┐
                         │            │            │
                   Conversation    Semantic     Project /
                     Memory         Memory      Episodic
                         │            │            │
                         └────────────┼────────────┘
                                      │
                                  Retrieval
                                      │
                               Context Builder
                                      │
                                     LLM
```

This architecture separates temporary execution state from longer-lived retrieval and project context.

---

# 🏗️ System Architecture

```text
                         ┌─────────────────────┐
                         │        USER         │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │   JARVIS-X Web UI   │
                         │ Chat / Voice / File │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │    FastAPI Layer    │
                         └──────────┬──────────┘
                                    │
             ┌──────────────────────┼──────────────────────┐
             │                      │                      │
             ▼                      ▼                      ▼
       Normal Chat             Agent Runtime          Multi-Agent
                                   │                    Workflow
                                   │
                         Reason → Act → Observe
                                   │
                    ┌──────────────┼──────────────┐
                    │              │              │
                    ▼              ▼              ▼
                   LLM            Tools         Memory
                    │                             │
                    │                             ▼
                    │                         Retrieval
                    │                             │
                    └──────────────┬──────────────┘
                                   │
                                   ▼
                            Context Builder
                                   │
                                   ▼
                            Provider Router
                                   │
                     ┌─────────────┼─────────────┐
                     │             │             │
                     ▼             ▼             ▼
                   Gemini       OpenAI-*        Local
                                compatible
                                   │
                                   ▼
                           Retry / Backoff /
                            Model Fallback
```

---

# 🛠️ Technology Stack

### Backend

- Python
- FastAPI
- Uvicorn
- Pydantic
- HTTPX

### AI Engineering

- Gemini API
- OpenAI-compatible provider architecture
- Retrieval-Augmented Generation
- Embeddings
- Agent runtime
- Multi-Agent orchestration
- Context engineering
- Tool orchestration

### Data & Infrastructure Architecture

- SQLite for local development
- PostgreSQL adapter
- Redis-compatible cache architecture
- Qdrant vector-store adapter

### Frontend

- HTML
- CSS
- Vanilla JavaScript
- Responsive mobile UI
- Web Speech APIs

### DevOps

- Docker
- Docker Compose
- Render
- GitHub Actions
- Kubernetes reference manifests

### Quality

- Pytest
- Ruff

---

# 📂 Project Structure

```text
JARVIS-X/
│
├── src/
│   └── jarvis/
│       ├── api.py
│       ├── llm.py
│       ├── services.py
│       ├── tools.py
│       ├── rag.py
│       ├── embeddings.py
│       ├── db.py
│       ├── speech.py
│       ├── multi_agent.py
│       ├── attachments.py
│       │
│       ├── runtime/
│       ├── memory/
│       ├── retrieval/
│       ├── security/
│       ├── observability/
│       ├── auth/
│       ├── cache/
│       ├── infrastructure/
│       ├── background/
│       └── evals/
│
├── static/
│   ├── index.html
│   ├── style.css
│   └── app.js
│
├── tests/
│
├── deploy/
│   └── k8s/
│
├── data/
├── workspace/
│
├── Dockerfile
├── docker-compose.yml
├── render.yaml
├── pyproject.toml
├── .env.example
└── README.md
```

---

# 💻 Running Locally

## 1. Clone the repository

```bash
git clone https://github.com/Arsh-005/JARVIS-X.git
cd JARVIS-X
```

---

## 2. Create a virtual environment

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

---

## 3. Install dependencies

```powershell
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

For optional enterprise infrastructure integrations:

```powershell
pip install -e ".[dev,enterprise]"
```

---

## 4. Configure environment variables

Create your local environment file:

```powershell
Copy-Item .env.example .env
```

Configure the required provider credentials inside `.env`.

Example:

```env
APP_ENV=development
DEBUG=true

LLM_PROVIDER=gemini
GEMINI_API_KEY=YOUR_GEMINI_API_KEY
GEMINI_MODEL=YOUR_SUPPORTED_GEMINI_MODEL

JWT_SECRET=YOUR_SECRET
API_KEY=YOUR_API_KEY
```

Never commit `.env` or real API keys.

---

## 5. Start JARVIS-X

```powershell
python -m uvicorn jarvis.api:app --app-dir .\src --host 127.0.0.1 --port 8010
```

Open:

```text
http://127.0.0.1:8010
```

---

# 🧪 Testing

Run the automated test suite:

```powershell
python -m pytest -q
```

Current validated project state:

```text
21 tests passed
```

Run static analysis:

```powershell
python -m ruff check src tests
```

The test architecture covers core application behavior and infrastructure-oriented components.

---

# 🐳 Docker

Build and run the application using Docker:

```bash
docker build -t jarvis-x .
docker run -p 10000:10000 --env-file .env jarvis-x
```

JARVIS-X runs as a non-root user inside the production container.

A Docker Compose configuration is also included for infrastructure-oriented development.

---

# ☁️ Production Deployment

The public version of JARVIS-X is deployed using **Render + Docker**.

Production topology:

```text
Browser
   │
   ▼
Render HTTPS Endpoint
   │
   ▼
Docker Container
   │
   ▼
FastAPI / JARVIS-X
   │
   ▼
Gemini API
```

This means end users only need the public web application.

They do **not** need:

- Python
- VS Code
- JARVIS-X source code
- Local model-routing software
- Personal Gemini credentials

Production secrets are supplied through deployment environment variables rather than committed to the repository.

---

# 🔐 Security Design

JARVIS-X includes security-oriented architecture for:

- API-key protection
- JWT infrastructure
- Rate limiting
- Tool permissions
- Workspace boundaries
- Human approval boundaries
- Audit logging
- Restricted high-risk actions
- Environment-based secrets
- Controlled file handling

The architecture intentionally avoids treating unrestricted LLM-generated shell execution as a safe default.

A true enterprise deployment should additionally implement organization-specific controls such as:

- Managed identity / OIDC
- WAF / API gateway protection
- Centralized secret management
- Malware scanning for uploads
- Prompt-injection defenses
- Network policies
- Persistent audit infrastructure
- Security testing
- Backup and disaster recovery
- Compliance and retention policies

---

# 🛡️ Agent Safety

Agentic AI systems introduce risks that normal chat applications do not.

JARVIS-X therefore treats:

```text
LLM reasoning
```

and

```text
real-world actions
```

as separate security boundaries.

The architecture includes concepts for:

```text
LLM
 ↓
Proposed Tool Call
 ↓
Tool Registry
 ↓
Permission / Validation
 ↓
Approval Boundary
 ↓
Execution
 ↓
Audit
 ↓
Observation
```

This prevents the LLM layer from automatically being equivalent to unrestricted system access.

---

# 📊 Observability

The project contains architecture for:

- Request IDs
- Application logging
- Agent execution tracing
- Tool auditing
- Checkpoints
- Metrics
- Prometheus-compatible metrics integration

These components are intended to make agent execution inspectable rather than operating as an opaque loop.

---

# 🔄 CI/CD

GitHub Actions configuration provides automated quality/build gates.

Typical development validation:

```text
Push / Pull Request
        │
        ▼
      Ruff
        │
        ▼
     Pytest
        │
        ▼
   Build Validation
```

Render can automatically redeploy the application after updates are pushed to the production branch.

---

# ⚠️ Current Limitations

JARVIS-X is an advanced portfolio project, but there are still differences between the current public deployment and a large-scale enterprise AI platform.

### Free deployment persistence

The current Render deployment should not be treated as durable persistent storage for local runtime files.

A larger production deployment should connect persistent services such as:

```text
PostgreSQL
Object Storage
Managed Vector Database
Redis
```

where appropriate.

### Video understanding

Video files can be uploaded/stored, but semantic frame-by-frame video understanding is not enabled in the current release.

### Image interface

Image upload is intentionally disabled in the current frontend build.

### Browser voice compatibility

Speech-recognition behavior depends on browser support.

### Production scaling

Large-scale production would require load testing, distributed state, managed persistence, stronger authentication, monitoring/SLOs, and organization-specific security controls.

---

# 🗺️ Future Improvements

Potential future work includes:

- Durable cloud conversation memory
- Managed vector database deployment
- Persistent object storage
- Streaming LLM responses
- Advanced evaluation pipelines
- Agent execution visualization
- Better multi-agent specialization
- Automated RAG evaluation
- Prompt-injection detection
- Improved authentication
- User accounts
- Conversation history
- Distributed agent workers
- Production telemetry dashboards
- Semantic video understanding

---

# 🎯 What This Project Demonstrates

JARVIS-X demonstrates practical understanding of:

```text
LLM Application Engineering
          +
Retrieval-Augmented Generation
          +
Agentic AI
          +
Multi-Agent Systems
          +
Context Engineering
          +
Provider Abstraction
          +
Reliability Engineering
          +
Backend/API Engineering
          +
AI Safety Boundaries
          +
Testing
          +
Containerization
          +
Cloud Deployment
```

The goal is not simply to call an LLM API.

The goal is to explore how the surrounding **AI system architecture** can be designed.

---

# 💼 Resume / CV Description

### JARVIS-X — Agentic AI Assistant

Built and deployed a modular Agentic AI platform using **Python, FastAPI, Gemini, RAG, agent orchestration, multi-agent workflows and voice interfaces**. Implemented document ingestion and retrieval, context-aware LLM interactions, provider abstraction, retry/backoff and model-fallback mechanisms, controlled tool architecture, memory/retrieval components, responsive web UI, automated testing, Docker containerization and cloud deployment on Render.

---

# 🎤 Interview Talking Points

If discussing JARVIS-X in an interview, the most important engineering decisions include:

- Why an agent runtime differs from a normal chatbot
- How Reason → Act → Observe execution works
- How tool execution is controlled
- How RAG differs from simply placing an entire document into a prompt
- How documents are ingested and retrieved
- Why provider abstraction is useful
- Why transient LLM failures require retry/backoff
- Why model fallback improves availability
- How multi-agent workflows differ from a single-agent workflow
- How memory and execution state differ
- How prompt injection can affect RAG and agents
- Why public deployment secrets must remain server-side
- Why local filesystem persistence is insufficient for scalable cloud deployment
- How the FastAPI backend communicates with the frontend and model providers
- How the application is tested and deployed

---

# 👨‍💻 Author

**Arshpreet Singh**

Computer Science Engineering Student  
AI Engineering • Agentic AI • Machine Learning • Software Development

---

# ⭐ Project Status

```text
JARVIS-X
├── Conversational AI        ✅
├── Gemini Routing           ✅
├── Retry / Model Fallback   ✅
├── Document Upload          ✅
├── RAG / Knowledge          ✅
├── Agent Mode               ✅
├── Multi-Agent Workflow     ✅
├── Voice Input              ✅
├── Text-to-Speech           ✅
├── Responsive Web UI        ✅
├── Automated Tests          ✅
├── Docker Deployment        ✅
└── Public Cloud Demo        ✅
```

If you find the architecture useful, consider starring the repository.