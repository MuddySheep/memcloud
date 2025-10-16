# MemCloud Deployment Guide - Google Cloud Platform (GCP)
## Production-Ready Deployment for MemMachine on GCP Cloud Run

**Status:** ✅ Production-Ready
**Last Updated:** October 2025
**Deployment Time:** ~20 minutes
**Monthly Cost:** $20-40 (with auto-scaling)

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
                  │ HTTPS
                  ▼
┌─────────────────────────────────────────────────────────────┐
│              Frontend (Next.js on Cloud Run)                 │
│              - Dashboard UI                                  │
│              - Instance Management                           │
└─────────────────┬───────────────────────────────────────────┘
                  │ HTTPS API
                  ▼
┌─────────────────────────────────────────────────────────────┐
│            Backend API (FastAPI on Cloud Run)                │
│            - Deployment orchestration                        │
│            - Instance tracking (PostgreSQL)                  │
└─────┬─────────────────────────────────────┬─────────────────┘
      │                                     │
      │ Creates/Manages                     │ Stores metadata
      ▼                                     ▼
┌─────────────────────┐          ┌──────────────────────────┐
│ MemMachine Instance │          │   Cloud SQL PostgreSQL   │
│  (Cloud Run)        │          │   - Instance metadata    │
│  + Neo4j Aura       │          │   - User data            │
│    (External SaaS)  │          │   - API keys             │
└─────────────────────┘          └──────────────────────────┘
```

**Key Components:**
- **Frontend:** Next.js dashboard for managing deployments
- **Backend API:** FastAPI service that orchestrates MemMachine deployments
- **Cloud SQL:** PostgreSQL database for tracking instances
- **MemMachine Instances:** User-deployed AI memory services (Cloud Run)
- **Neo4j Aura:** Managed graph database (external SaaS, no GCP hosting needed)

---

## ✅ Prerequisites

### 1. Google Cloud Account
- Active GCP account with billing enabled
- Owner or Editor role on project
- **Free tier:** $300 credits for new accounts (90 days)

### 2. Local Tools
```bash
# Google Cloud SDK
gcloud --version
# Expected: Google Cloud SDK 450.0.0+

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
| **Cloud Run (Backend)** | 1 vCPU, 2GB RAM, scale-to-zero | $5-10 |
| **Cloud Run (Frontend)** | 1 vCPU, 512MB RAM, scale-to-zero | $2-5 |
| **Cloud SQL (PostgreSQL)** | db-f1-micro, 1 vCPU, 614MB RAM | $7-15 |
| **Cloud Storage (Images)** | < 5GB | $0.20 |
| **Neo4j Aura (per instance)** | Free tier / Paid | $0-65 |
| **MemMachine Instances** | Per user deployment | $15-30 each |
| **Total (Platform Only)** | | **$15-30/month** |

**Notes:**
- Costs scale with usage (Cloud Run is pay-per-request)
- Neo4j Aura costs are per user instance, not platform cost
- Free tier covers development/testing for ~90 days

---

## 🚀 Initial Setup

### Step 1: Create GCP Project

```bash
# Set variables
export PROJECT_ID="memcloud-prod"  # Change to your unique project ID
export REGION="us-central1"
export ZONE="us-central1-a"

# Authenticate with GCP
gcloud auth login

# Create new project
gcloud projects create $PROJECT_ID \
  --name="MemCloud Production" \
  --set-as-default

# Set default project
gcloud config set project $PROJECT_ID
gcloud config set compute/region $REGION
gcloud config set compute/zone $ZONE
gcloud config set run/region $REGION

# Verify configuration
gcloud config list
```

**✅ Verification:**
```bash
gcloud projects describe $PROJECT_ID
# Should show: lifecycleState: ACTIVE
```

### Step 2: Enable Billing

```bash
# List billing accounts
gcloud billing accounts list

# Link billing account to project
export BILLING_ACCOUNT="XXXXXX-XXXXXX-XXXXXX"  # Use your billing account ID
gcloud billing projects link $PROJECT_ID \
  --billing-account=$BILLING_ACCOUNT

# Verify billing is enabled
gcloud billing projects describe $PROJECT_ID
```

