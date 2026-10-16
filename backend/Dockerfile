# Build context must be the repo root (not backend/) so the data directory is accessible.
# docker build -f backend/Dockerfile -t <image> .
# docker-compose uses context: . with dockerfile: backend/Dockerfile

FROM python:3.12-slim

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

# Bake the source spreadsheet into the image so the ingestion job can run
# without needing a bind-mount or kubectl cp.
COPY data/ /data/

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
