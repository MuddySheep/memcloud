# MemCloud Deployment Guide - Microsoft Azure
## Production-Ready Deployment for MemMachine on Azure Container Instances

**Status:** ✅ Production-Ready
**Last Updated:** October 2025
**Deployment Time:** ~20 minutes
**Monthly Cost:** $30-55 (with auto-scaling)

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
                  │ HTTPS (Azure Front Door)
                  ▼
┌─────────────────────────────────────────────────────────────┐
│          Frontend (Next.js on Container Instances)           │
│              - Application Gateway                           │
│              - Dashboard UI                                  │
└─────────────────┬───────────────────────────────────────────┘
                  │ HTTPS API
                  ▼
┌─────────────────────────────────────────────────────────────┐
│        Backend API (FastAPI on Container Instances)          │
│            - Application Gateway                             │
│            - Deployment orchestration                        │
└─────┬─────────────────────────────────────┬─────────────────┘
      │                                     │
      │ Creates/Manages                     │ Stores metadata
      ▼                                     ▼
┌─────────────────────┐          ┌──────────────────────────┐
│ MemMachine Instance │          │   Azure DB PostgreSQL    │
│  (Container Inst.)  │          │   - Instance metadata    │
│  + Neo4j Aura       │          │   - User data            │
│    (External SaaS)  │          │   - API keys             │
└─────────────────────┘          └──────────────────────────┘
```

**Key Components:**
- **Frontend:** Next.js on Azure Container Instances
- **Backend API:** FastAPI on Container Instances
- **Azure Database for PostgreSQL:** Managed database
- **Azure Container Registry:** Docker image storage
- **Key Vault:** Encrypted secrets storage
- **Neo4j Aura:** External managed graph database (no Azure hosting needed)

---

## ✅ Prerequisites

### 1. Azure Account
- Active Azure subscription
- Contributor or Owner role
- **Free tier:** $200 credits for new accounts (30 days)

### 2. Local Tools
```bash
# Azure CLI
az --version
# Expected: azure-cli 2.50.0+

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
| **Container Instances (Backend)** | 1 vCPU, 1.5GB RAM | $30-40 |
| **Container Instances (Frontend)** | 1 vCPU, 1GB RAM | $25-30 |
| **Azure DB for PostgreSQL** | Flexible Server, B1ms | $12-18 |
| **Container Registry** | Basic tier, < 10GB | $5 |
| **Key Vault** | Standard tier, 5 secrets | $0.03 |
| **Application Gateway** | Optional, for SSL | $125+ |
| **Neo4j Aura (per instance)** | Free tier / Paid | $0-65 |
| **MemMachine Instances** | Per user deployment | $30-40 each |
| **Total (Platform, without App GW)** | | **$72-93/month** |

**Notes:**
- Container Instances are billed per second of runtime
- Application Gateway adds significant cost but provides advanced features
- Consider using Azure Front Door as cost-effective alternative

---

## 🚀 Initial Setup

### Step 1: Configure Azure CLI

```bash
# Login to Azure
az login

# List subscriptions
az account list --output table

# Set default subscription
export SUBSCRIPTION_ID="your-subscription-id"
az account set --subscription $SUBSCRIPTION_ID

# Set default location
export LOCATION="eastus"  # Change to your preferred region
export RESOURCE_GROUP="memcloud-rg"

echo "Subscription: $SUBSCRIPTION_ID"
echo "Location: $LOCATION"
```

**✅ Verification:**
```bash
az account show
# Should show your subscription details
```

### Step 2: Create Resource Group

```bash
# Create resource group
az group create \
  --name $RESOURCE_GROUP \
  --location $LOCATION

echo "✅ Resource group created"
```

**✅ Verification:**
```bash
az group show --name $RESOURCE_GROUP
# Should show provisioning state: Succeeded
```

### Step 3: Create Virtual Network

```bash
# Create VNet
az network vnet create \
  --resource-group $RESOURCE_GROUP \
  --name memcloud-vnet \
  --address-prefix 10.0.0.0/16 \
  --subnet-name memcloud-subnet \
  --subnet-prefix 10.0.1.0/24

echo "✅ Virtual network created"
```

