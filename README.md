# JARVIS-X Enterprise Reference Architecture

JARVIS-X is a production-oriented reference implementation of a multimodal agentic AI assistant. It combines an explicit Reason → Act → Observe runtime, tool execution, RAG, layered memory, multimodal endpoints, human approval boundaries, observability, persistence, tests, and deployable infrastructure.

> **Scope:** this repository is an industry-style reference architecture, not a claim that a single ZIP is automatically production-ready for every organization. Real production rollout still requires organization-specific identity, threat modeling, cloud networking, secret rotation, backups, SLOs, legal/compliance review, and load/security testing.

## What is implemented

- FastAPI service with health/readiness endpoints, CORS, request IDs, streaming agent events, and rate limiting
- OpenAI/Gemini/local provider abstraction and routing
- Explicit budgeted agent runtime with state, checkpoints, termination rules, repeated-action loop detection, and tool budgets
- Structured planning/dependency validation and multi-agent review workflow
- Layered working/semantic/episodic/project memory
- RAG ingestion, hybrid retrieval and reranking
- Tool registry with workspace boundaries, web fetch controls, confirmation requirements and audit logging
- Speech-to-text, text-to-speech, image/vision endpoints and optional local computer capabilities
- Development SQLite path plus production Postgres adapter
- Redis-compatible cache adapter with in-memory fallback
- Qdrant vector-store adapter
- JWT service and API-key protection infrastructure
- Background job queue abstraction with local worker implementation
- Prometheus-compatible metrics adapter and internal tracing/metrics modules
- Unit, integration and enterprise-infrastructure tests
- Non-root Docker image, Docker Compose stack, GitHub Actions quality/build gates
- Kubernetes deployment, Service, HPA, ConfigMap and secret template

## Architecture

```text
Clients / Dashboard
        │
        ▼
   FastAPI Gateway
        │
  Auth / Rate Limit
        │
        ▼
    Agent Runtime
 Reason → Act → Observe
        │
 ┌──────┼─────────┐
 ▼      ▼         ▼
LLMs   Tools     Memory
 │      │          │
 │   Safety      RAG / Retrieval
 │   Approval      │
 └──────┴──────────┘
        │
        ▼
Infrastructure Adapters
Postgres • Redis • Qdrant
        │
        ▼
Metrics • Audit • Checkpoints
```

## Local development

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
copy .env.example .env
uvicorn jarvis.api:app --reload
```

Open `http://localhost:8000`.

## Full infrastructure stack

Install enterprise extras when running directly on the host:

```powershell
pip install -e ".[dev,enterprise]"
```

Or use containers:

```bash
docker compose up --build
```

The compose topology contains:

- JARVIS-X API
- PostgreSQL 16
- Redis 7
- Qdrant

Set real secrets in your environment before any public deployment.

## Testing

```bash
pytest
ruff check src tests
```

## Deployment

`deploy/k8s/` contains reference Kubernetes manifests. Replace `YOUR_USERNAME` in the image path and create a real Kubernetes Secret from a secure deployment system; do not commit populated secrets.

## Security principles

JARVIS-X intentionally does **not** expose unrestricted LLM-to-shell execution. Write-capable actions are permission-gated and high-risk local computer controls are disabled by default. Public deployments should additionally use managed identity/OIDC, TLS termination, secret management, network policies, WAF/API-gateway controls, vulnerability scanning, backups, retention policies and independent security review.

## CV-safe description

**JARVIS-X — Production-Oriented Multimodal Agentic AI Platform:** Built a modular agent runtime with LLM routing, hybrid RAG, layered memory, tool orchestration, human approval controls, multimodal speech/vision interfaces, checkpointing and loop prevention; added Postgres/Redis/Qdrant infrastructure adapters, observability, API security, background jobs, Docker/CI and Kubernetes deployment manifests.
