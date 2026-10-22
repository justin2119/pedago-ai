"""Orchestrator: coordinates retrieval, generation and validation for a lesson plan."""

from pedago_ai.agents.generator_agent import generate_lesson_plan
from pedago_ai.agents.retriever_agent import retrieve_context
from pedago_ai.agents.validator_agent import validate_lesson_plan
from pedago_ai.schemas.lesson_plan import LessonPlan, LessonPlanRequest

MAX_ATTEMPTS = 2


async def build_lesson_plan(request: LessonPlanRequest) -> LessonPlan:
    """Run retrieval, then generate and validate a lesson plan, retrying on validation issues.

    The teacher administrative block is mandatory: LessonPlanRequest validation rejects requests
    without it before any retrieval or generation runs, and it is carried onto the final plan.
    """
    context = await retrieve_context(request)
    request = request.model_copy(update={"context": context})

    issues: list[str] = []
    plan: LessonPlan | None = None
    for _ in range(MAX_ATTEMPTS):
        plan = await generate_lesson_plan(request, feedback=issues)
        issues = await validate_lesson_plan(plan, request)
        if not issues:
            break

    if plan is None:
        raise RuntimeError("Lesson plan generation produced no output.")
    return plan.model_copy(update={"teacher": request.teacher})
