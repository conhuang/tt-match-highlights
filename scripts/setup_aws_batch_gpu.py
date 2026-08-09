#!/usr/bin/env python3
import os
import sys
import json
import time
import subprocess
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("setup_batch_gpu")

AWS_REGION = os.getenv("AWS_REGION", "us-east-2")
ECR_REPO_NAME = "tt-video-editor-gpu-worker"
COMPUTE_ENV_NAME = "tt-video-editor-gpu-spot-env"
JOB_QUEUE_NAME = "tt-video-editor-gpu-queue"
JOB_DEF_NAME = "tt-video-editor-gpu-renderer"

def run_cmd(cmd, check=True):
    logger.info(f"Running command: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    res = subprocess.run(cmd, shell=isinstance(cmd, str), capture_output=True, text=True)
    if check and res.returncode != 0:
        logger.error(f"Command failed (exit {res.returncode}):\nSTDOUT: {res.stdout}\nSTDERR: {res.stderr}")
        sys.exit(res.returncode)
    return res.stdout.strip()

def main():
    try:
        import boto3
    except ImportError:
        logger.error("boto3 required. Install with `pip install boto3`.")
        sys.exit(1)

    sts = boto3.client("sts", region_name=AWS_REGION)
    account_id = sts.get_caller_identity()["Account"]
    logger.info(f"Connected to AWS Account: {account_id} in region {AWS_REGION}")

    ecr_client = boto3.client("ecr", region_name=AWS_REGION)
    batch_client = boto3.client("batch", region_name=AWS_REGION)
    iam_client = boto3.client("iam", region_name=AWS_REGION)

    # 1. ECR Repository Setup
    logger.info("Step 1: Setting up ECR Repository...")
    try:
        ecr_client.describe_repositories(repositoryNames=[ECR_REPO_NAME])
        logger.info(f"ECR repository {ECR_REPO_NAME} already exists.")
    except ecr_client.exceptions.RepositoryNotFoundException:
        logger.info(f"Creating ECR repository {ECR_REPO_NAME}...")
        ecr_client.create_repository(repositoryName=ECR_REPO_NAME)

    ecr_uri = f"{account_id}.dkr.ecr.{AWS_REGION}.amazonaws.com/{ECR_REPO_NAME}:latest"

    # 2. Build & Push GPU Worker Container
    logger.info(f"Step 2: Building and pushing Docker container to {ecr_uri}...")
    run_cmd(f"aws ecr get-login-password --region {AWS_REGION} | docker login --username AWS --password-stdin {account_id}.dkr.ecr.{AWS_REGION}.amazonaws.com")
    run_cmd(f"docker build -t {ECR_REPO_NAME}:latest -f docker/Dockerfile.gpu .")
    run_cmd(f"docker tag {ECR_REPO_NAME}:latest {ecr_uri}")
    run_cmd(f"docker push {ecr_uri}")
    logger.info("Successfully pushed GPU Worker image to ECR!")

    # 3. Create IAM Roles if missing
    logger.info("Step 3: Verifying IAM Service & Task Execution Roles...")
    ecs_task_execution_role_arn = f"arn:aws:iam::{account_id}:role/ecsTaskExecutionRole"
    try:
        iam_client.get_role(RoleName="ecsTaskExecutionRole")
    except iam_client.exceptions.NoSuchEntityException:
        logger.info("Creating ecsTaskExecutionRole...")
        assume_role_policy = {
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Principal": {"Service": "ecs-tasks.amazonaws.com"},
                "Action": "sts:AssumeRole"
            }]
        }
        iam_client.create_role(
            RoleName="ecsTaskExecutionRole",
            AssumeRolePolicyDocument=json.dumps(assume_role_policy)
        )
        iam_client.attach_role_policy(
            RoleName="ecsTaskExecutionRole",
            PolicyArn="arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
        )
        iam_client.attach_role_policy(
            RoleName="ecsTaskExecutionRole",
            PolicyArn="arn:aws:iam::aws:policy/AmazonS3FullAccess"
        )
        iam_client.attach_role_policy(
            RoleName="ecsTaskExecutionRole",
            PolicyArn="arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess"
        )

    # 4. AWS Batch Compute Environment
    logger.info("Step 4: Setting up AWS Batch Compute Environment (Spot g4dn.xlarge, Scale-to-Zero)...")
    comp_envs = batch_client.describe_compute_environments(computeEnvironments=[COMPUTE_ENV_NAME])
    if not comp_envs.get("computeEnvironments"):
        # Get default VPC subnets & security groups
        ec2_client = boto3.client("ec2", region_name=AWS_REGION)
        vpcs = ec2_client.describe_vpcs(Filters=[{"Name": "isDefault", "Values": ["true"]}])
        vpc_id = vpcs["Vpcs"][0]["VpcId"] if vpcs.get("Vpcs") else None
        subnets = [s["SubnetId"] for s in ec2_client.describe_subnets(Filters=[{"Name": "vpc-id", "Values": [vpc_id]}])["Subnets"]]
        sgs = [sg["GroupId"] for sg in ec2_client.describe_security_groups(Filters=[{"Name": "vpc-id", "Values": [vpc_id]}])["SecurityGroups"]]

        batch_service_role = f"arn:aws:iam::{account_id}:role/aws-service-role/batch.amazonaws.com/AWSServiceRoleForBatch"

        logger.info(f"Creating AWS Batch Compute Environment: {COMPUTE_ENV_NAME}")
        batch_client.create_compute_environment(
            computeEnvironmentName=COMPUTE_ENV_NAME,
            type="MANAGED",
            state="ENABLED",
            computeResources={
                "type": "SPOT",
                "allocationStrategy": "SPOT_CAPACITY_OPTIMIZED",
                "minvCpus": 0,
                "maxvCpus": 16,
                "desiredvCpus": 0,
                "instanceTypes": ["g4dn.xlarge"],
                "subnets": subnets,
                "securityGroupIds": sgs,
                "instanceRole": f"arn:aws:iam::{account_id}:instance-profile/ecsInstanceRole"
            },
            serviceRole=batch_service_role
        )
        logger.info("Waiting for Compute Environment to become VALID...")
        time.sleep(15)

    # 5. AWS Batch Job Queue
    logger.info("Step 5: Setting up AWS Batch Job Queue...")
    job_queues = batch_client.describe_job_queues(jobQueues=[JOB_QUEUE_NAME])
    if not job_queues.get("jobQueues"):
        logger.info(f"Creating Job Queue: {JOB_QUEUE_NAME}")
        batch_client.create_job_queue(
            jobQueueName=JOB_QUEUE_NAME,
            state="ENABLED",
            priority=1,
            computeEnvironmentOrder=[{"order": 1, "computeEnvironment": COMPUTE_ENV_NAME}]
        )
        time.sleep(5)

    # 6. AWS Batch Job Definition
    logger.info("Step 6: Registering AWS Batch Job Definition...")
    job_def_resp = batch_client.register_job_definition(
        jobDefinitionName=JOB_DEF_NAME,
        type="container",
        containerProperties={
            "image": ecr_uri,
            "vcpus": 4,
            "memory": 8192,
            "jobRoleArn": ecs_task_execution_role_arn,
            "executionRoleArn": ecs_task_execution_role_arn,
            "resourceRequirements": [
                {"type": "GPU", "value": "1"}
            ]
        }
    )
    job_def_arn = job_def_resp["jobDefinitionArn"]
    logger.info(f"Registered Job Definition: {job_def_arn}")

    logger.info("\n🎉 AWS Batch GPU Infrastructure setup complete!")
    logger.info(f"Set the following env vars in deploy.sh / EC2 environment:")
    logger.info(f"  AWS_BATCH_JOB_QUEUE={JOB_QUEUE_NAME}")
    logger.info(f"  AWS_BATCH_JOB_DEF={JOB_DEF_NAME}\n")

if __name__ == "__main__":
    main()