**✅ Verification:**
```bash
gcloud billing projects describe $PROJECT_ID | grep billingEnabled
# Should show: billingEnabled: true
```

### Step 3: Enable Required APIs

```bash
# Enable all necessary APIs (takes ~2 minutes)
gcloud services enable \
  run.googleapis.com \
  sqladmin.googleapis.com \
  secretmanager.googleapis.com \
  cloudbuild.googleapis.com \
  containerregistry.googleapis.com \
  compute.googleapis.com \
  iam.googleapis.com \
  logging.googleapis.com \
  monitoring.googleapis.com

# Wait for API propagation
echo "⏳ Waiting for APIs to propagate (60 seconds)..."
sleep 60
```

**✅ Verification:**
```bash
gcloud services list --enabled | grep -E "run|sqladmin|secretmanager|cloudbuild"
# Should show all 4 APIs enabled
```

### Step 4: Set Up IAM Permissions

```bash
# Get project number (needed for default service account)
export PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='get(projectNumber)')
export DEFAULT_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

echo "Project Number: $PROJECT_NUMBER"
echo "Default Service Account: $DEFAULT_SA"

# Grant Cloud Run runtime permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${DEFAULT_SA}" \
  --role="roles/secretmanager.secretAccessor"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${DEFAULT_SA}" \
  --role="roles/cloudsql.client"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${DEFAULT_SA}" \
  --role="roles/run.admin"

echo "✅ IAM permissions configured"
```

**✅ Verification:**
```bash
gcloud projects get-iam-policy $PROJECT_ID \
  --flatten="bindings[].members" \
  --filter="bindings.members:${DEFAULT_SA}" \
  --format="table(bindings.role)"
# Should show at least 3 roles
```

### Step 5: Configure Docker for GCR

```bash
# Configure Docker to use gcloud for authentication
gcloud auth configure-docker

# Test Docker authentication
docker pull gcr.io/google-samples/hello-app:1.0
```

**✅ Verification:**
```bash
docker images | grep hello-app
# Should show the pulled image
```

---

## 🐳 Build Custom Docker Image

### Why We Need a Custom Image

The official `memmachine/memmachine:latest` image lacks PostgreSQL support. We must build a custom image that installs `psycopg2-binary` to the exact location where MemMachine's virtual environment expects it.

### Step 1: Create Build Directory

```bash
cd ~/
mkdir -p memcloud-docker/backend
cd memcloud-docker/backend
```

### Step 2: Create Dockerfile

Create `Dockerfile`:

```dockerfile
# MemMachine Custom Image with PostgreSQL Support
# CRITICAL: Install psycopg2 to .venv site-packages for MemMachine's Python to find it

FROM memmachine/memmachine:latest

USER root

# Install PostgreSQL client libraries and build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# CRITICAL: Install psycopg2-binary to the EXACT location where venv Python looks
# MemMachine uses /app/.venv/bin/python which is a symlink to /usr/local/bin/python3
# But Python's sys.path includes /app/.venv/lib/python3.12/site-packages
RUN /usr/local/bin/python3 -m pip install --no-cache-dir \
    --target=/app/.venv/lib/python3.12/site-packages \
    psycopg2-binary

# Verify installation with the venv Python (the one MemMachine actually uses)
RUN /app/.venv/bin/python -c "import psycopg2; print('✅ psycopg2 installed:', psycopg2.__version__)"

# Copy startup script
COPY startup.sh /app/startup.sh
RUN chmod +x /app/startup.sh

USER appuser
WORKDIR /app

# Use startup script as entrypoint
ENTRYPOINT ["/app/startup.sh"]
```

### Step 3: Create Startup Script

Create `startup.sh`:

```bash
#!/bin/bash
set -e

echo "🚀 Starting MemMachine Cloud Run instance..."

# Verify psycopg2 installation
echo "🔍 Verifying psycopg2 installation..."
if /app/.venv/bin/python -c "import psycopg2; print('psycopg2 version:', psycopg2.__version__)" 2>&1; then
    echo "✅ psycopg2 is available"
else
    echo "❌ ERROR: psycopg2 not found - this should have been installed during Docker build"
    exit 1
fi

# Generate MemMachine configuration from environment variables
echo "📝 Generating configuration from environment..."
cat > /app/configuration.yml <<EOF
# MemMachine Configuration - Generated at runtime
long_term_memory:
  derivative_deriver: sentence
  embedder: openai_embedder
  reranker: hybrid_reranker
  vector_graph_store: neo4j_storage

sessiondb:
  uri: postgresql://postgres:\${POSTGRES_PASSWORD}@\${POSTGRES_HOST}:5432/postgres

model:
  openai_model:
    model_name: "gpt-4o-mini"
    api_key: \${OPENAI_API_KEY}

storage:
  neo4j_storage:
    vendor_name: neo4j
    host: \${NEO4J_HOST}
    port: 7687
    user: neo4j
    password: \${NEO4J_PASSWORD}

sessionmemory:
  model_name: openai_model
  message_capacity: 500
  max_message_length: 16000
  max_token_num: 8000

embedder:
  openai_embedder:
    model_name: "text-embedding-3-small"
    api_key: \${OPENAI_API_KEY}

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

echo "✅ Configuration file created"

# Export required environment variables for MemMachine
export MEMORY_CONFIG=/app/configuration.yml
export NEO4J_USERNAME=neo4j
export NEO4J_URI=bolt://\${NEO4J_HOST}:7687

# Initialize database schema (required on first run)
echo "🔧 Syncing profile schema..."
memmachine-sync-profile-schema || echo "⚠️  Schema sync completed or already exists"

# Start MemMachine server
echo "🎯 Starting MemMachine server on port \${PORT:-8080}..."
exec memmachine-server --host 0.0.0.0 --port \${PORT:-8080}
```

### Step 4: Build and Push Image

```bash
# Build the image
docker build -t gcr.io/$PROJECT_ID/memmachine-custom:latest .

# Test locally (optional but recommended)
docker run -p 8080:8080 \
  -e POSTGRES_HOST=localhost \
  -e POSTGRES_PASSWORD=test \
  -e NEO4J_HOST=localhost \
  -e NEO4J_PASSWORD=test \
  -e OPENAI_API_KEY=sk-test \
  gcr.io/$PROJECT_ID/memmachine-custom:latest &

# Wait a few seconds and test
sleep 5
curl http://localhost:8080/health || echo "Container started (health check may fail without real DB)"
docker stop $(docker ps -q --filter ancestor=gcr.io/$PROJECT_ID/memmachine-custom:latest)

# Push to Google Container Registry
docker push gcr.io/$PROJECT_ID/memmachine-custom:latest

# Get the image digest (for production deployments)
export MEMMACHINE_IMAGE=$(gcloud container images describe gcr.io/$PROJECT_ID/memmachine-custom:latest --format='get(image_summary.fully_qualified_digest)')
echo "✅ Image pushed: $MEMMACHINE_IMAGE"
```

**✅ Verification:**
```bash
gcloud container images list --repository=gcr.io/$PROJECT_ID
# Should show memmachine-custom

gcloud container images describe $MEMMACHINE_IMAGE
# Should show details of the image
```

---

## 🔧 Deploy Backend Services

### Step 1: Deploy Cloud SQL PostgreSQL

```bash
# Create Cloud SQL instance (takes 3-5 minutes)
echo "⏳ Creating Cloud SQL instance (this takes 3-5 minutes)..."

gcloud sql instances create memcloud-postgres \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=$REGION \
  --root-password=$(openssl rand -base64 32) \
  --enable-bin-log=false

# Enable public IP access (required for Cloud Run to connect)
gcloud sql instances patch memcloud-postgres \
  --authorized-networks=0.0.0.0/0 \
  --quiet

# Get the public IP
export POSTGRES_IP=$(gcloud sql instances describe memcloud-postgres \
  --format='get(ipAddresses[0].ipAddress)')

echo "✅ PostgreSQL deployed at: $POSTGRES_IP"

# Get the root password
export POSTGRES_PASSWORD=$(gcloud sql users list --instance=memcloud-postgres \
  --format='value(name)' | xargs -I {} gcloud sql users describe postgres --instance=memcloud-postgres)

# Create database
gcloud sql databases create memcloud_prod --instance=memcloud-postgres
```

