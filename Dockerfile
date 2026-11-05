# syntax=docker/dockerfile:1
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Run as an unprivileged user; the image never needs root at runtime.
RUN groupadd --system app \
    && useradd --system --gid app --home-dir /app --shell /usr/sbin/nologin app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# The AI package (ai/) is part of the product path.  Its base requirement is
# pydantic (already installed above), so the deterministic mock provider works
# without this step.  Build with --build-arg INSTALL_AI_EXTRAS=true to add the
# optional LangGraph and OpenAI/Gemini SDKs for a live model provider.
COPY ai/requirements.txt ./ai/requirements.txt
ARG INSTALL_AI_EXTRAS=false
RUN if [ "$INSTALL_AI_EXTRAS" = "true" ]; then \
        pip install --no-cache-dir -r ai/requirements.txt; \
    fi

COPY --chown=app:app . .

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import sys,urllib.request; \
sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=4).status == 200 else 1)"

# Migrations are applied by docker-compose before this command runs. Running
# uvicorn alone keeps the container restartable and avoids two replicas racing
# to migrate the same database.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