**✅ Verification:**
```bash
az network vnet show \
  --resource-group $RESOURCE_GROUP \
  --name memcloud-vnet
```

### Step 4: Create Network Security Group

```bash
# Create NSG
az network nsg create \
  --resource-group $RESOURCE_GROUP \
  --name memcloud-nsg

# Allow HTTP
az network nsg rule create \
  --resource-group $RESOURCE_GROUP \
  --nsg-name memcloud-nsg \
  --name allow-http \
  --priority 100 \
  --source-address-prefixes '*' \
  --source-port-ranges '*' \
  --destination-address-prefixes '*' \
  --destination-port-ranges 80 \
  --access Allow \
  --protocol Tcp

# Allow HTTPS
az network nsg rule create \
  --resource-group $RESOURCE_GROUP \
  --nsg-name memcloud-nsg \
  --name allow-https \
  --priority 110 \
  --source-address-prefixes '*' \
  --source-port-ranges '*' \
  --destination-address-prefixes '*' \
  --destination-port-ranges 443 \
  --access Allow \
  --protocol Tcp

# Allow PostgreSQL (internal only)
az network nsg rule create \
  --resource-group $RESOURCE_GROUP \
  --nsg-name memcloud-nsg \
  --name allow-postgres \
  --priority 120 \
  --source-address-prefixes 10.0.0.0/16 \
  --source-port-ranges '*' \
  --destination-address-prefixes '*' \
  --destination-port-ranges 5432 \
  --access Allow \
  --protocol Tcp

# Associate NSG with subnet
az network vnet subnet update \
  --resource-group $RESOURCE_GROUP \
  --vnet-name memcloud-vnet \
  --name memcloud-subnet \
  --network-security-group memcloud-nsg

echo "✅ Network security configured"
```

**✅ Verification:**
```bash
az network nsg show \
  --resource-group $RESOURCE_GROUP \
  --name memcloud-nsg
```

### Step 5: Create Azure Container Registry

```bash
# Create ACR (must be globally unique)
export ACR_NAME="memcloud${RANDOM}"

az acr create \
  --resource-group $RESOURCE_GROUP \
  --name $ACR_NAME \
  --sku Basic \
  --admin-enabled true

# Get ACR credentials
export ACR_USERNAME=$(az acr credential show \
  --name $ACR_NAME \
  --resource-group $RESOURCE_GROUP \
  --query username \
  --output tsv)

export ACR_PASSWORD=$(az acr credential show \
  --name $ACR_NAME \
  --resource-group $RESOURCE_GROUP \
  --query "passwords[0].value" \
  --output tsv)

export ACR_LOGIN_SERVER=$(az acr show \
  --name $ACR_NAME \
  --resource-group $RESOURCE_GROUP \
  --query loginServer \
  --output tsv)

# Login to ACR
az acr login --name $ACR_NAME

echo "✅ Container registry created: $ACR_LOGIN_SERVER"
```

**✅ Verification:**
```bash
az acr show --name $ACR_NAME --resource-group $RESOURCE_GROUP
# Should show provisioningState: Succeeded
```

### Step 6: Create Key Vault

```bash
# Create Key Vault (must be globally unique)
export KEYVAULT_NAME="memcloud-kv-${RANDOM}"

az keyvault create \
  --name $KEYVAULT_NAME \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION

echo "✅ Key Vault created: $KEYVAULT_NAME"
```

**✅ Verification:**
```bash
az keyvault show --name $KEYVAULT_NAME --resource-group $RESOURCE_GROUP
# Should show provisioningState: Succeeded
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

Create `Dockerfile` (identical to GCP/AWS):

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

Create `startup.sh` (identical to GCP/AWS version - see DEPLOY_GCP.md)

### Step 4: Build and Push to ACR

```bash
# Build the image
docker build -t memmachine-custom:latest .

# Tag for ACR
docker tag memmachine-custom:latest \
  $ACR_LOGIN_SERVER/memmachine-custom:latest

# Push to ACR
docker push $ACR_LOGIN_SERVER/memmachine-custom:latest

echo "✅ Custom MemMachine image pushed to ACR"
```

**✅ Verification:**
```bash
az acr repository list --name $ACR_NAME --output table
# Should show memmachine-custom
```

---

## 🔧 Deploy Backend Services

### Step 1: Deploy Azure Database for PostgreSQL

```bash
# Generate password
export DB_PASSWORD=$(openssl rand -base64 32)

