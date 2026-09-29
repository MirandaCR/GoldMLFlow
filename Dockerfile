# ╔══════════════════════════════════════════════════════════════════╗
# ║  Dockerfile — packs the API + champion model into a "food truck"  ║
# ║  Empaqueta la API + el modelo campeón en un "food truck"          ║
# ║                                                                   ║
# ║  Build:  docker build -t goldmlflow-api .                         ║
# ║  Run:    docker run -p 8000:8000 goldmlflow-api                   ║
# ╚══════════════════════════════════════════════════════════════════╝
FROM python:3.12-slim

# Don't write .pyc files, print logs immediately
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MODEL_DIR=/app/models/champion

WORKDIR /app

# 1) Dependencies first → Docker caches this layer (faster rebuilds)
#    Primero dependencias → Docker cachea esta capa (builds más rápidos)
COPY requirements-api.txt .
RUN pip install --no-cache-dir -r requirements-api.txt

# 2) Only the code the API needs + the champion model
#    Solo el código que la API necesita + el modelo campeón
COPY params.yaml .
COPY src/__init__.py src/utils.py src/
COPY src/features/ src/features/
COPY src/api/ src/api/
COPY models/champion/ models/champion/

# 3) Run as a non-root user (security good practice)
RUN useradd --create-home appuser
USER appuser

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
