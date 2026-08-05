# === KIDSFLOW backend image ===
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Tizim bog'liqliklari (asyncpg build uchun minimal talab).
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Bog'liqliklarni alohida qatlamda o'rnatish (keshdan foydalanish uchun).
COPY requirements.txt requirements-dev.txt ./
RUN pip install -r requirements.txt

# Ilova kodi.
COPY . .

# Root bo'lmagan foydalanuvchi.
RUN useradd --create-home --uid 1000 appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Healthcheck (12-bo'lim).
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:8000/api/v1/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
