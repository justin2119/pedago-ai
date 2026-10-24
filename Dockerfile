# syntax=docker/dockerfile:1
# Hugging Face Spaces (Docker SDK) image for PrepaCours. Serves FastAPI on port 7860.
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Dependency layer first, for caching. The repo has no uv.lock, so --frozen is not used.
# Installing with --no-install-project keeps this layer independent of the source code.
COPY pyproject.toml ./
RUN uv sync --no-dev --no-install-project

# Application source, frontend and corpus (the frontend is served by the app at /app).
COPY src ./src
COPY frontend ./frontend
COPY corpus ./corpus

# Install the project itself into the environment.
RUN uv sync --no-dev

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 7860

CMD ["uvicorn", "pedago_ai.main:app", "--host", "0.0.0.0", "--port", "7860"]
