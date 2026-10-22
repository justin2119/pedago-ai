"""Validator agent: checks a generated lesson plan for structural and pedagogical consistency."""

from pedago_ai.schemas.lesson_plan import LessonPlan, LessonPlanRequest


async def validate_lesson_plan(plan: LessonPlan, request: LessonPlanRequest) -> list[str]:
    """Return human-readable issues; an empty list means the plan is valid."""
    issues: list[str] = []

    timing_total = sum(segment.duration_minutes for segment in plan.timing)
    if timing_total != request.duration_minutes:
        issues.append(
            f"Timing totals {timing_total} minutes but the lesson lasts "
            f"{request.duration_minutes} minutes."
        )

    activity_total = sum(activity.duration_minutes for activity in plan.activities)
    if activity_total != request.duration_minutes:
        issues.append(
            f"Activities total {activity_total} minutes but the lesson lasts "
            f"{request.duration_minutes} minutes."
        )

    if not plan.evaluation:
        issues.append("The lesson plan has no evaluation items.")

    return issues