**✅ Verification:**
```bash
gcloud sql instances describe memcloud-postgres --format='get(state)'
# Should show: RUNNABLE
```

### Step 2: Create Secrets

```bash
# Store database password in Secret Manager
gcloud sql users list --instance=memcloud-postgres
# Note the postgres password from output

echo -n "YOUR_POSTGRES_PASSWORD" | gcloud secrets create memcloud-db-password \
  --data-file=- \
  --replication-policy=automatic

echo "✅ Database password stored in Secret Manager"
```

**✅ Verification:**
```bash
gcloud secrets describe memcloud-db-password
gcloud secrets versions access latest --secret=memcloud-db-password
# Should show your password
```

### Step 3: Deploy Backend API

Copy your backend code to `~/memcloud-backend/` or use the repo:

```bash
cd ~/
git clone <YOUR_MEMCLOUD_REPO> memcloud-backend
cd memcloud-backend/backend

# Or if you have the code locally, copy it
# cp -r /path/to/Memcloud/backend ~/memcloud-backend
```

Build and deploy:

```bash
# Build backend Docker image
gcloud builds submit --tag gcr.io/$PROJECT_ID/memcloud-backend:latest

# Deploy to Cloud Run
gcloud run deploy memcloud-backend \
  --image=gcr.io/$PROJECT_ID/memcloud-backend:latest \
  --region=$REGION \
  --platform=managed \
  --allow-unauthenticated \
  --min-instances=0 \
  --max-instances=10 \
  --cpu=1 \
  --memory=2Gi \
  --timeout=600s \
  --set-env-vars="DATABASE_URL=postgresql+asyncpg://postgres@$POSTGRES_IP:5432/memcloud_prod" \
  --set-env-vars="USE_CLOUD_SQL_CONNECTOR=false" \
  --set-env-vars="DB_HOST=$POSTGRES_IP" \
  --set-env-vars="DB_PORT=5432" \
  --set-env-vars="DB_NAME=memcloud_prod" \
  --set-env-vars="DB_USER=postgres" \
  --set-secrets="DB_PASSWORD=memcloud-db-password:latest" \
  --set-env-vars="GCP_PROJECT_ID=$PROJECT_ID" \
  --set-env-vars="GCP_REGION=$REGION"

# Get backend URL
export BACKEND_URL=$(gcloud run services describe memcloud-backend \
  --region=$REGION \
  --format='get(status.url)')

echo "✅ Backend deployed at: $BACKEND_URL"
```

**✅ Verification:**
```bash
curl $BACKEND_URL/
# Should return: {"service":"MemCloud API","version":"1.0.0","status":"healthy"}

curl $BACKEND_URL/health
# Should return 200 OK
```

### Step 4: Initialize Database

```bash
# Run database migrations
gcloud run jobs create memcloud-db-init \
  --image=gcr.io/$PROJECT_ID/memcloud-backend:latest \
  --region=$REGION \
  --set-env-vars="DATABASE_URL=postgresql+asyncpg://postgres@$POSTGRES_IP:5432/memcloud_prod" \
  --set-secrets="DB_PASSWORD=memcloud-db-password:latest" \
  --command="python,init_database_simple.py" \
  --max-retries=0

# Execute the job
gcloud run jobs execute memcloud-db-init --region=$REGION

# Check logs
gcloud run jobs logs read memcloud-db-init --region=$REGION
```

**✅ Verification:**
```bash
curl $BACKEND_URL/api/v1/instances
# Should return: [] (empty list, no instances yet)
```

---

## 🎨 Deploy Frontend

### Step 1: Build Frontend Image

