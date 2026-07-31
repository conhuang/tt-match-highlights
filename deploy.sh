#!/usr/bin/env bash
set -euo pipefail

# Configuration with environment defaults
AWS_REGION="${AWS_REGION:-us-east-2}"
EC2_INSTANCE_ID="${EC2_INSTANCE_ID:-i-0ddbb277eaf3c1889}"
ECR_REGISTRY="${ECR_REGISTRY:-475632990529.dkr.ecr.us-east-2.amazonaws.com}"
ECR_REPOSITORY="${ECR_REPOSITORY:-tt_video_editor}"
GIT_SHA="${GIT_COMMIT_SHA:-${GITHUB_SHA:-latest}}"

echo "🚀 Starting remote deployment to EC2 instance: $EC2_INSTANCE_ID ($AWS_REGION)..."

COMMAND_ID=$(aws ssm send-command \
  --instance-ids "$EC2_INSTANCE_ID" \
  --document-name "AWS-RunShellScript" \
  --parameters "commands=[
    \"aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REGISTRY\",
    \"docker image prune -a -f\",
    \"docker pull $ECR_REGISTRY/$ECR_REPOSITORY:latest\",
    \"docker stop tt_app || true\",
    \"docker rm tt_app || true\",
    \"docker run -d --name tt_app --restart always -p 80:80 -e STORAGE_TYPE=s3 -e S3_BUCKET_NAME=tt-video-editor-storage -e DATABASE_TYPE=dynamodb -e DYNAMODB_TABLE_NAME=tt_video_editor_matches -e AWS_REGION=$AWS_REGION -e GIT_COMMIT_SHA=$GIT_SHA $ECR_REGISTRY/$ECR_REPOSITORY:latest\"
  ]" \
  --region "$AWS_REGION" \
  --query "Command.CommandId" --output text)

echo "📌 Submitted SSM Command ID: $COMMAND_ID"
echo "⏳ Waiting for remote execution on EC2..."

aws ssm wait command-executed \
  --command-id "$COMMAND_ID" \
  --instance-id "$EC2_INSTANCE_ID" \
  --region "$AWS_REGION" || true

STATUS=$(aws ssm get-command-invocation \
  --command-id "$COMMAND_ID" \
  --instance-id "$EC2_INSTANCE_ID" \
  --region "$AWS_REGION" \
  --query "Status" --output text)

if [ "$STATUS" != "Success" ]; then
  echo "❌ Deployment command failed on EC2 with status: $STATUS"
  aws ssm get-command-invocation \
    --command-id "$COMMAND_ID" \
    --instance-id "$EC2_INSTANCE_ID" \
    --region "$AWS_REGION" \
    --query "StandardErrorContent" --output text
  exit 1
fi

echo "✅ Deployment completed successfully on EC2!"
