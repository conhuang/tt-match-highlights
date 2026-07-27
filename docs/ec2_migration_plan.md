# Complete EC2 Migration Guide & Command Log

## Overview
Migrated the `tt_video_editor` application from **AWS ECS Fargate + Application Load Balancer (~$90–$95/month)** to a single **`t4g.small` (ARM64 Graviton2) EC2 instance (~$12.26/month)**, cutting monthly AWS infrastructure costs by **~85%**.

* **Live Server IP**: `http://3.144.150.60`
* **Instance ID**: `i-0ddbb277eaf3c1889`
* **Region**: `us-east-2` (Ohio)

---

## Exact Commands Executed

### Step 1: Create IAM Role & Instance Profile
Created an IAM Role and Instance Profile to grant the EC2 instance access to S3, DynamoDB, ECR, and Systems Manager without needing hardcoded credentials.

```bash
# 1. Create trust policy allowing EC2 service to assume role
aws iam create-role \
  --role-name tt_video_editor_ec2_role \
  --assume-role-policy-document file://scratch/ec2_trust_policy.json

# 2. Attach inline permissions policy for S3, DynamoDB, and ECR
aws iam put-role-policy \
  --role-name tt_video_editor_ec2_role \
  --policy-name TTVideoEditorEC2Policy \
  --policy-document file://scratch/ec2_policy.json

# 3. Attach AWS Managed Policy for Systems Manager (SSM) remote management
aws iam attach-role-policy \
  --role-name tt_video_editor_ec2_role \
  --policy-arn arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore

# 4. Create Instance Profile & attach role to it
aws iam create-instance-profile --instance-profile-name tt_video_editor_ec2_profile
aws iam add-role-to-instance-profile \
  --instance-profile-name tt_video_editor_ec2_profile \
  --role-name tt_video_editor_ec2_role
```

---

### Step 2: Create Security Group & Open Inbound Ports
Created a Security Group `tt-video-editor-ec2-sg` allowing inbound HTTP (port 80), HTTPS (port 443), and SSH (port 22).

```bash
# 1. Create Security Group in default VPC
aws ec2 create-security-group \
  --group-name tt-video-editor-ec2-sg \
  --description "Security group for TT Video Editor EC2 instance" \
  --vpc-id vpc-022be172aa04366eb \
  --region us-east-2

# 2. Authorize Port 80 (HTTP), Port 443 (HTTPS), and Port 22 (SSH)
aws ec2 authorize-security-group-ingress --group-name tt-video-editor-ec2-sg --protocol tcp --port 80 --cidr 0.0.0.0/0 --region us-east-2
aws ec2 authorize-security-group-ingress --group-name tt-video-editor-ec2-sg --protocol tcp --port 443 --cidr 0.0.0.0/0 --region us-east-2
aws ec2 authorize-security-group-ingress --group-name tt-video-editor-ec2-sg --protocol tcp --port 22 --cidr 0.0.0.0/0 --region us-east-2
```

---

### Step 3: Launch `t4g.small` ARM EC2 Instance
Launched the instance with the Amazon Linux 2023 ARM64 AMI, attaching the IAM Instance Profile and automated User-Data provisioning script.

```bash
# 1. Lookup latest AL2023 ARM64 AMI ID (ami-0f149f4742f21a6a4)
aws ssm get-parameters --names /aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-arm64 --region us-east-2

# 2. Launch instance
aws ec2 run-instances \
  --image-id ami-0f149f4742f21a6a4 \
  --instance-type t4g.small \
  --security-group-ids sg-02c91476e8aa76fa7 \
  --iam-instance-profile Name=tt_video_editor_ec2_profile \
  --user-data file://scratch/ec2_userdata.sh \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=tt-video-editor-server}]' \
  --region us-east-2
```

---

### Step 4: Automated EC2 User-Data Provisioning (`scratch/ec2_userdata.sh`)
The instance runs this script on first boot to install software, configure Nginx, clone the repository, and start the Docker container:

```bash
#!/bin/bash
set -e

# Install Docker, Nginx, Git, and AWS CLI
dnf update -y
dnf install -y docker nginx git aws-cli

systemctl start docker
systemctl enable docker
systemctl start nginx
systemctl enable nginx

# Configure Nginx reverse proxy (Port 80 -> Container Port 8000)
cat << 'EOF' > /etc/nginx/conf.d/tt_video_editor.conf
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;

    client_max_body_size 500M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

nginx -t
systemctl restart nginx

# Clone repo & build native ARM64 container
cd /tmp && rm -rf app
git clone https://github.com/conhuang/tt-match-highlights.git app
cd app

docker build -t tt_app_arm .

docker run -d \
  --name tt_app \
  --restart always \
  -p 8000:80 \
  -e STORAGE_TYPE=s3 \
  -e S3_BUCKET_NAME=tt-video-editor-storage \
  -e DB_TYPE=dynamodb \
  -e DYNAMODB_TABLE_NAME=tt_video_editor_matches \
  -e AWS_REGION=us-east-2 \
  tt_app_arm
```

---

### Step 5: Stop Fargate & Delete Application Load Balancer
Froze Fargate compute billing and removed the Application Load Balancer to eliminate base fees.

```bash
# 1. Scale Fargate desired count to 0
aws ecs update-service --cluster default --service tt_video_editor-8212 --desired-count 0 --region us-east-2

# 2. Delete Application Load Balancer ($16.20/mo saved)
aws elbv2 delete-load-balancer \
  --load-balancer-arn arn:aws:elasticloadbalancing:us-east-2:475632990529:loadbalancer/app/ecs-express-gateway-alb-240cdaf3/32bcd0d30551922e \
  --region us-east-2
```

---

### Step 6: Configure S3 Lifecycle Rule for Incomplete Upload Cleanup
Configured S3 to purge incomplete multipart upload chunks older than 7 days on both production and test buckets:

```bash
aws s3api put-bucket-lifecycle-configuration \
  --bucket tt-video-editor-storage \
  --lifecycle-configuration file://scratch/s3_lifecycle.json

aws s3api put-bucket-lifecycle-configuration \
  --bucket tt-video-editor-storage-test \
  --lifecycle-configuration file://scratch/s3_lifecycle.json
```

---

### Step 7: Continuous Integration & Deployment (GitHub Actions)
Updated `.github/workflows/deploy.yml` so that pushing code to `main` automatically builds an ARM64 image with `docker buildx` and triggers an AWS SSM command on `i-0ddbb277eaf3c1889` to pull and restart the container seamlessly.

---

## Final Cost Comparison

| Component | Before (Fargate + ALB) | After (Single EC2 `t4g.small`) |
| :--- | :--- | :--- |
| **Compute** | 2 Fargate Tasks ($71.10/mo) | 1 EC2 `t4g.small` ($12.26/mo) |
| **Load Balancer** | ALB Base Fee ($16.20/mo) | Nginx Reverse Proxy ($0.00/mo) |
| **Database** | DynamoDB PAY_PER_REQUEST (~$0/mo) | DynamoDB PAY_PER_REQUEST (~$0/mo) |
| **Storage** | S3 Standard (~$1-2/mo) | S3 Standard (~$1-2/mo) |
| **Total Monthly Bill** | **~$89 – $95 / month** | **~$12.26 / month (~85% Savings)** |
