# MemMachine Custom Docker Image

This directory contains the custom MemMachine Docker image with PostgreSQL support.

## Why This Is Needed

The official `memmachine/memmachine:latest` image does not include PostgreSQL support (`psycopg2`). When deploying with Cloud SQL, RDS, or Azure Database for PostgreSQL, MemMachine needs `psycopg2-binary` installed.

## The Critical Fix

```dockerfile
# Install psycopg2-binary to the EXACT location where venv Python looks
RUN /usr/local/bin/python3 -m pip install --no-cache-dir \
    --target=/app/.venv/lib/python3.12/site-packages \
    psycopg2-binary
```

**Why this specific location?**
- MemMachine uses `/app/.venv/bin/python` (a symlink to `/usr/local/bin/python3`)
- Python's `sys.path` includes `/app/.venv/lib/python3.12/site-packages`
- Installing to system Python doesn't work (wrong location)
- Installing at runtime is too slow (MemMachine starts before it completes)

## Files

- **Dockerfile** - Custom image build instructions
- **startup.sh** - Container startup script that:
  - Verifies psycopg2 installation
  - Generates MemMachine configuration from environment variables
  - Starts MemMachine server

## Usage

### Build Image (Local)

```bash
docker build -t memmachine-custom:latest .
```

### Build and Push to GCP

```bash
# Build
docker build -t gcr.io/$PROJECT_ID/memmachine-custom:latest .

# Push
docker push gcr.io/$PROJECT_ID/memmachine-custom:latest
```

### Build and Push to AWS

```bash
# Login to ECR
aws ecr get-login-password --region $AWS_REGION | \
  docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Build
docker build -t $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/memmachine-custom:latest .

# Push
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/memmachine-custom:latest
```

### Build and Push to Azure

```bash
# Login to ACR
az acr login --name $ACR_NAME

# Build
docker build -t $ACR_LOGIN_SERVER/memmachine-custom:latest .

# Push
docker push $ACR_LOGIN_SERVER/memmachine-custom:latest
```

## Environment Variables Required

The container expects these environment variables:

```bash
# PostgreSQL
POSTGRES_HOST=your-db-host
POSTGRES_PORT=5432
POSTGRES_PASSWORD=your-password

# Neo4j (Aura or self-hosted)
NEO4J_HOST=xxxxx.databases.neo4j.io
NEO4J_PASSWORD=your-password

# OpenAI
OPENAI_API_KEY=sk-...

# Server (set by cloud provider)
PORT=8080
```

## Testing Locally

```bash
docker run -p 8080:8080 \
  -e POSTGRES_HOST=localhost \
  -e POSTGRES_PASSWORD=test \
  -e NEO4J_HOST=localhost \
  -e NEO4J_PASSWORD=test \
  -e OPENAI_API_KEY=sk-test \
  memmachine-custom:latest
```

## Verification

The container logs should show:

```
🚀 Starting MemMachine Cloud Run instance...
🔍 Verifying psycopg2 installation...
psycopg2 version: 2.9.11 (dt dec pq3 ext lo64)
✅ psycopg2 is available
📝 Generating configuration from environment...
✅ Configuration file created
🔧 Syncing profile schema...
🎯 Starting MemMachine server on port 8080...
```

## Troubleshooting

### psycopg2 not found

If you see `ModuleNotFoundError: No module named 'psycopg2'`:

1. Verify the Dockerfile uses the exact `--target` path shown above
2. Rebuild the image (don't skip Docker cache)
3. Test with: `docker run --rm IMAGE /app/.venv/bin/python -c "import psycopg2; print(psycopg2.__version__)"`

### Container exits immediately

Check logs:
- **GCP:** `gcloud run services logs read SERVICE_NAME`
- **AWS:** `aws logs tail /ecs/SERVICE_NAME`
- **Azure:** `az container logs --name CONTAINER_NAME`

Common causes:
- Missing environment variables
- Wrong PostgreSQL credentials
- Neo4j Aura connection failed

## References

- [DEPLOY_GCP.md](../DEPLOY_GCP.md) - Full GCP deployment guide
- [DEPLOY_AWS.md](../DEPLOY_AWS.md) - Full AWS deployment guide
- [DEPLOY_AZURE.md](../DEPLOY_AZURE.md) - Full Azure deployment guide
- [TROUBLESHOOTING_RUNBOOK.md](../TROUBLESHOOTING_RUNBOOK.md) - Common errors and solutions
