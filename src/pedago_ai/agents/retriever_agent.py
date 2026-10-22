"""Retriever agent: fetches relevant curriculum passages from the pgvector store."""

from pedago_ai.rag.supabase_client import search_similar_chunks
from pedago_ai.schemas.lesson_plan import LessonPlanRequest

TOP_K = 6


async def retrieve_context(request: LessonPlanRequest) -> str:
    """Return curriculum context relevant to the request as a single text block."""
    query = f"{request.subject} {request.level} {request.theme} {request.competence}"
    chunks = await search_similar_chunks(query, limit=TOP_K)
    return "\n\n".join(chunks)