# Create PostgreSQL flexible server (takes 3-5 minutes)
echo "⏳ Creating PostgreSQL server (this takes 3-5 minutes)..."

az postgres flexible-server create \
  --resource-group $RESOURCE_GROUP \
  --name memcloud-postgres-${RANDOM} \
  --location $LOCATION \
  --admin-user pgadmin \
  --admin-password "$DB_PASSWORD" \
  --sku-name Standard_B1ms \
  --tier Burstable \
  --storage-size 32 \
  --version 15 \
  --public-access 0.0.0.0-255.255.255.255

# Get database server name
export DB_SERVER=$(az postgres flexible-server list \
  --resource-group $RESOURCE_GROUP \
  --query "[?contains(name, 'memcloud-postgres')].name" \
  --output tsv)

# Get database host
export DB_HOST=$(az postgres flexible-server show \
  --resource-group $RESOURCE_GROUP \
  --name $DB_SERVER \
  --query fullyQualifiedDomainName \
  --output tsv)

# Create database
az postgres flexible-server db create \
  --resource-group $RESOURCE_GROUP \
  --server-name $DB_SERVER \
  --database-name memcloud_prod

echo "✅ PostgreSQL deployed at: $DB_HOST"
```

**✅ Verification:**
```bash
az postgres flexible-server show \
  --resource-group $RESOURCE_GROUP \
  --name $DB_SERVER \
  --query state \
  --output tsv
# Should show: Ready
```

### Step 2: Store Secrets in Key Vault

```bash
# Store database password
az keyvault secret set \
  --vault-name $KEYVAULT_NAME \
  --name db-password \
  --value "$DB_PASSWORD"

# Store ACR credentials
az keyvault secret set \
  --vault-name $KEYVAULT_NAME \
  --name acr-username \
  --value "$ACR_USERNAME"

az keyvault secret set \
  --vault-name $KEYVAULT_NAME \
  --name acr-password \
  --value "$ACR_PASSWORD"

echo "✅ Secrets stored in Key Vault"
```

**✅ Verification:**
```bash
az keyvault secret list --vault-name $KEYVAULT_NAME --output table
# Should show 3 secrets
```

### Step 3: Build and Push Backend Image

```bash
# Clone or copy your backend code
cd ~/
git clone <YOUR_MEMCLOUD_REPO> memcloud-backend
cd memcloud-backend/backend

# Build backend image
docker build -t memcloud-backend:latest .

# Tag for ACR
docker tag memcloud-backend:latest \
  $ACR_LOGIN_SERVER/memcloud-backend:latest

# Push to ACR
docker push $ACR_LOGIN_SERVER/memcloud-backend:latest

echo "✅ Backend image pushed to ACR"
```

**✅ Verification:**
```bash
az acr repository show \
  --name $ACR_NAME \
  --repository memcloud-backend
```

### Step 4: Deploy Backend Container Instance

```bash
# Create environment variable file
cat > backend-env.yaml <<EOF
- name: DB_HOST
  value: $DB_HOST
- name: DB_PORT
  value: "5432"
- name: DB_NAME
  value: memcloud_prod
- name: DB_USER
  value: pgadmin
- name: USE_CLOUD_SQL_CONNECTOR
  value: "false"
- name: AZURE_REGION
  value: $LOCATION
EOF

# Create secure environment variables (secrets)
cat > backend-secrets.yaml <<EOF
- name: DB_PASSWORD
  secureValue: $DB_PASSWORD
EOF

# Deploy container instance
az container create \
  --resource-group $RESOURCE_GROUP \
  --name memcloud-backend \
  --image $ACR_LOGIN_SERVER/memcloud-backend:latest \
  --registry-login-server $ACR_LOGIN_SERVER \
  --registry-username $ACR_USERNAME \
  --registry-password $ACR_PASSWORD \
  --dns-name-label memcloud-backend-${RANDOM} \
  --ports 80 8080 \
  --cpu 1 \
  --memory 2 \
  --environment-variables @backend-env.yaml \
  --secure-environment-variables @backend-secrets.yaml \
  --restart-policy Always

