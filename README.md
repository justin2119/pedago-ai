# pedago-ai

AI-assisted lesson plan generation for Togolese secondary education, following the APC (Approche Par Competences) framework.

## Stack

- Python 3.11+ managed with uv
- FastAPI backend
- PydanticAI agents (orchestrator, retriever, generator, validator)
- OpenAI-compatible model proxy (configurable base URL and model)
- Supabase with pgvector for retrieval

## Setup

```bash
uv sync
cp .env.example .env
uv run uvicorn pedago_ai.main:app --reload
```

Health check: GET /health
