
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    BHARATSTOCK_MODEL_DIR=/app/model_artifacts

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt \
    && useradd --create-home --uid 10001 appuser

# Application source
COPY app ./app

# Include automated tests in the API image
COPY tests ./tests

# Preserve model artifact directory and permissions
RUN mkdir -p /app/model_artifacts \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=4s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# Include isolated ML feature research tools
COPY research ./research
