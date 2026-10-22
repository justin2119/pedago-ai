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

## Lesson plan request

The teacher's administrative information is mandatory before a fiche de cours can be generated. The `teacher` block is validated first and is copied into the official header of the generated Word document.

```json
{
  "teacher": {
    "nom": "Mensah",
    "prenom": "Kofi",
    "dre": "DRE Maritime",
    "iesg": "IESG Vogan",
    "etablissement": "Lycee de Vogan",
    "telephone": "+228 90 00 00 00",
    "classe": "Seconde C",
    "serie": "C"
  },
  "subject": "Physique-Chimie",
  "level": "Seconde C",
  "theme": "Mecanique",
  "sub_theme": "Forces et mouvements",
  "duration_minutes": 55,
  "competence": "Expliquer le mouvement d'un solide soumis a des forces"
}
```

Field notes:

- `nom`, `prenom`, `dre`, `iesg`, `etablissement`, `telephone` and `classe` are required.
- `serie` is optional.
- A request without the `teacher` block is rejected with a validation error.
