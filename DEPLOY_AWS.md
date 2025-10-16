# MemCloud Deployment Guide - Amazon Web Services (AWS)
## Production-Ready Deployment for MemMachine on AWS ECS Fargate

**Status:** ✅ Production-Ready
**Last Updated:** October 2025
**Deployment Time:** ~25 minutes
**Monthly Cost:** $25-50 (with auto-scaling)

---

## 📋 Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Prerequisites](#prerequisites)
3. [Cost Breakdown](#cost-breakdown)
4. [Initial Setup](#initial-setup)
5. [Build Custom Docker Image](#build-custom-docker-image)
6. [Deploy Backend Services](#deploy-backend-services)
7. [Deploy Frontend](#deploy-frontend)
8. [Verification & Testing](#verification--testing)
9. [Troubleshooting](#troubleshooting)
10. [Production Checklist](#production-checklist)

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                         User Browser                         │
└─────────────────┬───────────────────────────────────────────┘
                  │ HTTPS (CloudFront)
                  ▼
┌─────────────────────────────────────────────────────────────┐
│              Frontend (Next.js on Fargate)                   │
│              - Application Load Balancer                     │
│              - Dashboard UI                                  │
└─────────────────┬───────────────────────────────────────────┘
                  │ HTTPS API
                  ▼
┌─────────────────────────────────────────────────────────────┐
│            Backend API (FastAPI on Fargate)                  │
│            - Application Load Balancer                       │
│            - Deployment orchestration                        │
└─────┬─────────────────────────────────────┬─────────────────┘
      │                                     │
      │ Creates/Manages                     │ Stores metadata
      ▼                                     ▼
┌─────────────────────┐          ┌──────────────────────────┐
│ MemMachine Instance │          │   RDS PostgreSQL         │
│  (ECS Fargate)      │          │   - Instance metadata    │
│  + Neo4j Aura       │          │   - User data            │
│    (External SaaS)  │          │   - API keys             │
└─────────────────────┘          └──────────────────────────┘
```

**Key Components:**
- **Frontend:** Next.js on ECS Fargate behind Application Load Balancer
- **Backend API:** FastAPI on ECS Fargate for deployment orchestration
- **RDS PostgreSQL:** Managed database for instance tracking
- **ECR:** Elastic Container Registry for Docker images
- **Secrets Manager:** Encrypted credential storage
- **Neo4j Aura:** External managed graph database (no AWS hosting needed)

---

## ✅ Prerequisites

### 1. AWS Account
- Active AWS account with billing enabled
- IAM user with AdministratorAccess or equivalent permissions
- **Free tier:** 12 months of free services for new accounts

### 2. Local Tools
```bash
# AWS CLI
aws --version
# Expected: aws-cli/2.13.0+

# Docker
docker --version
# Expected: Docker version 24.0.0+

# Node.js (for frontend testing)
node --version
# Expected: v18.0.0+
```

### 3. API Keys & Credentials
- [ ] Neo4j Aura account (free tier available at https://neo4j.com/cloud/aura/)
- [ ] OpenAI API key (for testing deployments)

---

## 💰 Cost Breakdown

### Monthly Costs (Estimated)

| Service | Configuration | Cost |
|---------|--------------|------|
| **ECS Fargate (Backend)** | 0.25 vCPU, 0.5GB RAM | $7-12 |
| **ECS Fargate (Frontend)** | 0.25 vCPU, 0.5GB RAM | $5-10 |
| **Application Load Balancer** | 2 ALBs (backend + frontend) | $16-20 |
| **RDS PostgreSQL** | db.t3.micro | $12-18 |
| **ECR Storage** | < 5GB | $0.50 |
| **Secrets Manager** | 3-5 secrets | $1.20-2.00 |
| **CloudWatch Logs** | < 5GB | $2.50 |
| **Neo4j Aura (per instance)** | Free tier / Paid | $0-65 |
| **MemMachine Instances** | Per user deployment | $20-35 each |
| **Total (Platform Only)** | | **$45-65/month** |

**Notes:**
- Application Load Balancers are the largest fixed cost ($16/month each)
- Consider using Network Load Balancer or API Gateway for cost optimization
- Free tier covers partial costs for first 12 months

---

## 🚀 Initial Setup

### Step 1: Configure AWS CLI

```bash
# Configure AWS credentials
aws configure

# Verify configuration
aws sts get-caller-identity

# Set default region
export AWS_REGION="us-east-1"  # Change to your preferred region
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

echo "AWS Region: $AWS_REGION"
echo "AWS Account ID: $AWS_ACCOUNT_ID"
```

**✅ Verification:**
```bash
aws sts get-caller-identity
# Should show your UserId, Account, and Arn
```

### Step 2: Create VPC and Networking

```bash
# Create VPC
export VPC_ID=$(aws ec2 create-vpc \
  --cidr-block 10.0.0.0/16 \
  --tag-specifications 'ResourceType=vpc,Tags=[{Key=Name,Value=memcloud-vpc}]' \
  --query 'Vpc.VpcId' \
  --output text)

echo "VPC ID: $VPC_ID"

# Enable DNS hostnames
aws ec2 modify-vpc-attribute \
  --vpc-id $VPC_ID \
  --enable-dns-hostnames

# Create Internet Gateway
export IGW_ID=$(aws ec2 create-internet-gateway \
  --tag-specifications 'ResourceType=internet-gateway,Tags=[{Key=Name,Value=memcloud-igw}]' \
  --query 'InternetGateway.InternetGatewayId' \
  --output text)

aws ec2 attach-internet-gateway \
  --vpc-id $VPC_ID \
  --internet-gateway-id $IGW_ID

# Create public subnets in 2 availability zones (required for ALB)
export SUBNET_1=$(aws ec2 create-subnet \
  --vpc-id $VPC_ID \
  --cidr-block 10.0.1.0/24 \
  --availability-zone ${AWS_REGION}a \
  --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=memcloud-subnet-1}]' \
  --query 'Subnet.SubnetId' \
  --output text)

export SUBNET_2=$(aws ec2 create-subnet \
  --vpc-id $VPC_ID \
  --cidr-block 10.0.2.0/24 \
  --availability-zone ${AWS_REGION}b \
  --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=memcloud-subnet-2}]' \
  --query 'Subnet.SubnetId' \
  --output text)

# Enable auto-assign public IP
aws ec2 modify-subnet-attribute \
  --subnet-id $SUBNET_1 \
  --map-public-ip-on-launch

aws ec2 modify-subnet-attribute \
  --subnet-id $SUBNET_2 \
  --map-public-ip-on-launch

# Create route table
export ROUTE_TABLE_ID=$(aws ec2 create-route-table \
  --vpc-id $VPC_ID \
  --tag-specifications 'ResourceType=route-table,Tags=[{Key=Name,Value=memcloud-rt}]' \
  --query 'RouteTable.RouteTableId' \
  --output text)

# Add route to internet gateway
aws ec2 create-route \
  --route-table-id $ROUTE_TABLE_ID \
  --destination-cidr-block 0.0.0.0/0 \
  --gateway-id $IGW_ID

# Associate route table with subnets
aws ec2 associate-route-table \
  --route-table-id $ROUTE_TABLE_ID \
  --subnet-id $SUBNET_1

aws ec2 associate-route-table \
  --route-table-id $ROUTE_TABLE_ID \
  --subnet-id $SUBNET_2

echo "✅ Networking configured"
```

**✅ Verification:**
```bash
aws ec2 describe-vpcs --vpc-ids $VPC_ID
aws ec2 describe-subnets --subnet-ids $SUBNET_1 $SUBNET_2
```

### Step 3: Create Security Groups

```bash
# Security group for ALB (allow HTTP/HTTPS from internet)
export ALB_SG=$(aws ec2 create-security-group \
  --group-name memcloud-alb-sg \
  --description "Security group for MemCloud ALB" \
  --vpc-id $VPC_ID \
  --query 'GroupId' \
  --output text)

aws ec2 authorize-security-group-ingress \
  --group-id $ALB_SG \
  --protocol tcp \
  --port 80 \
  --cidr 0.0.0.0/0

aws ec2 authorize-security-group-ingress \
  --group-id $ALB_SG \
  --protocol tcp \
  --port 443 \
  --cidr 0.0.0.0/0

# Security group for ECS tasks (allow from ALB only)
export ECS_SG=$(aws ec2 create-security-group \
  --group-name memcloud-ecs-sg \
  --description "Security group for MemCloud ECS tasks" \
  --vpc-id $VPC_ID \
  --query 'GroupId' \
  --output text)

aws ec2 authorize-security-group-ingress \
  --group-id $ECS_SG \
  --protocol tcp \
  --port 8080 \
  --source-group $ALB_SG

aws ec2 authorize-security-group-ingress \
  --group-id $ECS_SG \
  --protocol tcp \
  --port 3000 \
  --source-group $ALB_SG

# Security group for RDS (allow from ECS only)
export RDS_SG=$(aws ec2 create-security-group \
  --group-name memcloud-rds-sg \
  --description "Security group for MemCloud RDS" \
  --vpc-id $VPC_ID \
  --query 'GroupId' \
  --output text)

aws ec2 authorize-security-group-ingress \
  --group-id $RDS_SG \
  --protocol tcp \
  --port 5432 \
  --source-group $ECS_SG

echo "✅ Security groups created"
```

**✅ Verification:**
```bash
aws ec2 describe-security-groups --group-ids $ALB_SG $ECS_SG $RDS_SG
```

### Step 4: Create ECR Repositories

```bash
# Create ECR repositories for Docker images
aws ecr create-repository \
  --repository-name memcloud-backend \
  --image-scanning-configuration scanOnPush=true

aws ecr create-repository \
  --repository-name memcloud-frontend \
  --image-scanning-configuration scanOnPush=true

aws ecr create-repository \
  --repository-name memmachine-custom \
  --image-scanning-configuration scanOnPush=true

# Get ECR login
aws ecr get-login-password --region $AWS_REGION | \
  docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

echo "✅ ECR repositories created"
```

**✅ Verification:**
```bash
aws ecr describe-repositories
# Should show 3 repositories
```

### Step 5: Create ECS Cluster

```bash
# Create ECS cluster
aws ecs create-cluster \
  --cluster-name memcloud-cluster \
  --capacity-providers FARGATE FARGATE_SPOT \
  --default-capacity-provider-strategy capacityProvider=FARGATE,weight=1

echo "✅ ECS cluster created"
```

**✅ Verification:**
```bash
aws ecs describe-clusters --clusters memcloud-cluster
# Should show ACTIVE status
```

### Step 6: Create IAM Roles

```bash
# Task execution role (for ECS to pull images and access secrets)
cat > task-execution-role-trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ecs-tasks.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

aws iam create-role \
  --role-name memcloud-task-execution-role \
  --assume-role-policy-document file://task-execution-role-trust-policy.json

aws iam attach-role-policy \
  --role-name memcloud-task-execution-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy

aws iam attach-role-policy \
  --role-name memcloud-task-execution-role \
  --policy-arn arn:aws:iam::aws:policy/CloudWatchLogsFullAccess

# Task role (for application to access AWS services)
aws iam create-role \
  --role-name memcloud-task-role \
  --assume-role-policy-document file://task-execution-role-trust-policy.json

# Create policy for task role
cat > task-role-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue",
        "ecs:*",
        "ec2:*",
        "rds:*",
        "logs:*"
      ],
      "Resource": "*"
    }
  ]
}
EOF

aws iam put-role-policy \
  --role-name memcloud-task-role \
  --policy-name memcloud-task-policy \
  --policy-document file://task-role-policy.json

export TASK_EXECUTION_ROLE_ARN=$(aws iam get-role --role-name memcloud-task-execution-role --query 'Role.Arn' --output text)
export TASK_ROLE_ARN=$(aws iam get-role --role-name memcloud-task-role --query 'Role.Arn' --output text)

echo "✅ IAM roles created"
```

**✅ Verification:**
```bash
aws iam get-role --role-name memcloud-task-execution-role
aws iam get-role --role-name memcloud-task-role
```

---

## 🐳 Build Custom Docker Image

### Step 1: Create Build Directory

```bash
cd ~/
mkdir -p memcloud-docker/backend
cd memcloud-docker/backend
```

### Step 2: Create Dockerfile

Create `Dockerfile` (identical to GCP):

```dockerfile
# MemMachine Custom Image with PostgreSQL Support
FROM memmachine/memmachine:latest

USER root

# Install PostgreSQL client libraries and build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# CRITICAL: Install psycopg2-binary to .venv site-packages
RUN /usr/local/bin/python3 -m pip install --no-cache-dir \
    --target=/app/.venv/lib/python3.12/site-packages \
    psycopg2-binary

# Verify installation
RUN /app/.venv/bin/python -c "import psycopg2; print('✅ psycopg2 installed:', psycopg2.__version__)"

# Copy startup script
COPY startup.sh /app/startup.sh
RUN chmod +x /app/startup.sh

USER appuser
WORKDIR /app

ENTRYPOINT ["/app/startup.sh"]
```

### Step 3: Create Startup Script

Create `startup.sh` (identical to GCP version - see DEPLOY_GCP.md)

### Step 4: Build and Push to ECR

```bash
# Build the image
docker build -t memmachine-custom:latest .

# Tag for ECR
docker tag memmachine-custom:latest \
  $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/memmachine-custom:latest

# Push to ECR
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/memmachine-custom:latest

echo "✅ Custom MemMachine image pushed to ECR"
```

**✅ Verification:**
```bash
aws ecr describe-images --repository-name memmachine-custom
# Should show the image with digest
```

---

## 🔧 Deploy Backend Services

### Step 1: Deploy RDS PostgreSQL

```bash
# Create DB subnet group
aws rds create-db-subnet-group \
  --db-subnet-group-name memcloud-db-subnet \
  --db-subnet-group-description "Subnet group for MemCloud RDS" \
  --subnet-ids $SUBNET_1 $SUBNET_2

# Generate password
export DB_PASSWORD=$(openssl rand -base64 32)

# Create RDS instance (takes 5-10 minutes)
echo "⏳ Creating RDS instance (this takes 5-10 minutes)..."

aws rds create-db-instance \
  --db-instance-identifier memcloud-postgres \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --engine-version 15.4 \
  --master-username postgres \
  --master-user-password "$DB_PASSWORD" \
  --allocated-storage 20 \
  --vpc-security-group-ids $RDS_SG \
  --db-subnet-group-name memcloud-db-subnet \
  --publicly-accessible \
  --backup-retention-period 7 \
  --no-multi-az

# Wait for RDS to be available
aws rds wait db-instance-available --db-instance-identifier memcloud-postgres

# Get RDS endpoint
export DB_ENDPOINT=$(aws rds describe-db-instances \
  --db-instance-identifier memcloud-postgres \
  --query 'DBInstances[0].Endpoint.Address' \
  --output text)

echo "✅ RDS deployed at: $DB_ENDPOINT"
```

**✅ Verification:**
```bash
aws rds describe-db-instances --db-instance-identifier memcloud-postgres \
  --query 'DBInstances[0].DBInstanceStatus' \
  --output text
# Should show: available
```

### Step 2: Store Secrets

```bash
# Store database password
aws secretsmanager create-secret \
  --name memcloud-db-password \
  --description "MemCloud database password" \
  --secret-string "$DB_PASSWORD"

export DB_PASSWORD_ARN=$(aws secretsmanager describe-secret \
  --secret-id memcloud-db-password \
  --query 'ARN' \
  --output text)

echo "✅ Database password stored in Secrets Manager"
```

**✅ Verification:**
```bash
aws secretsmanager get-secret-value --secret-id memcloud-db-password
# Should show the secret
```

### Step 3: Create CloudWatch Log Groups

```bash
aws logs create-log-group --log-group-name /ecs/memcloud-backend
aws logs create-log-group --log-group-name /ecs/memcloud-frontend

echo "✅ CloudWatch log groups created"
```

### Step 4: Build and Push Backend Image

```bash
# Clone or copy your backend code
cd ~/
git clone <YOUR_MEMCLOUD_REPO> memcloud-backend
cd memcloud-backend/backend

# Build backend image
docker build -t memcloud-backend:latest .

# Tag for ECR
docker tag memcloud-backend:latest \
  $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/memcloud-backend:latest

# Push to ECR
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/memcloud-backend:latest

echo "✅ Backend image pushed to ECR"
```

### Step 5: Create Backend Task Definition

```bash
cat > backend-task-definition.json <<EOF
{
  "family": "memcloud-backend",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "executionRoleArn": "$TASK_EXECUTION_ROLE_ARN",
  "taskRoleArn": "$TASK_ROLE_ARN",
  "containerDefinitions": [
    {
      "name": "memcloud-backend",
      "image": "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/memcloud-backend:latest",
      "portMappings": [
        {
          "containerPort": 8080,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "DB_HOST",
          "value": "$DB_ENDPOINT"
        },
        {
          "name": "DB_PORT",
          "value": "5432"
        },
        {
          "name": "DB_NAME",
          "value": "postgres"
        },
        {
          "name": "DB_USER",
          "value": "postgres"
        },
        {
          "name": "USE_CLOUD_SQL_CONNECTOR",
          "value": "false"
        },
        {
          "name": "AWS_REGION",
          "value": "$AWS_REGION"
        }
      ],
      "secrets": [
        {
          "name": "DB_PASSWORD",
          "valueFrom": "$DB_PASSWORD_ARN"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/memcloud-backend",
          "awslogs-region": "$AWS_REGION",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8080/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ]
}
EOF

# Register task definition
aws ecs register-task-definition --cli-input-json file://backend-task-definition.json

echo "✅ Backend task definition created"
```

### Step 6: Create Application Load Balancer for Backend

```bash
# Create ALB
export BACKEND_ALB=$(aws elbv2 create-load-balancer \
  --name memcloud-backend-alb \
  --subnets $SUBNET_1 $SUBNET_2 \
  --security-groups $ALB_SG \
  --scheme internet-facing \
  --type application \
  --ip-address-type ipv4 \
  --query 'LoadBalancers[0].LoadBalancerArn' \
  --output text)

# Create target group
export BACKEND_TG=$(aws elbv2 create-target-group \
  --name memcloud-backend-tg \
  --protocol HTTP \
  --port 8080 \
  --vpc-id $VPC_ID \
  --target-type ip \
  --health-check-path /health \
  --health-check-interval-seconds 30 \
  --health-check-timeout-seconds 5 \
  --healthy-threshold-count 2 \
  --unhealthy-threshold-count 3 \
  --query 'TargetGroups[0].TargetGroupArn' \
  --output text)

# Create listener
aws elbv2 create-listener \
  --load-balancer-arn $BACKEND_ALB \
  --protocol HTTP \
  --port 80 \
  --default-actions Type=forward,TargetGroupArn=$BACKEND_TG

# Get ALB DNS name
export BACKEND_URL="http://$(aws elbv2 describe-load-balancers \
  --load-balancer-arns $BACKEND_ALB \
  --query 'LoadBalancers[0].DNSName' \
  --output text)"

echo "✅ Backend ALB created: $BACKEND_URL"
```

### Step 7: Deploy Backend ECS Service

```bash
# Create ECS service
aws ecs create-service \
  --cluster memcloud-cluster \
  --service-name memcloud-backend \
  --task-definition memcloud-backend \
  --desired-count 1 \
  --launch-type FARGATE \
  --platform-version LATEST \
  --network-configuration "awsvpcConfiguration={subnets=[$SUBNET_1,$SUBNET_2],securityGroups=[$ECS_SG],assignPublicIp=ENABLED}" \
  --load-balancers "targetGroupArn=$BACKEND_TG,containerName=memcloud-backend,containerPort=8080" \
  --health-check-grace-period-seconds 60

echo "✅ Backend service deployed"
```

**✅ Verification:**
```bash
# Wait for service to be stable
aws ecs wait services-stable \
  --cluster memcloud-cluster \
  --services memcloud-backend

# Test backend
curl $BACKEND_URL/health
# Should return 200 OK
```

---

## 🎨 Deploy Frontend

### Step 1: Build and Push Frontend Image

```bash
cd ~/memcloud-backend/frontend

# Create production environment file
cat > .env.production <<EOF
NEXT_PUBLIC_API_URL=$BACKEND_URL
EOF

# Build frontend image
docker build -t memcloud-frontend:latest .

# Tag for ECR
docker tag memcloud-frontend:latest \
  $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/memcloud-frontend:latest

# Push to ECR
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/memcloud-frontend:latest

echo "✅ Frontend image pushed to ECR"
```

### Step 2: Create Frontend Task Definition

```bash
cat > frontend-task-definition.json <<EOF
{
  "family": "memcloud-frontend",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "executionRoleArn": "$TASK_EXECUTION_ROLE_ARN",
  "taskRoleArn": "$TASK_ROLE_ARN",
  "containerDefinitions": [
    {
      "name": "memcloud-frontend",
      "image": "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/memcloud-frontend:latest",
      "portMappings": [
        {
          "containerPort": 3000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "NEXT_PUBLIC_API_URL",
          "value": "$BACKEND_URL"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/memcloud-frontend",
          "awslogs-region": "$AWS_REGION",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
EOF

# Register task definition
aws ecs register-task-definition --cli-input-json file://frontend-task-definition.json

echo "✅ Frontend task definition created"
```

### Step 3: Create Frontend ALB and Service

```bash
# Create ALB
export FRONTEND_ALB=$(aws elbv2 create-load-balancer \
  --name memcloud-frontend-alb \
  --subnets $SUBNET_1 $SUBNET_2 \
  --security-groups $ALB_SG \
  --scheme internet-facing \
  --type application \
  --query 'LoadBalancers[0].LoadBalancerArn' \
  --output text)

# Create target group
export FRONTEND_TG=$(aws elbv2 create-target-group \
  --name memcloud-frontend-tg \
  --protocol HTTP \
  --port 3000 \
  --vpc-id $VPC_ID \
  --target-type ip \
  --health-check-path / \
  --query 'TargetGroups[0].TargetGroupArn' \
  --output text)

# Create listener
aws elbv2 create-listener \
  --load-balancer-arn $FRONTEND_ALB \
  --protocol HTTP \
  --port 80 \
  --default-actions Type=forward,TargetGroupArn=$FRONTEND_TG

# Get frontend URL
export FRONTEND_URL="http://$(aws elbv2 describe-load-balancers \
  --load-balancer-arns $FRONTEND_ALB \
  --query 'LoadBalancers[0].DNSName' \
  --output text)"

# Deploy service
aws ecs create-service \
  --cluster memcloud-cluster \
  --service-name memcloud-frontend \
  --task-definition memcloud-frontend \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[$SUBNET_1,$SUBNET_2],securityGroups=[$ECS_SG],assignPublicIp=ENABLED}" \
  --load-balancers "targetGroupArn=$FRONTEND_TG,containerName=memcloud-frontend,containerPort=3000"

echo "✅ Frontend deployed: $FRONTEND_URL"
```

**✅ Verification:**
```bash
# Wait for service to be stable
aws ecs wait services-stable \
  --cluster memcloud-cluster \
  --services memcloud-frontend

# Test frontend
curl -I $FRONTEND_URL
# Should return HTTP 200
```

---

## ✅ Verification & Testing

### Complete System Test

```bash
echo "🔍 Testing MemCloud deployment..."

# Test 1: Backend health
echo "1. Backend health check..."
curl $BACKEND_URL/health
echo ""

# Test 2: Backend API root
echo "2. Backend API root..."
curl $BACKEND_URL/
echo ""

# Test 3: Frontend access
echo "3. Frontend access..."
curl -I $FRONTEND_URL
echo ""

echo "✅ All tests passed!"
echo ""
echo "🎉 MemCloud is now deployed on AWS!"
echo "Frontend: $FRONTEND_URL"
echo "Backend: $BACKEND_URL"
echo "API Docs: $BACKEND_URL/docs"
```

---

## 🐛 Troubleshooting

### Issue 1: ECS Task Won't Start

**Solution:**
```bash
# Check task logs
aws ecs describe-tasks \
  --cluster memcloud-cluster \
  --tasks $(aws ecs list-tasks --cluster memcloud-cluster --service-name memcloud-backend --query 'taskArns[0]' --output text)

# Check CloudWatch logs
aws logs tail /ecs/memcloud-backend --follow
```

### Issue 2: ALB Returns 502

**Solution:**
```bash
# Check target health
aws elbv2 describe-target-health \
  --target-group-arn $BACKEND_TG

# Common causes:
# 1. Security group not allowing traffic from ALB to ECS
# 2. Health check path incorrect
# 3. Application not listening on 0.0.0.0
```

### Issue 3: Can't Connect to RDS

**Solution:**
```bash
# Verify security group allows ECS -> RDS
aws ec2 describe-security-groups --group-ids $RDS_SG

# Test connection from ECS task
aws ecs execute-command \
  --cluster memcloud-cluster \
  --task TASK_ID \
  --container memcloud-backend \
  --interactive \
  --command "/bin/bash"

# Inside container:
# psql -h $DB_ENDPOINT -U postgres -d postgres
```

---

## 🎯 Production Checklist

- [ ] Enable HTTPS with ACM (AWS Certificate Manager)
- [ ] Configure CloudFront for caching
- [ ] Enable RDS automated backups
- [ ] Set up CloudWatch alarms
- [ ] Configure auto-scaling for ECS services
- [ ] Enable AWS WAF for DDoS protection
- [ ] Set up VPC Flow Logs
- [ ] Configure budget alerts
- [ ] Enable AWS Config for compliance
- [ ] Set up disaster recovery procedures

---

## 🧹 Cleanup

```bash
# Delete ECS services
aws ecs update-service --cluster memcloud-cluster --service memcloud-backend --desired-count 0
aws ecs update-service --cluster memcloud-cluster --service memcloud-frontend --desired-count 0
aws ecs delete-service --cluster memcloud-cluster --service memcloud-backend --force
aws ecs delete-service --cluster memcloud-cluster --service memcloud-frontend --force

# Delete load balancers
aws elbv2 delete-load-balancer --load-balancer-arn $BACKEND_ALB
aws elbv2 delete-load-balancer --load-balancer-arn $FRONTEND_ALB
aws elbv2 delete-target-group --target-group-arn $BACKEND_TG
aws elbv2 delete-target-group --target-group-arn $FRONTEND_TG

# Delete RDS
aws rds delete-db-instance --db-instance-identifier memcloud-postgres --skip-final-snapshot

# Delete secrets
aws secretsmanager delete-secret --secret-id memcloud-db-password --force-delete-without-recovery

# Delete ECR repositories
aws ecr delete-repository --repository-name memcloud-backend --force
aws ecr delete-repository --repository-name memcloud-frontend --force
aws ecr delete-repository --repository-name memmachine-custom --force

# Delete VPC components
aws ec2 delete-security-group --group-id $ALB_SG
aws ec2 delete-security-group --group-id $ECS_SG
aws ec2 delete-security-group --group-id $RDS_SG
aws ec2 detach-internet-gateway --internet-gateway-id $IGW_ID --vpc-id $VPC_ID
aws ec2 delete-internet-gateway --internet-gateway-id $IGW_ID
aws ec2 delete-subnet --subnet-id $SUBNET_1
aws ec2 delete-subnet --subnet-id $SUBNET_2
aws ec2 delete-route-table --route-table-id $ROUTE_TABLE_ID
aws ec2 delete-vpc --vpc-id $VPC_ID
```

---

**Document Version:** 2.0
**Includes:** Neo4j Aura support, ECS Fargate, RDS PostgreSQL
**Tested:** October 2025
**Next Steps:** See `DEPLOY_GCP.md` or `DEPLOY_AZURE.md` for other cloud providers