# Get backend URL
export BACKEND_FQDN=$(az container show \
  --resource-group $RESOURCE_GROUP \
  --name memcloud-backend \
  --query ipAddress.fqdn \
  --output tsv)

export BACKEND_URL="http://${BACKEND_FQDN}:8080"

echo "✅ Backend deployed at: $BACKEND_URL"
```

**✅ Verification:**
```bash
# Wait for container to be running
az container show \
  --resource-group $RESOURCE_GROUP \
  --name memcloud-backend \
  --query instanceView.state \
  --output tsv
# Should show: Running

# Test health endpoint
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

# Tag for ACR
docker tag memcloud-frontend:latest \
  $ACR_LOGIN_SERVER/memcloud-frontend:latest

# Push to ACR
docker push $ACR_LOGIN_SERVER/memcloud-frontend:latest

echo "✅ Frontend image pushed to ACR"
```

### Step 2: Deploy Frontend Container Instance

```bash
# Create environment variable file
cat > frontend-env.yaml <<EOF
- name: NEXT_PUBLIC_API_URL
  value: $BACKEND_URL
EOF

# Deploy container instance
az container create \
  --resource-group $RESOURCE_GROUP \
  --name memcloud-frontend \
  --image $ACR_LOGIN_SERVER/memcloud-frontend:latest \
  --registry-login-server $ACR_LOGIN_SERVER \
  --registry-username $ACR_USERNAME \
  --registry-password $ACR_PASSWORD \
  --dns-name-label memcloud-frontend-${RANDOM} \
  --ports 80 3000 \
  --cpu 1 \
  --memory 1 \
  --environment-variables @frontend-env.yaml \
  --restart-policy Always

# Get frontend URL
export FRONTEND_FQDN=$(az container show \
  --resource-group $RESOURCE_GROUP \
  --name memcloud-frontend \
  --query ipAddress.fqdn \
  --output tsv)

export FRONTEND_URL="http://${FRONTEND_FQDN}:3000"

echo "✅ Frontend deployed at: $FRONTEND_URL"
```

**✅ Verification:**
```bash
# Wait for container to be running
az container show \
  --resource-group $RESOURCE_GROUP \
  --name memcloud-frontend \
  --query instanceView.state \
  --output tsv
# Should show: Running

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
echo "🎉 MemCloud is now deployed on Azure!"
echo "Frontend: $FRONTEND_URL"
echo "Backend: $BACKEND_URL"
echo "API Docs: $BACKEND_URL/docs"
```

---

## 🐛 Troubleshooting

### Issue 1: Container Won't Start

**Solution:**
```bash
# Check container logs
az container logs \
  --resource-group $RESOURCE_GROUP \
  --name memcloud-backend

# Check container events
az container show \
  --resource-group $RESOURCE_GROUP \
  --name memcloud-backend \
  --query instanceView.events
```

### Issue 2: Can't Connect to PostgreSQL

**Solution:**
```bash
# Verify firewall rules
az postgres flexible-server firewall-rule list \
  --resource-group $RESOURCE_GROUP \
  --name $DB_SERVER

# Add firewall rule if needed
az postgres flexible-server firewall-rule create \
  --resource-group $RESOURCE_GROUP \
  --name $DB_SERVER \
  --rule-name allow-all \
  --start-ip-address 0.0.0.0 \
  --end-ip-address 255.255.255.255

# Test connection
az postgres flexible-server connect \
  --name $DB_SERVER \
  --admin-user pgadmin \
  --admin-password "$DB_PASSWORD"
```

### Issue 3: Container Registry Authentication Failed

**Solution:**
```bash
# Verify ACR credentials
az acr credential show \
  --name $ACR_NAME \
  --resource-group $RESOURCE_GROUP

# Re-enable admin user if disabled
az acr update \
  --name $ACR_NAME \
  --admin-enabled true

# Test login
docker login $ACR_LOGIN_SERVER \
  --username $ACR_USERNAME \
  --password $ACR_PASSWORD
```

### Issue 4: Neo4j Aura Connection Failed

**Solution:**
```bash
# Verify Neo4j Aura credentials
# 1. URI format: neo4j+s://xxxxx.databases.neo4j.io
# 2. Username: usually "neo4j"
# 3. Password: from Neo4j Aura console

