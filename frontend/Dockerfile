# syntax=docker/dockerfile:1
# Streamlit frontend image. Build from the repository root so the build context
# includes only `frontend/`; see the `frontend` service in docker-compose.yml.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN groupadd --system app \
    && useradd --system --gid app --home-dir /app --shell /usr/sbin/nologin app

COPY frontend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=app:app frontend/ ./

USER app

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import sys,urllib.request; \
sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health', timeout=4).status == 200 else 1)"

# `--server.address 0.0.0.0` is required inside a container; the theme and
# headless flag come from .streamlit/config.toml.
CMD ["python", "-m", "streamlit", "run", "app.py", \
     "--server.address", "0.0.0.0", "--server.port", "8501"]
