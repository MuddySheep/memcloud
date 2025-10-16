# MemMachine Cloud Deployment Guide
## Comprehensive Technical Documentation for Cloud Migration

**Date:** October 14, 2025
**Status:** Production-Ready ✅
**Tested On:** Google Cloud Platform (GCP)
**Applicable To:** AWS, Azure, and other cloud providers

---

## Table of Contents

1. [Critical Discovery: The psycopg2 Problem](#critical-discovery-the-psycopg2-problem)
2. [MemMachine Architecture Requirements](#memmachine-architecture-requirements)
3. [Prerequisites & Cloud Setup](#prerequisites--cloud-setup)
4. [GCP-Specific Setup (Complete Guide)](#gcp-specific-setup-complete-guide)
5. [Building the Custom Docker Image](#building-the-custom-docker-image)
6. [Deployment Process](#deployment-process)
7. [Troubleshooting & Lessons Learned](#troubleshooting--lessons-learned)
8. [AWS/Azure Migration Notes](#awsazure-migration-notes)

---

## Critical Discovery: The psycopg2 Problem

### The Issue
MemMachine's official Docker image (`memmachine/memmachine:latest`) does NOT include PostgreSQL support out of the box. When you try to use Cloud SQL PostgreSQL with MemMachine, you get:

```
ModuleNotFoundError: No module named 'psycopg2'
```

### Why Standard Fixes Don't Work

**❌ WRONG: Runtime Installation**
```bash
# In startup script - DOES NOT WORK
pip install psycopg2-binary
```
**Problem:** Container starts, MemMachine tries to connect to PostgreSQL BEFORE the installation completes.

**❌ WRONG: Install to System Python**
```dockerfile
RUN pip3 install psycopg2-binary
# or
RUN /usr/local/bin/python3 -m pip install psycopg2-binary
```
**Problem:** MemMachine uses `/app/.venv/bin/python` which is a symlink-based "virtual environment" that doesn't see system packages.

**✅ CORRECT: Install to .venv site-packages**
```dockerfile
RUN /usr/local/bin/python3 -m pip install --no-cache-dir \
    --target=/app/.venv/lib/python3.12/site-packages \
    psycopg2-binary
```
**Why it works:** This installs directly into the directory where the venv Python looks for packages.

### The Virtual Environment Discovery

MemMachine's `.venv` is NOT a standard Python virtual environment. It's a collection of symlinks:

```bash
/app/.venv/bin/python -> /usr/local/bin/python3
/app/.venv/bin/python3 -> python
/app/.venv/bin/python3.12 -> python
```

However, the Python path includes `/app/.venv/lib/python3.12/site-packages`:
```python
sys.path = [
    '',
    '/usr/local/lib/python312.zip',
    '/usr/local/lib/python3.12',
    '/usr/local/lib/python3.12/lib-dynload',
    '/app/.venv/lib/python3.12/site-packages'  # ← This is where psycopg2 must go!
]
```

---

## MemMachine Architecture Requirements

### Core Components

MemMachine requires THREE separate services:

#### 1. **PostgreSQL Database**
- **Purpose:** Session storage, conversation history
- **Extension Required:** `pgvector` (for embeddings)
- **Minimum Specs:** 1 vCPU, 3.75 GB RAM
- **Network:** Must be accessible from MemMachine service
- **Authentication:** Username/password (store in secrets manager)

#### 2. **Neo4j Graph Database**
- **Purpose:** Episodic memory, knowledge graph, entity relationships
- **Version:** 5.23-community (or later)
- **Minimum Specs:** 1 vCPU, 2 GB RAM
- **Ports:**
  - 7687 (Bolt protocol - REQUIRED)
  - 7474 (HTTP - optional, for browser UI)
- **Network:** Must be accessible from MemMachine service
- **Authentication:** neo4j user + password (store in secrets manager)

#### 3. **MemMachine API**
- **Base Image:** `memmachine/memmachine:latest`
- **Custom Image Required:** YES (to add PostgreSQL support)
- **Minimum Specs:** 2 vCPU, 2 GB RAM
- **Port:** 8080 (default)
- **Startup Time:** 30-60 seconds
- **Health Check:** `/health` endpoint

### Environment Variables Required

MemMachine requires these environment variables:

```bash
# PostgreSQL Configuration
POSTGRES_HOST=<postgres-ip-or-hostname>
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=<secret>
POSTGRES_DB=postgres

# Neo4j Configuration
NEO4J_HOST=<neo4j-hostname>
NEO4J_PORT=7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=<secret>

# OpenAI Configuration
OPENAI_API_KEY=<user-api-key>

# MemMachine Configuration
MEMORY_CONFIG=/app/configuration.yml  # Path to generated config
PORT=8080  # Server port (set by cloud provider)
HOST=0.0.0.0  # Listen on all interfaces
```

### Configuration File Generation

MemMachine requires a `configuration.yml` file. This should be **generated at runtime** from environment variables (see startup script below).

---

## Prerequisites & Cloud Setup

### Required Tools & Access

1. **Cloud Provider Account** (GCP, AWS, or Azure)
2. **Command-Line Tools**:
   - `gcloud` (GCP) / `aws` (AWS) / `az` (Azure)
   - `docker` (for building custom images)
   - `kubectl` (optional, for Kubernetes)
3. **Permissions**:
   - Create/manage compute instances
   - Create/manage databases
   - Create/manage container registries
   - Create/manage secrets
   - Create/manage IAM roles/service accounts

### Cost Estimate (Monthly)

Based on GCP pricing (similar for AWS/Azure):

| Component | Specs | Cost |
|-----------|-------|------|
| PostgreSQL | db-custom-1-3840 (1 vCPU, 3.75 GB) | ~$50-70 |
| Neo4j (Cloud Run) | 1 vCPU, 2 GB RAM, always-on | ~$40-60 |
| MemMachine (Cloud Run) | 2 vCPU, 2 GB RAM, auto-scale | ~$30-50 |
| **Total per instance** | | **~$120-180/month** |

*Note: Costs decrease with scale-to-zero for Neo4j/MemMachine*

---

## GCP-Specific Setup (Complete Guide)

### Step 1: Create GCP Project

```bash
# Set your project ID
export PROJECT_ID="your-project-id"
export REGION="us-central1"

# Create project (if new)
gcloud projects create $PROJECT_ID --name="MemMachine Cloud"

# Set as default project
gcloud config set project $PROJECT_ID
```

### Step 2: Enable Required APIs

```bash
# Enable all necessary APIs
gcloud services enable \
  run.googleapis.com \
  sqladmin.googleapis.com \
  secretmanager.googleapis.com \
  cloudbuild.googleapis.com \
  containerregistry.googleapis.com \
  compute.googleapis.com \
  iam.googleapis.com
```

### Step 3: Create Service Account

```bash
# Create service account for deployments
gcloud iam service-accounts create memmachine-deployer \
  --display-name="MemMachine Deployment Service Account"

export SA_EMAIL="memmachine-deployer@${PROJECT_ID}.iam.gserviceaccount.com"

# Grant necessary roles
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/cloudsql.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/secretmanager.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/iam.serviceAccountUser"

# Create and download service account key
gcloud iam service-accounts keys create ~/memmachine-sa-key.json \
  --iam-account=$SA_EMAIL
```

### Step 4: Configure Secret Manager

```bash
# Secret Manager is now enabled - no additional setup needed
# Secrets will be created during deployment

# Optional: Create a test secret to verify
echo "test-value" | gcloud secrets create test-secret --data-file=-
gcloud secrets delete test-secret --quiet  # Clean up
```

### Step 5: Set Up Container Registry

```bash
# Configure Docker to authenticate with GCR
gcloud auth configure-docker

# Create a repository (optional, auto-created on first push)
# GCR is automatically available at gcr.io/$PROJECT_ID
```

### Step 6: Configure IAM for Cloud Run

```bash
# Allow Cloud Run services to access secrets
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${PROJECT_ID}-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

# Allow Cloud Run services to pull images
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${PROJECT_ID}-compute@developer.gserviceaccount.com" \
  --role="roles/storage.objectViewer"
```

### Step 7: Network Configuration (Optional)

For production deployments, consider:

```bash
# Create VPC network
gcloud compute networks create memmachine-vpc \
  --subnet-mode=auto

# Create firewall rules
gcloud compute firewall-rules create allow-postgres \
  --network=memmachine-vpc \
  --allow=tcp:5432 \
  --source-ranges=0.0.0.0/0

gcloud compute firewall-rules create allow-neo4j \
  --network=memmachine-vpc \
  --allow=tcp:7687 \
  --source-ranges=0.0.0.0/0
```

---

## Building the Custom Docker Image

### Step 1: Create Docker Build Directory

```bash
mkdir -p memmachine-docker
cd memmachine-docker
```

### Step 2: Create Dockerfile

Create `Dockerfile`:

```dockerfile
# MemMachine Custom Image with PostgreSQL Support
# CRITICAL: Install psycopg2 to .venv site-packages for venv Python to find it

FROM memmachine/memmachine:latest

USER root

# Install PostgreSQL client libraries and build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# CRITICAL STEP: Install psycopg2-binary to .venv site-packages
# This is where the venv Python (used by MemMachine) looks for packages
RUN /usr/local/bin/python3 -m pip install --no-cache-dir \
    --target=/app/.venv/lib/python3.12/site-packages \
    psycopg2-binary

# Verify installation with the venv Python (the one that will actually run)
RUN /app/.venv/bin/python -c "import psycopg2; print('✅ psycopg2 installed and accessible:', psycopg2.__version__)"

# Copy startup script
COPY startup.sh /app/startup.sh
RUN chmod +x /app/startup.sh

# Use startup script as entrypoint
ENTRYPOINT ["/app/startup.sh"]
```

### Step 3: Create Startup Script

Create `startup.sh`:

```bash
#!/bin/bash
set -e

echo "Starting MemMachine Cloud Run instance..."

# Verify psycopg2 installation
echo "Verifying psycopg2 installation..."
if /app/.venv/bin/python -c "import psycopg2; print('psycopg2 version:', psycopg2.__version__)" 2>&1; then
    echo "✅ psycopg2 is available"
else
    echo "❌ ERROR: psycopg2 not found - this should have been installed during Docker build"
    exit 1
fi

# Generate MemMachine configuration from environment variables
echo "Generating configuration from environment..."
cat > /app/configuration.yml <<EOF
# MemMachine Configuration - Generated at runtime
long_term_memory:
  derivative_deriver: sentence
  embedder: openai_embedder
  reranker: hybrid_reranker
  vector_graph_store: neo4j_storage

sessiondb:
  uri: postgresql://postgres:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:5432/postgres

model:
  openai_model:
    model_name: "gpt-4o-mini"
    api_key: ${OPENAI_API_KEY}

storage:
  neo4j_storage:
    vendor_name: neo4j
    host: ${NEO4J_HOST}
    port: 7687
    user: neo4j
    password: ${NEO4J_PASSWORD}

sessionmemory:
  model_name: openai_model
  message_capacity: 500
  max_message_length: 16000
  max_token_num: 8000

embedder:
  openai_embedder:
    model_name: "text-embedding-3-small"
    api_key: ${OPENAI_API_KEY}

reranker:
  hybrid_reranker:
    type: "rrf-hybrid"
    reranker_ids:
      - identity_ranker
      - bm25_ranker
  identity_ranker:
    type: "identity"
  bm25_ranker:
    type: "bm25"
EOF

echo "Configuration file created at /app/configuration.yml"

# Export required environment variables for MemMachine
export MEMORY_CONFIG=/app/configuration.yml
export NEO4J_USERNAME=neo4j
export NEO4J_URI=bolt://${NEO4J_HOST}:7687

# Initialize database schema (required on first run)
echo "Syncing profile schema..."
memmachine-sync-profile-schema || echo "Schema sync completed or already exists"

# Start MemMachine server
echo "Starting MemMachine server on port ${PORT:-8080}..."
exec memmachine-server --host 0.0.0.0 --port ${PORT:-8080}
```

### Step 4: Build and Push Image

```bash
# Build image
docker build -t gcr.io/$PROJECT_ID/memmachine-custom:v1 .

# Test locally (optional)
docker run -p 8080:8080 \
  -e POSTGRES_HOST=host.docker.internal \
  -e POSTGRES_PASSWORD=test \
  -e NEO4J_HOST=host.docker.internal \
  -e NEO4J_PASSWORD=test \
  -e OPENAI_API_KEY=sk-test \
  gcr.io/$PROJECT_ID/memmachine-custom:v1

# Push to Google Container Registry
docker push gcr.io/$PROJECT_ID/memmachine-custom:v1

# Get the image digest (for immutable deployments)
gcloud container images describe gcr.io/$PROJECT_ID/memmachine-custom:v1 \
  --format='get(image_summary.digest)'
```

**IMPORTANT:** Use the **digest** (SHA256 hash) in production deployments, not tags. This ensures you deploy the exact image version.

Example:
```python
docker_image = "gcr.io/my-project/memmachine-custom@sha256:abc123..."
```

---

## Deployment Process

### Step 1: Create Secrets

```bash
export INSTANCE_ID="mem-$(uuidgen | cut -d'-' -f1)"

# Store OpenAI API key
echo "sk-your-actual-key" | gcloud secrets create openai-key-${INSTANCE_ID} \
  --data-file=- \
  --replication-policy=automatic

# Generate and store PostgreSQL password
export POSTGRES_PASSWORD=$(openssl rand -base64 32)
echo $POSTGRES_PASSWORD | gcloud secrets create postgres-pass-${INSTANCE_ID} \
  --data-file=- \
  --replication-policy=automatic

# Generate and store Neo4j password
export NEO4J_PASSWORD=$(openssl rand -base64 32)
echo $NEO4J_PASSWORD | gcloud secrets create neo4j-pass-${INSTANCE_ID} \
  --data-file=- \
  --replication-policy=automatic
```

### Step 2: Deploy PostgreSQL (Cloud SQL)

```bash
# Create Cloud SQL instance (takes 3-5 minutes)
gcloud sql instances create memmachine-${INSTANCE_ID} \
  --database-version=POSTGRES_15 \
  --tier=db-custom-1-3840 \
  --region=$REGION \
  --root-password=$POSTGRES_PASSWORD \
  --network=default \
  --no-backup \
  --enable-bin-log=false

# Enable public IP (for Cloud Run to access)
gcloud sql instances patch memmachine-${INSTANCE_ID} \
  --authorized-networks=0.0.0.0/0

# Get the public IP
export POSTGRES_IP=$(gcloud sql instances describe memmachine-${INSTANCE_ID} \
  --format='get(ipAddresses[0].ipAddress)')

echo "PostgreSQL IP: $POSTGRES_IP"
```

**Production Note:** For better security, use Private IP with VPC peering instead of public IP.

### Step 3: Deploy Neo4j to Cloud Run

```bash
# Deploy Neo4j as a Cloud Run service
gcloud run deploy neo4j-${INSTANCE_ID} \
  --image=neo4j:5.23-community \
  --region=$REGION \
  --cpu=1 \
  --memory=2Gi \
  --min-instances=1 \
  --max-instances=1 \
  --port=7687 \
  --set-env-vars="NEO4J_AUTH=neo4j/${NEO4J_PASSWORD}" \
  --set-env-vars="NEO4J_server_memory_heap_max__size=1G" \
  --set-env-vars="NEO4J_server_memory_heap_initial__size=512m" \
  --set-env-vars="NEO4J_server_default__listen__address=0.0.0.0" \
  --set-env-vars="NEO4J_server_bolt_listen__address=0.0.0.0:7687" \
  --allow-unauthenticated

# Get Neo4j URL (remove https:// prefix for bolt connection)
export NEO4J_URL=$(gcloud run services describe neo4j-${INSTANCE_ID} \
  --region=$REGION \
  --format='get(status.url)')
export NEO4J_HOST=$(echo $NEO4J_URL | sed 's|https://||')

echo "Neo4j Bolt URL: $NEO4J_HOST:7687"
```

### Step 4: Deploy MemMachine to Cloud Run

```bash
# Deploy MemMachine with secrets mounted as environment variables
gcloud run deploy memmachine-${INSTANCE_ID} \
  --image=gcr.io/$PROJECT_ID/memmachine-custom@sha256:YOUR-DIGEST-HERE \
  --region=$REGION \
  --cpu=2 \
  --memory=2Gi \
  --min-instances=0 \
  --max-instances=10 \
  --port=8080 \
  --timeout=600s \
  --set-env-vars="POSTGRES_HOST=$POSTGRES_IP" \
  --set-env-vars="POSTGRES_PORT=5432" \
  --set-env-vars="POSTGRES_USER=postgres" \
  --set-env-vars="POSTGRES_DB=postgres" \
  --set-env-vars="NEO4J_HOST=$NEO4J_HOST" \
  --set-env-vars="NEO4J_PORT=7687" \
  --set-env-vars="NEO4J_USER=neo4j" \
  --set-secrets="POSTGRES_PASSWORD=postgres-pass-${INSTANCE_ID}:latest" \
  --set-secrets="NEO4J_PASSWORD=neo4j-pass-${INSTANCE_ID}:latest" \
  --set-secrets="OPENAI_API_KEY=openai-key-${INSTANCE_ID}:latest" \
  --allow-unauthenticated

# Get MemMachine URL
export MEMMACHINE_URL=$(gcloud run services describe memmachine-${INSTANCE_ID} \
  --region=$REGION \
  --format='get(status.url)')

echo "MemMachine API: $MEMMACHINE_URL"
```

### Step 5: Validate Deployment

```bash
# Check health endpoint
curl $MEMMACHINE_URL/health

# Expected response:
# {"status":"healthy"}

# Check logs for errors
gcloud run services logs read memmachine-${INSTANCE_ID} \
  --region=$REGION \
  --limit=50
```

---

## Troubleshooting & Lessons Learned

### Issue 1: psycopg2 Not Found

**Symptoms:**
```
ModuleNotFoundError: No module named 'psycopg2'
```

**Solution:**
Install psycopg2 to `.venv/lib/python3.12/site-packages` during Docker build (see Dockerfile above).

**Why other solutions don't work:**
- Runtime installation: Too late, MemMachine already tried to import
- System Python installation: MemMachine uses venv Python which doesn't see system packages
- Installing to wrong directory: Must be exactly where venv Python's sys.path looks

### Issue 2: PostgreSQL Connection Timeout

**Symptoms:**
```
could not connect to server: Connection timed out
```

**Solutions:**
1. Enable public IP on Cloud SQL instance
2. Add authorized network: `0.0.0.0/0` (allow all)
3. Verify POSTGRES_HOST is the public IP, not connection name
4. For production: Use Private IP with VPC peering

### Issue 3: Neo4j Connection Failed

**Symptoms:**
```
Failed to establish connection to Neo4j
```

**Solutions:**
1. Ensure Neo4j is set to always-on (`--min-instances=1`)
2. Use the hostname WITHOUT `https://` prefix
3. Port must be 7687 (Bolt protocol)
4. Verify NEO4J_AUTH environment variable format: `neo4j/password`

### Issue 4: Startup Probe Timeout

**Symptoms:**
```
The revision 'memmachine-xxx-001' is not ready and cannot serve traffic
```

**Solutions:**
1. Increase startup probe `failureThreshold` to 30 (allows 5 minutes)
2. Increase `initial_delay_seconds` to 30
3. Add more memory if OOMKilled
4. Check logs for actual errors

### Issue 5: Secret Access Denied

**Symptoms:**
```
Error: failed to access secret 'projects/xxx/secrets/openai-key'
```

**Solutions:**
1. Grant `roles/secretmanager.secretAccessor` to compute service account
2. Verify secret exists: `gcloud secrets list`
3. Verify secret version: `gcloud secrets versions list SECRET_NAME`
4. Check IAM permissions: `gcloud secrets get-iam-policy SECRET_NAME`

---

## AWS/Azure Migration Notes

### AWS Equivalent Services

| GCP Service | AWS Equivalent | Notes |
|-------------|----------------|-------|
| Cloud Run | ECS Fargate / App Runner | Use Fargate for containerized workloads |
| Cloud SQL | RDS PostgreSQL | Enable public access or use VPC |
| Secret Manager | AWS Secrets Manager | Similar API, slightly different syntax |
| Container Registry | ECR (Elastic Container Registry) | Must authenticate Docker |
| IAM Roles | IAM Roles | Attach to ECS task definition |

### AWS Deployment Commands

```bash
# Build and push to ECR
aws ecr create-repository --repository-name memmachine-custom
aws ecr get-login-password | docker login --username AWS --password-stdin $AWS_ACCOUNT.dkr.ecr.$REGION.amazonaws.com
docker build -t $AWS_ACCOUNT.dkr.ecr.$REGION.amazonaws.com/memmachine-custom:v1 .
docker push $AWS_ACCOUNT.dkr.ecr.$REGION.amazonaws.com/memmachine-custom:v1

# Create RDS PostgreSQL
aws rds create-db-instance \
  --db-instance-identifier memmachine-postgres \
  --db-instance-class db.t3.medium \
  --engine postgres \
  --master-username postgres \
  --master-user-password $POSTGRES_PASSWORD \
  --allocated-storage 20 \
  --publicly-accessible

# Create ECS task definition (use similar env vars as GCP)
aws ecs register-task-definition --cli-input-json file://task-definition.json

# Deploy to Fargate
aws ecs create-service \
  --cluster memmachine \
  --service-name memmachine-api \
  --task-definition memmachine:1 \
  --desired-count 1 \
  --launch-type FARGATE
```

### Azure Equivalent Services

| GCP Service | Azure Equivalent | Notes |
|-------------|------------------|-------|
| Cloud Run | Azure Container Instances / App Service | Use ACI for serverless |
| Cloud SQL | Azure Database for PostgreSQL | Flexible Server recommended |
| Secret Manager | Azure Key Vault | Different API, similar concept |
| Container Registry | Azure Container Registry (ACR) | Must authenticate |
| IAM Roles | Managed Identities | Assign to container instances |

### Azure Deployment Commands

```bash
# Create resource group
az group create --name memmachine-rg --location eastus

# Create ACR and push image
az acr create --resource-group memmachine-rg --name memmachineacr --sku Basic
az acr login --name memmachineacr
docker build -t memmachineacr.azurecr.io/memmachine-custom:v1 .
docker push memmachineacr.azurecr.io/memmachine-custom:v1

# Create PostgreSQL
az postgres flexible-server create \
  --name memmachine-postgres \
  --resource-group memmachine-rg \
  --admin-user postgres \
  --admin-password $POSTGRES_PASSWORD \
  --sku-name Standard_B1ms \
  --public-access 0.0.0.0-255.255.255.255

# Deploy to Azure Container Instances
az container create \
  --resource-group memmachine-rg \
  --name memmachine-api \
  --image memmachineacr.azurecr.io/memmachine-custom:v1 \
  --cpu 2 \
  --memory 2 \
  --ports 8080 \
  --environment-variables POSTGRES_HOST=$POSTGRES_IP \
  --secure-environment-variables POSTGRES_PASSWORD=$POSTGRES_PASSWORD
```

---

## Key Takeaways for Any Cloud Provider

### Universal Requirements

1. **Custom Docker Image Required**
   - Base: `memmachine/memmachine:latest`
   - Add: `psycopg2-binary` to `.venv/lib/python3.12/site-packages`
   - Verify: Run import test during build

2. **Three Services Always Needed**
   - PostgreSQL (with pgvector extension)
   - Neo4j (Bolt protocol on port 7687)
   - MemMachine (custom image)

3. **Secrets Management**
   - Never hardcode credentials
   - Use cloud provider's secret manager
   - Mount as environment variables

4. **Network Configuration**
   - PostgreSQL must be accessible (public IP or VPC)
   - Neo4j must be accessible (HTTP/HTTPS endpoint)
   - MemMachine needs egress to both databases

5. **Health Checks & Startup Time**
   - Allow 30-60 seconds for startup
   - Use `/health` endpoint
   - Set appropriate timeout thresholds

### Build-Time vs Runtime Decisions

**Build Time (Dockerfile):**
- Install system dependencies (libpq-dev, gcc)
- Install Python packages (psycopg2-binary)
- Copy static files (startup script)

**Runtime (Startup Script):**
- Generate configuration from environment variables
- Verify dependencies are installed
- Initialize database schemas
- Start the MemMachine server

**Never At Runtime:**
- Installing Python packages (too slow, can fail)
- Building code (containers should be immutable)
- Downloading large dependencies

---

## Production Checklist

Before going to production:

- [ ] Use SHA256 digests for Docker images (not tags)
- [ ] Enable VPC/Private networking (no public IPs)
- [ ] Set up automated backups for PostgreSQL
- [ ] Enable Cloud Armor / WAF for DDoS protection
- [ ] Set up monitoring and alerting (Stackdriver/CloudWatch/Monitor)
- [ ] Configure auto-scaling based on CPU/memory
- [ ] Set up log aggregation and analysis
- [ ] Implement secret rotation policies
- [ ] Set up staging environment for testing
- [ ] Document incident response procedures
- [ ] Enable audit logging for compliance
- [ ] Set up cost alerts and budgets

---

## Conclusion

Deploying MemMachine to the cloud requires understanding its unique architecture (symlink-based venv) and properly building a custom Docker image with PostgreSQL support. The key insight is installing `psycopg2-binary` to the exact directory where the venv Python looks for packages.

This guide is proven to work on GCP and the principles apply to AWS, Azure, and other cloud providers. The main differences are in the specific commands and service names, but the architecture and requirements remain the same.

**Critical Success Factors:**
1. Build psycopg2 into the Docker image (not runtime)
2. Install to `.venv/lib/python3.12/site-packages` specifically
3. Verify during build with venv Python
4. Generate config at runtime from environment variables
5. Allow sufficient startup time (30-60 seconds)

With this guide, you can reproduce a working MemMachine deployment on any cloud provider without running into the errors we encountered.

---

**Document Version:** 1.0
**Last Updated:** October 14, 2025
**Tested Configuration:** GCP Cloud Run + Cloud SQL + Neo4j
**Status:** Production-Ready ✅
