#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

echo "=== ECR Deployment Script ==="

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    echo "ERROR: Docker daemon is not running. Please start Docker and try again."
    exit 1
fi

# Prompt for inputs if they aren't set in environment
if [ -z "$AWS_REGION" ]; then
    read -p "Enter AWS Region (e.g., us-east-1): " AWS_REGION
fi

if [ -z "$AWS_ACCOUNT_ID" ]; then
    read -p "Enter AWS Account ID (12-digit number): " AWS_ACCOUNT_ID
fi

if [ -z "$ECR_REPO_NAME" ]; then
    read -p "Enter ECR Repository Name: " ECR_REPO_NAME
fi

# Construct variables
ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
IMAGE_TAG="${ECR_REGISTRY}/${ECR_REPO_NAME}:latest"

echo ""
echo "Configuration Details:"
echo "- Region: $AWS_REGION"
echo "- Account ID: $AWS_ACCOUNT_ID"
echo "- Registry: $ECR_REGISTRY"
echo "- Repository: $ECR_REPO_NAME"
echo "- Image Tag: $IMAGE_TAG"
echo ""

# Step 1: Login to ECR
echo "1. Logging in to Amazon ECR..."
aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "$ECR_REGISTRY"

# Step 2: Build the Docker image
echo "2. Building Docker image..."
docker build --platform linux/amd64 -t "$ECR_REPO_NAME" .

# Step 3: Tag the Docker image
echo "3. Tagging Docker image..."
docker tag "${ECR_REPO_NAME}:latest" "$IMAGE_TAG"

# Step 4: Push the Docker image
echo "4. Pushing Docker image to ECR..."
docker push "$IMAGE_TAG"

echo "=== Deployment to ECR complete! ==="
echo "You can now deploy this image in ECS using the ECS Console or ECS Express Mode."