```bash
cd ~/memcloud-backend/frontend

# Update environment variable for backend URL
cat > .env.production <<EOF
NEXT_PUBLIC_API_URL=$BACKEND_URL
EOF

# Build frontend Docker image
gcloud builds submit --tag gcr.io/$PROJECT_ID/memcloud-frontend:latest
```

### Step 2: Deploy Frontend to Cloud Run

```bash
gcloud run deploy memcloud-frontend \
  --image=gcr.io/$PROJECT_ID/memcloud-frontend:latest \
  --region=$REGION \
  --platform=managed \
  --allow-unauthenticated \
  --min-instances=0 \
  --max-instances=5 \
  --cpu=1 \
  --memory=512Mi \
  --timeout=60s \
  --set-env-vars="NEXT_PUBLIC_API_URL=$BACKEND_URL"

# Get frontend URL
export FRONTEND_URL=$(gcloud run services describe memcloud-frontend \
  --region=$REGION \
  --format='get(status.url)')

echo "✅ Frontend deployed at: $FRONTEND_URL"
```

**✅ Verification:**
```bash
curl -I $FRONTEND_URL
# Should return: HTTP/2 200
```

---

## ✅ Verification & Testing

### Complete System Test

```bash
# Test 1: Backend health
echo "Test 1: Backend health..."
curl $BACKEND_URL/health
echo ""

# Test 2: Backend API root
echo "Test 2: Backend API root..."
curl $BACKEND_URL/
echo ""

# Test 3: List instances (should be empty initially)
echo "Test 3: List instances..."
curl $BACKEND_URL/api/v1/instances
echo ""

# Test 4: Frontend access
echo "Test 4: Frontend access..."
curl -I $FRONTEND_URL
echo ""

# Test 5: Deploy a test MemMachine instance with Neo4j Aura
echo "Test 5: Deploy test instance..."
curl -X POST $BACKEND_URL/api/v1/deployment/deploy \
  -H "Content-Type: application/json" \
  -d '{
    "name": "test-instance",
    "openai_api_key": "sk-proj-YOUR_KEY_HERE",
    "user_id": "test-user",
    "neo4j_uri": "neo4j+s://YOUR_AURA_ID.databases.neo4j.io",
    "neo4j_user": "neo4j",
    "neo4j_password": "YOUR_AURA_PASSWORD"
  }'

echo ""
echo "✅ All tests complete!"
```

### Access the Dashboard

```bash
echo "🎉 MemCloud is now deployed!"
echo ""
echo "Frontend Dashboard: $FRONTEND_URL"
echo "Backend API: $BACKEND_URL"
echo "API Docs: $BACKEND_URL/docs"
echo ""
echo "Open the dashboard in your browser to deploy MemMachine instances!"
```

---

## 🐛 Troubleshooting

### Issue 1: Backend Returns 503

**Symptom:** Backend health check fails with 503 Service Unavailable

**Solution:**
```bash
# Check backend logs
gcloud run services logs read memcloud-backend --region=$REGION --limit=50

# Look for database connection errors
# If you see "Connection timed out", verify:

# 1. Cloud SQL is running
gcloud sql instances describe memcloud-postgres --format='get(state)'

# 2. Authorized networks configured
gcloud sql instances describe memcloud-postgres --format='get(settings.ipConfiguration.authorizedNetworks)'

# 3. Correct IP in environment
gcloud run services describe memcloud-backend --format='get(spec.template.spec.containers[0].env)'
```

### Issue 2: Frontend Can't Connect to Backend

**Symptom:** Frontend shows connection errors

**Solution:**
```bash
# Check frontend environment variable
gcloud run services describe memcloud-frontend \
  --format='get(spec.template.spec.containers[0].env)' | grep NEXT_PUBLIC_API_URL

# Should match backend URL
echo "Backend URL: $BACKEND_URL"

# Update if wrong
gcloud run services update memcloud-frontend \
  --set-env-vars="NEXT_PUBLIC_API_URL=$BACKEND_URL" \
  --region=$REGION
```

### Issue 3: MemMachine Instance Won't Deploy

**Symptom:** Deployment fails with "psycopg2 not found"

