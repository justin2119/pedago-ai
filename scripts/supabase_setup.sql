-- Supabase setup for the pedago-ai RAG corpus.
-- Idempotent: safe to re-run. Apply via the Supabase SQL editor or a migration.
-- Embedding dimension must match EMBEDDING_DIMENSIONS (1536 for text-embedding-3-small).

create extension if not exists vector;

create table if not exists public.document_chunks (
    id text primary key,
    content text not null,
    metadata jsonb not null default '{}'::jsonb,
    embedding vector(1536) not null,
    created_at timestamptz not null default now()
);

create index if not exists document_chunks_metadata_idx
    on public.document_chunks using gin (metadata jsonb_path_ops);

create index if not exists document_chunks_source_idx
    on public.document_chunks ((metadata->>'source'));

create index if not exists document_chunks_embedding_idx
    on public.document_chunks using hnsw (embedding vector_cosine_ops);

-- Vector similarity search with optional metadata filters.
-- Each filter is ignored when NULL, so calling with only query_embedding and match_count
-- still works.
create or replace function public.match_document_chunks(
    query_embedding vector(1536),
    match_count int default 6,
    filter_classe text default null,
    filter_serie text default null,
    filter_matiere text default null,
    filter_type_document text default null
)
returns table (
    id text,
    content text,
    metadata jsonb,
    similarity float
)
language sql stable
as $$
    select
        d.id,
        d.content,
        d.metadata,
        1 - (d.embedding <=> query_embedding) as similarity
    from public.document_chunks d
    where (filter_classe is null or d.metadata->>'classe' = filter_classe)
      and (filter_serie is null or d.metadata->>'serie' = filter_serie)
      and (filter_matiere is null or d.metadata->>'matiere' = filter_matiere)
      and (filter_type_document is null or d.metadata->>'type_document' = filter_type_document)
    order by d.embedding <=> query_embedding
    limit match_count;
$$;
