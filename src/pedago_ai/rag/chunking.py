"""Text chunking for curriculum documents before embedding."""


def chunk_text(text: str, max_chars: int = 1200, overlap: int = 150) -> list[str]:
    """Split text into overlapping chunks, preferring paragraph boundaries."""
    if max_chars <= overlap:
        raise ValueError("max_chars must be greater than overlap")

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if len(current) + len(paragraph) + 2 <= max_chars:
            current = f"{current}\n\n{paragraph}" if current else paragraph
            continue
        if current:
            chunks.append(current)
            tail = current[-overlap:]
            current = f"{tail}\n\n{paragraph}" if tail else paragraph
        else:
            current = paragraph
        while len(current) > max_chars:
            chunks.append(current[:max_chars])
            current = current[max_chars - overlap :]
    if current:
        chunks.append(current)
    return chunks
