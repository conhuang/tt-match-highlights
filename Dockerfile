# 1. Build React Frontend Stage
FROM node:18-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# 2. Final Python App Stage
FROM python:3.11-slim
WORKDIR /app

# Install system dependencies (e.g. ffmpeg if needed in production)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY app/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Copy compiled React static assets from Stage 1 into app/static/
COPY --from=frontend-builder /app/app/static /app/app/static

EXPOSE 80
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]