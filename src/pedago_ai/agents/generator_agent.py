"""Generator agent: produces an APC lesson plan using PydanticAI and an OpenAI-compatible model."""

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from pedago_ai.config import get_settings
from pedago_ai.schemas.lesson_plan import PERIOD_MINUTES, LessonPlan, LessonPlanRequest

OUTPUT_RETRIES = 3

SYSTEM_PROMPT = (
    "You are an expert pedagogue for Togolese secondary schools following the APC "
    "(Approche Par Competences) framework. Produce a complete lesson plan with operational "
    "pedagogical objectives, timed phases, professor and student activities, and evaluation "
    "items. Use the provided curriculum context when available. The request contains the "
    "teacher's administrative information (teacher block); keep it unchanged and do not invent "
    "any teacher, DRE, IESG or school details. "
    "Every entry in activities MUST include a non-empty professor_activity (what the teacher "
    "does) and a non-empty student_activity (what the learners do), in addition to phase, "
    "duration_minutes and materials. Never omit these two fields. "
    "Togolese secondary lessons are measured in official periods of 55 minutes. The total "
    "duration is always 1 to 6 periods (55, 110, 165, 220, 275 or 330 minutes). Distribute the "
    "timing and activities so that the phase durations add up exactly to the total duration, "
    "and so that each period is accounted for: the sum of timing durations must equal the total "
    "minutes, and the sum of activity durations must equal the total minutes. Give longer phases "
    "(construction, application) the larger share in multi-period lessons, keep a short motivation "
    "and synthesis, and reserve the final period time for evaluation when there are several periods. "
    "Each phase's duration_minutes must be a positive integer."
)


def build_model() -> OpenAIChatModel:
    """Create the OpenAI-compatible chat model from settings."""
    settings = get_settings()
    provider = OpenAIProvider(base_url=settings.model_base_url, api_key=settings.model_api_key)
    return OpenAIChatModel(settings.model_name, provider=provider)


def build_generator() -> Agent[None, LessonPlan]:
    """Create the PydanticAI agent that returns a structured LessonPlan."""
    return Agent(
        build_model(),
        output_type=LessonPlan,
        system_prompt=SYSTEM_PROMPT,
        output_retries=OUTPUT_RETRIES,
    )


def period_hint(duration_minutes: int) -> str:
    """Describe the 55-minute period breakdown of a lesson duration for the model."""
    periods = max(1, round(duration_minutes / PERIOD_MINUTES))
    hours = duration_minutes // 60
    minutes = duration_minutes % 60
    return (
        f"Durée totale : {duration_minutes} minutes, soit {periods} période(s) de {PERIOD_MINUTES} minutes "
        f"({periods} x {PERIOD_MINUTES} min, affichée comme {hours} h {minutes:02d} min). "
        "Répartissez les phases et les activités sur ces périodes, sans dépasser ni laisser de temps vide."
    )


async def generate_lesson_plan(request: LessonPlanRequest, feedback: list[str]) -> LessonPlan:
    """Generate a lesson plan for the request, incorporating validator feedback if any."""
    prompt = request.model_dump_json(indent=2)
    prompt += "\n\n" + period_hint(request.duration_minutes)
    if feedback:
        prompt += "\n\nFix these issues from the previous attempt:\n- " + "\n- ".join(feedback)
    result = await build_generator().run(prompt)
    plan = result.output
    # The teacher's administrative block comes from the request, never from the model output.
    return plan.model_copy(update={"teacher": request.teacher})
