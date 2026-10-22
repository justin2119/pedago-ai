"""Supabase client and pgvector similarity search."""

from functools import lru_cache

import httpx
from supabase import Client, create_client

from pedago_ai.config import get_settings


@lru_cache
def get_supabase() -> Client:
    """Return a cached Supabase client built from settings."""
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_key)


async def embed_text(text: str) -> list[float]:
    """Embed text via the OpenAI-compatible proxy."""
    settings = get_settings()
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{settings.model_base_url.rstrip('/')}/embeddings",
            headers={"Authorization": f"Bearer {settings.model_api_key}"},
            json={"model": settings.embedding_model_name, "input": text},
        )
        response.raise_for_status()
        data = response.json()
    return list(data["data"][0]["embedding"])


async def search_similar_chunks(query: str, limit: int = 6) -> list[str]:
    """Return the content of the chunks most similar to the query via the pgvector match function."""
    settings = get_settings()
    embedding = await embed_text(query)
    result = (
        get_supabase()
        .rpc(settings.supabase_match_function, {"query_embedding": embedding, "match_count": limit})
        .execute()
    )
    return [row["content"] for row in (result.data or [])]
