"""Generator agent: produces an APC lesson plan using PydanticAI and an OpenAI-compatible model."""

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

from pedago_ai.config import get_settings
from pedago_ai.schemas.lesson_plan import LessonPlan, LessonPlanRequest

SYSTEM_PROMPT = (
    "You are an expert pedagogue for Togolese secondary schools following the APC "
    "(Approche Par Competences) framework. Produce a complete lesson plan with operational "
    "pedagogical objectives, timed phases, professor and student activities, and evaluation "
    "items. Use the provided curriculum context when available."
)


def build_model() -> OpenAIModel:
    """Create the OpenAI-compatible chat model from settings."""
    settings = get_settings()
    provider = OpenAIProvider(base_url=settings.model_base_url, api_key=settings.model_api_key)
    return OpenAIModel(settings.model_name, provider=provider)


def build_generator() -> Agent[None, LessonPlan]:
    """Create the PydanticAI agent that returns a structured LessonPlan."""
    return Agent(build_model(), output_type=LessonPlan, system_prompt=SYSTEM_PROMPT)


async def generate_lesson_plan(request: LessonPlanRequest, feedback: list[str]) -> LessonPlan:
    """Generate a lesson plan for the request, incorporating validator feedback if any."""
    prompt = request.model_dump_json(indent=2)
    if feedback:
        prompt += "\n\nFix these issues from the previous attempt:\n- " + "\n- ".join(feedback)
    result = await build_generator().run(prompt)
    return result.output