**Solution:**
```bash
# Verify custom image is being used
gcloud container images list --repository=gcr.io/$PROJECT_ID

# Check if psycopg2 was installed during build
docker run --rm gcr.io/$PROJECT_ID/memmachine-custom:latest \
  /app/.venv/bin/python -c "import psycopg2; print(psycopg2.__version__)"

# Should print version number (e.g., 2.9.11)
```

### Issue 4: Neo4j Aura Connection Failed

**Symptom:** MemMachine can't connect to Neo4j Aura

**Solution:**
```bash
# Verify Neo4j Aura credentials
# 1. Check URI format: neo4j+s://xxxxx.databases.neo4j.io (no port, no protocol://bolt)
# 2. Check username: usually "neo4j"
# 3. Check password: from Neo4j Aura console

# Test connection from Cloud Shell
pip3 install neo4j
python3 << EOF
from neo4j import GraphDatabase
uri = "neo4j+s://YOUR_AURA_ID.databases.neo4j.io"
driver = GraphDatabase.driver(uri, auth=("neo4j", "YOUR_PASSWORD"))
with driver.session() as session:
    result = session.run("RETURN 1 as num")
    print("Connection successful:", result.single()["num"])
driver.close()
EOF
```

---

## 🎯 Production Checklist

Before going live:

- [ ] Change all default passwords
- [ ] Set up monitoring and alerting
- [ ] Configure custom domain
- [ ] Enable Cloud Armor (DDoS protection)
- [ ] Set up automated backups for Cloud SQL
- [ ] Configure budget alerts
- [ ] Review IAM permissions (principle of least privilege)
- [ ] Enable audit logging
- [ ] Set up CI/CD pipeline
- [ ] Document disaster recovery procedures
- [ ] Test rollback procedures
- [ ] Load test the application

---

## 📊 Monitoring & Operations

### View Logs

```bash
# Backend logs
gcloud run services logs read memcloud-backend --region=$REGION --tail

# Frontend logs
gcloud run services logs read memcloud-frontend --region=$REGION --tail

# Database logs
gcloud sql operations list --instance=memcloud-postgres --limit=10
```

### Scale Services

```bash
# Increase backend capacity
gcloud run services update memcloud-backend \
  --max-instances=20 \
  --cpu=2 \
  --memory=4Gi \
  --region=$REGION

# Increase database capacity
gcloud sql instances patch memcloud-postgres \
  --tier=db-n1-standard-1
```

### Backup Database

```bash
# Create manual backup
gcloud sql backups create --instance=memcloud-postgres

# List backups
gcloud sql backups list --instance=memcloud-postgres
```

---

## 🧹 Cleanup (Development Only)

To delete all resources:

```bash
# Delete Cloud Run services
gcloud run services delete memcloud-backend --region=$REGION --quiet
gcloud run services delete memcloud-frontend --region=$REGION --quiet

# Delete Cloud SQL
gcloud sql instances delete memcloud-postgres --quiet

# Delete secrets
gcloud secrets delete memcloud-db-password --quiet

# Delete container images
gcloud container images delete gcr.io/$PROJECT_ID/memcloud-backend:latest --quiet
gcloud container images delete gcr.io/$PROJECT_ID/memcloud-frontend:latest --quiet
gcloud container images delete gcr.io/$PROJECT_ID/memmachine-custom:latest --quiet

# Delete project (WARNING: irreversible!)
# gcloud projects delete $PROJECT_ID
```

---

## 📚 Additional Resources

- [GCP Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Cloud SQL Best Practices](https://cloud.google.com/sql/docs/postgres/best-practices)
- [Neo4j Aura Documentation](https://neo4j.com/docs/aura/)
- [MemMachine GitHub](https://github.com/memverge-ai/memmachine)

---

**Document Version:** 2.0
**Includes:** Neo4j Aura support, PUBLIC IP configuration, psycopg2 fix
**Tested:** October 2025
**Next Steps:** See `DEPLOY_AWS.md` or `DEPLOY_AZURE.md` for other cloud providers
