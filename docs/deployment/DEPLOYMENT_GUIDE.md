# AWS ECS Express Mode Deployment Guide

This guide details the step-by-step process to deploy your containerized FastAPI application to AWS using the recommended **Amazon ECS Express Mode** pipeline.

---

## 📋 Prerequisites
Before deploying, ensure you have:
1. An AWS Account.
2. The AWS CLI installed and configured locally (`aws configure`).
3. Docker running on your local machine.
4. Your ECR repository created: `475632990529.dkr.ecr.us-east-2.amazonaws.com/tt_video_editor`.

---

## 🚀 Step 1: Build & Push to Amazon ECR

Because you are building on a Mac (Apple Silicon), you must build your image for the target architecture of ECS Fargate (`linux/amd64`).

1. **Log in to ECR**:
   Run the login command in your terminal:
   ```bash
   aws ecr get-login-password --region us-east-2 | docker login --username AWS --password-stdin 475632990529.dkr.ecr.us-east-2.amazonaws.com
   ```

2. **Build the Docker Image**:
   Build the image forcing the Intel/AMD64 target platform:
   ```bash
   docker build --platform linux/amd64 -t tt_video_editor .
   ```

3. **Tag the Image**:
   Tag the image for your ECR repository:
   ```bash
   docker tag tt_video_editor:latest 475632990529.dkr.ecr.us-east-2.amazonaws.com/tt_video_editor:latest
   ```

4. **Push the Image**:
   Push the image to Amazon ECR:
   ```bash
   docker push 475632990529.dkr.ecr.us-east-2.amazonaws.com/tt_video_editor:latest
   ```

---

## 🏗️ Step 2: Deploy using ECS Express Mode

AWS ECS Express Mode automates the creation of VPCs, subnets, routing tables, target groups, Application Load Balancers, and scaling configurations in a single process.

1. **Open ECS Console**:
   * Navigate to the **Amazon ECS Console**.
   * Select the **us-east-2 (Ohio)** region in the top-right corner.

2. **Create the Cluster**:
   * Click **Create Cluster** in the left navigation sidebar.
   * Cluster Name: **`main`**.
   * Under Infrastructure, select **AWS Fargate (serverless)**.
   * Click **Create**.

3. **Deploy the Service**:
   * Navigate to the newly created `main` cluster.
   * Under the **Services** tab, click **Deploy**.
   * Under **Deployment Configuration**:
     * **Application Type**: Select **Service**.
     * **Family**: Enter a name (e.g. `tt-video-editor-task`).
     * **Image URI**: Enter your ECR URI: `475632990529.dkr.ecr.us-east-2.amazonaws.com/tt_video_editor:latest`.
     * **Service Name**: **`tt_video_editor-8212`**.
     * **Desired Tasks**: Set to `1` (for development/testing to save cost) or `2` (for high availability).

4. **Configure Port Mapping**:
   * Under **Container Port Mapping**:
     * Set **Port**: `80`.
     * Set **Protocol**: `HTTP`.

5. **Enable Networking & Load Balancing**:
   * Under the **Networking** section:
     * ECS Express Mode will automatically generate a default VPC and Subnets.
   * Under **Load Balancing**:
     * Select **Application Load Balancer (ALB)**.
     * Express Mode will automatically provision a new ALB and Target Group routing public traffic on Port `80` to your container's Port `80`.

6. **Configure Environment Variables**:
   * Add the following environment variables in the **Environment variables** section to activate DynamoDB:
     * **`DB_TYPE`**: `dynamodb`
     * **`DYNAMODB_TABLE_NAME`**: `tt_video_editor_matches`
     * **`AWS_REGION`**: `us-east-2`
   * Click **Deploy**.

---

## 🔍 Step 3: Verification & Health Monitoring

1. **Wait for Deployment**:
   * ECS will transition your task from `PROVISIONING` -> `PENDING` -> `RUNNING`. This takes roughly 2 minutes.

2. **Verify Load Balancer Target Group**:
   * Navigate to the **EC2 Console** -> **Target Groups**.
   * Select your Target Group, click the **Targets** tab, and verify that the container IP status says **`Healthy`**.

3. **Access Your API**:
   * Navigate to the **EC2 Console** -> **Load Balancers**.
   * Select your load balancer and copy the **DNS name** (e.g., `tt-video-editor-XXXX.us-east-2.elb.amazonaws.com`).
   * Open the URL in your browser:
     * Health check: `http://<YOUR_ALB_DNS>/`
     * Swagger documentation: `http://<YOUR_ALB_DNS>/docs`

---

## 🛠️ Troubleshooting

* **Task crashes with `CannotPullContainerError`**:
  * Ensure the local image was built using the `--platform linux/amd64` flag on your Mac.
* **Health Check fails with 403 or Timeout**:
  * Check the **Security Group** attached to your Load Balancer and Task to ensure it allows inbound HTTP (Port 80) traffic.
* **Database Connection fails / Unauthorized**:
   * Ensure that the **ECS Task Role** (not the execution role) has the `ECS-DynamoDB-MatchesPolicy` IAM policy attached, granting access to the `tt_video_editor_matches` table.
   * Make sure your Fargate task's environment variables (`DB_TYPE` and `DYNAMODB_TABLE_NAME`) match your AWS setup.