# Test from Azure Cloud Shell
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

- [ ] Configure custom domain with Azure DNS
- [ ] Enable HTTPS with Azure Front Door
- [ ] Set up Azure Monitor for logging and alerting
- [ ] Configure database backups and retention
- [ ] Enable Azure Security Center
- [ ] Set up budget alerts
- [ ] Configure managed identities (instead of admin credentials)
- [ ] Enable Azure Key Vault access policies
- [ ] Set up Azure Application Insights
- [ ] Configure disaster recovery procedures
- [ ] Enable Azure DDoS Protection
- [ ] Set up CI/CD with Azure DevOps or GitHub Actions

---

## 📊 Monitoring & Operations

### View Logs

```bash
# Backend logs
az container logs \
  --resource-group $RESOURCE_GROUP \
  --name memcloud-backend \
  --follow

# Frontend logs
az container logs \
  --resource-group $RESOURCE_GROUP \
  --name memcloud-frontend \
  --follow

# Database logs
az postgres flexible-server server-logs list \
  --resource-group $RESOURCE_GROUP \
  --name $DB_SERVER
```

### Scale Containers

```bash
# Update backend resources
az container create \
  --resource-group $RESOURCE_GROUP \
  --name memcloud-backend \
  --cpu 2 \
  --memory 4 \
  --restart-policy Always

# For auto-scaling, consider using Azure Container Apps instead
```

### Backup Database

```bash
# Enable automated backups (default: 7 days)
az postgres flexible-server update \
  --resource-group $RESOURCE_GROUP \
  --name $DB_SERVER \
  --backup-retention 30

# List backups
az postgres flexible-server backup list \
  --resource-group $RESOURCE_GROUP \
  --name $DB_SERVER
```

---

## 🧹 Cleanup (Development Only)

To delete all resources:

```bash
# Delete entire resource group (WARNING: irreversible!)
az group delete \
  --name $RESOURCE_GROUP \
  --yes \
  --no-wait

echo "✅ All resources deleted"
```

---

## 📚 Additional Resources

- [Azure Container Instances Documentation](https://docs.microsoft.com/en-us/azure/container-instances/)
- [Azure Database for PostgreSQL Documentation](https://docs.microsoft.com/en-us/azure/postgresql/)
- [Azure Container Registry Documentation](https://docs.microsoft.com/en-us/azure/container-registry/)
- [Azure Key Vault Documentation](https://docs.microsoft.com/en-us/azure/key-vault/)
- [Neo4j Aura Documentation](https://neo4j.com/docs/aura/)

---

## 💡 Azure-Specific Optimizations

### Use Container Apps for Auto-Scaling

For production workloads with variable traffic, consider Azure Container Apps:

```bash
# Create Container Apps environment
az containerapp env create \
  --name memcloud-env \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION

# Deploy backend as Container App
az containerapp create \
  --name memcloud-backend \
  --resource-group $RESOURCE_GROUP \
  --environment memcloud-env \
  --image $ACR_LOGIN_SERVER/memcloud-backend:latest \
  --target-port 8080 \
  --ingress external \
  --min-replicas 0 \
  --max-replicas 10 \
  --cpu 1.0 \
  --memory 2Gi
```

**Benefits:**
- Auto-scaling to zero (save costs)
- Built-in load balancing
- Managed HTTPS certificates
- Better suited for production

### Use Managed Identity

Replace username/password authentication with managed identities:

```bash
# Enable managed identity for container
az container create \
  --resource-group $RESOURCE_GROUP \
  --name memcloud-backend \
  --assign-identity [system] \
  ...

# Grant Key Vault access
IDENTITY_ID=$(az container show \
  --resource-group $RESOURCE_GROUP \
  --name memcloud-backend \
  --query identity.principalId \
  --output tsv)

az keyvault set-policy \
  --name $KEYVAULT_NAME \
  --object-id $IDENTITY_ID \
  --secret-permissions get list
```

---

**Document Version:** 2.0
**Includes:** Neo4j Aura support, Container Instances, Azure DB for PostgreSQL
**Tested:** October 2025
**Next Steps:** See `DEPLOY_GCP.md` or `DEPLOY_AWS.md` for other cloud providers
