#!/bin/bash

# 1. Build React frontend static assets
echo "📦 Building React frontend..."
(cd frontend && npm run build)
echo ""

# 2. Find the environment file (prefer .env.dev, fallback to .env)
ENV_FILE=""
if [ -f .env.dev ]; then
    ENV_FILE=".env.dev"
elif [ -f .env ]; then
    ENV_FILE=".env"
fi

# Ensure default configurations if not overridden by the env file
export STORAGE_TYPE="${STORAGE_TYPE:-s3}"
export S3_BUCKET_NAME="${S3_BUCKET_NAME:-tt-video-editor-storage}"
export AWS_REGION="${AWS_REGION:-us-east-2}"

echo "Starting FastAPI Development Server..."
echo "  Storage:   $STORAGE_TYPE"
echo "  S3 Bucket: $S3_BUCKET_NAME"
echo "  Region:    $AWS_REGION"
echo "  Web App UI: http://localhost:8000/"
echo "  Swagger UI: http://localhost:8000/docs"

if [ -n "$ENV_FILE" ]; then
    echo "  Config:    Loading from $ENV_FILE"
    # Run uvicorn server in virtual environment using native env-file support
    .venv/bin/uvicorn app.main:app --reload --port 8000 --env-file "$ENV_FILE"
else
    echo "  Config:    Using system environment variables"
    .venv/bin/uvicorn app.main:app --reload --port 8000
fi
