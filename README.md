# pedago-ai

![Vert Foret](https://img.shields.io/badge/Vert_For%C3%AAt-006A4E?style=for-the-badge&logoColor=white) ![Jaune Or](https://img.shields.io/badge/Jaune_Or-FFCE00?style=for-the-badge&logoColor=black) ![Rouge Sang](https://img.shields.io/badge/Rouge_Sang-D21034?style=for-the-badge&logoColor=white) ![Blanc Pur](https://img.shields.io/badge/Blanc_Pur-FFFFFF?style=for-the-badge&logoColor=black) ![Fond clair](https://img.shields.io/badge/Fond_clair-F8FAF9?style=for-the-badge&logoColor=black)

AI-assisted lesson plan generation for Togolese secondary education, following the APC (Approche Par Competences) framework.

## Stack

- Python 3.11+ managed with uv
- FastAPI backend
- PydanticAI agents (orchestrator, retriever, generator, validator)
- OpenAI-compatible model proxy (configurable base URL and model)
- Supabase with pgvector for retrieval
- Frontend: vanilla HTML5 / CSS3 / ES6+ JavaScript as a Progressive Web App (see below)

## Togolese National Design System

The interface uses the colors of the Togolese national flag, each with a fixed functional role.

| Token | Hex | Role | Badge |
|---|---|---|---|
| Vert Foret / Espoir | `#006A4E` | Primary structural elements, brand accents, success states | ![#006A4E](https://img.shields.io/badge/Vert_For%C3%AAt-006A4E?style=flat-square) |
| Jaune Or / Travail | `#FFCE00` | Secondary highlights, badges, warnings, APC metrics | ![#FFCE00](https://img.shields.io/badge/Jaune_Or-FFCE00?style=flat-square&logoColor=black) |
| Rouge Sang / Fidelite | `#D21034` | Critical actions, CTA generate button, emblem canton | ![#D21034](https://img.shields.io/badge/Rouge_Sang-D21034?style=flat-square) |
| Blanc Pur | `#FFFFFF` | Surfaces and cards | ![#FFFFFF](https://img.shields.io/badge/Blanc_Pur-FFFFFF?style=flat-square&logoColor=black) |
| Fond clair | `#F8FAF9` | Clean pedagogical page background | ![#F8FAF9](https://img.shields.io/badge/Fond_clair-F8FAF9?style=flat-square&logoColor=black) |

## Frontend PWA Architecture

Status: this section describes the target frontend architecture. The frontend files listed below are not yet in the repository.

- Vanilla HTML5 / CSS3 / ES6+ JavaScript, with zero external JS framework and zero runtime overhead.
- Full PWA support:
  - `manifest.json` for installability and app metadata.
  - Service Worker (`sw.js`) that caches generated lesson plans so teachers can consult them offline in areas with low connectivity in Togo.
- Local persistence of the teacher administrative profile (Nom, Prenom, DRE, IESG, Etablissement, Telephone) via `localStorage`, so the header of each fiche de cours is pre-filled.

### Style Carre

The design system rules, called "Style Carre", keep the interface sober and institutional:

- Cards, inputs and modals use a 4px to 5px border-radius.
- The pill shape (`rounded-full`) is reserved exclusively for primary action buttons and badges.

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
