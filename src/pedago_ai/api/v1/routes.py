"""API v1 routes: lesson plan generation and DOCX export."""

import logging
import re
import unicodedata

from fastapi import APIRouter
from fastapi.responses import JSONResponse, Response
from pydantic import ValidationError

from pedago_ai.agents.orchestrator import build_lesson_plan
from pedago_ai.schemas.lesson_plan import LessonPlan, LessonPlanRequest
from pedago_ai.services.export_docx import lesson_plan_to_docx

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["lesson-plans"])

DOCX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def _error(status_code: int, code: str, message: str) -> JSONResponse:
    """Build a structured error body the PWA can display."""
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
    )


def _docx_filename(theme: str) -> str:
    """Return an ASCII-safe filename: fiche_pedagogique_{theme}.docx."""
    ascii_theme = unicodedata.normalize("NFKD", theme).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^A-Za-z0-9]+", "_", ascii_theme).strip("_") or "theme"
    return f"fiche_pedagogique_{slug}.docx"


@router.post("/generate", response_model=LessonPlan)
async def generate_lesson(request: LessonPlanRequest) -> LessonPlan | JSONResponse:
    """Run retrieval, generation and validation, and return the validated lesson plan.

    Request validation (including the mandatory teacher block) is handled by FastAPI and
    returns 422. Model output that cannot be parsed or validated returns 502. Any other
    failure (LLM proxy down, Supabase or retrieval unavailable) returns 503.
    """
    try:
        return await build_lesson_plan(request)
    except ValidationError:
        logger.exception("Model output failed schema validation")
        return _error(
            502,
            "invalid_model_output",
            "The generated lesson plan was invalid. Please try again.",
        )
    except Exception:
        logger.exception("Lesson plan generation failed")
        return _error(
            503,
            "generation_unavailable",
            "Lesson plan generation is temporarily unavailable. Please try again later.",
        )


@router.post("/export/docx")
async def export_docx(plan: LessonPlan) -> Response:
    """Render a LessonPlan as a Word document download."""
    try:
        content = lesson_plan_to_docx(plan)
    except Exception:
        logger.exception("DOCX export failed")
        return _error(500, "export_failed", "The Word document could not be created.")
    headers = {"Content-Disposition": f'attachment; filename="{_docx_filename(plan.theme)}"'}
    return Response(content=content, media_type=DOCX_MEDIA_TYPE, headers=headers)
