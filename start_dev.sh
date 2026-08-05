#!/bin/bash

# 1. Find the environment file (prefer .env.dev, fallback to .env)
ENV_FILE=""
if [ -f .env.dev ]; then
    ENV_FILE=".env.dev"
elif [ -f .env ]; then
    ENV_FILE=".env"
fi

if [ -n "$ENV_FILE" ]; then
    echo "  Config:    Loading from $ENV_FILE"
    set -a
    source "$ENV_FILE"
    set +a
fi

# Ensure default configurations if not overridden by the env file
export DB_TYPE="${DB_TYPE:-dynamodb}"
export DYNAMODB_TABLE_NAME="${DYNAMODB_TABLE_NAME:-tt_video_editor_matches_dev}"
export STORAGE_TYPE="${STORAGE_TYPE:-s3}"
export S3_BUCKET_NAME="${S3_BUCKET_NAME:-tt-video-editor-storage-test}"
export AWS_REGION="${AWS_REGION:-us-east-2}"
export VITE_GOOGLE_CLIENT_ID="${VITE_GOOGLE_CLIENT_ID:-$GOOGLE_CLIENT_ID}"
export DISABLE_AUTH="${DISABLE_AUTH:-true}"

# 2. Build React frontend static assets
echo "📦 Building React frontend..."
(cd frontend && VITE_GOOGLE_CLIENT_ID="${VITE_GOOGLE_CLIENT_ID:-$GOOGLE_CLIENT_ID}" npm run build)
echo ""

echo "Starting FastAPI Development Server..."
echo "  Database:  $DB_TYPE (Table: $DYNAMODB_TABLE_NAME)"
echo "  Storage:   $STORAGE_TYPE (Bucket: $S3_BUCKET_NAME)"
echo "  Region:    $AWS_REGION"
echo "  Web App UI: http://localhost:8000/"
echo "  Swagger UI: http://localhost:8000/docs"

.venv/bin/uvicorn app.main:app --reload --port 8000
