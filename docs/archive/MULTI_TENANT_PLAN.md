# Multi-Tenant MemMachine Deployment Plan

**Goal:** Each user gets their own isolated MemMachine instance with their own OpenAI key and databases.

## Complexity Assessment: ⭐⭐⭐ (Medium - 4-6 hours)

**Why it's manageable:**
- ✅ We already have a working MemMachine deployment
- ✅ We have infrastructure code (deploy scripts)
- ✅ Cloud Run makes per-user instances easy
- ✅ Your dashboard UI already has the "Deploy Instance" button

**Challenges:**
- Need to create resources dynamically per user
- Need to track which resources belong to which user
- Need to handle user's OpenAI API keys securely
- Need to implement cleanup when user deletes instance

---

## Architecture: Per-User Isolation

### What Each User Gets:

```
User "brandon@email.com" clicks "Deploy Instance"
  ↓
Creates:
  1. Cloud Run MemMachine:    memmachine-brandon-abc123
  2. Cloud Run Neo4j:         neo4j-brandon-abc123
  3. PostgreSQL Database:     memmachine-brandon-abc123
  4. Secret (their API key):  openai-key-brandon-abc123
  ↓
User's playground connects ONLY to their instances
  ↓
User's conversations stored in THEIR database
  ↓
User's OpenAI key used for THEIR requests
```

---

## Implementation Steps

### Phase 1: Backend API Updates (2 hours)

#### 1.1 Create Deployment Endpoint
**File:** `backend/app/api/v1/endpoints/deployment.py` (already exists!)

Update to handle full deployment:

```python
@router.post("/deploy")
async def deploy_instance(
    request: DeploymentRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Deploy a complete MemMachine instance for a user.

    Steps:
    1. Generate unique instance ID
    2. Store user's OpenAI key in Secret Manager
    3. Deploy PostgreSQL Cloud SQL instance
    4. Deploy Neo4j Cloud Run service
    5. Deploy MemMachine Cloud Run service
    6. Store deployment info in Supabase
    7. Return instance details
    """

    instance_id = f"{current_user.id}-{uuid.uuid4().hex[:8]}"

    # 1. Store OpenAI key securely
    secret_name = f"openai-key-{instance_id}"
    await store_secret(secret_name, request.openai_api_key)

    # 2. Deploy PostgreSQL
    db_instance = await deploy_postgres(
        instance_name=f"memmachine-{instance_id}",
        user="memuser",
        password=generate_secure_password(),
        database="memmachine"
    )

    # 3. Deploy Neo4j
    neo4j_service = await deploy_neo4j(
        service_name=f"neo4j-{instance_id}",
        password=generate_secure_password()
    )

    # 4. Deploy MemMachine
    memmachine_service = await deploy_memmachine(
        service_name=f"memmachine-{instance_id}",
        openai_secret=secret_name,
        postgres_host=db_instance.ip,
        neo4j_url=neo4j_service.url
    )

    # 5. Store deployment record
    deployment = await db.deployments.create({
        "user_id": current_user.id,
        "instance_id": instance_id,
        "memmachine_url": memmachine_service.url,
        "neo4j_url": neo4j_service.url,
        "postgres_instance": db_instance.name,
        "status": "running",
        "created_at": datetime.utcnow()
    })

    return deployment
```

#### 1.2 Deployment Helper Functions

**File:** `backend/app/services/memmachine_deployer.py` (already exists!)

Add these functions:

```python
async def deploy_postgres(instance_name: str, user: str, password: str, database: str):
    """Deploy Cloud SQL PostgreSQL instance."""
    cmd = f"""
    gcloud sql instances create {instance_name} \
      --database-version=POSTGRES_15 \
      --tier=db-f1-micro \
      --region=us-central1 \
      --authorized-networks=0.0.0.0/0 \
      --project=memmachine-cloud
    """
    await run_command(cmd)

    # Create database
    await run_command(f"gcloud sql databases create {database} --instance={instance_name}")

    # Create user
    await run_command(f"gcloud sql users create {user} --instance={instance_name} --password={password}")

    # Get IP
    ip = await get_instance_ip(instance_name)

    return {
        "name": instance_name,
        "ip": ip,
        "user": user,
        "password": password,
        "database": database
    }

async def deploy_neo4j(service_name: str, password: str):
    """Deploy Neo4j Cloud Run service."""
    cmd = f"""
    gcloud run deploy {service_name} \
      --image neo4j:5.13.0 \
      --platform managed \
      --region us-central1 \
      --set-env-vars NEO4J_AUTH=neo4j/{password} \
      --allow-unauthenticated \
      --memory 2Gi \
      --cpu 1 \
      --project memmachine-cloud
    """
    await run_command(cmd)

    url = await get_service_url(service_name)

    return {
        "name": service_name,
        "url": url,
        "password": password
    }

async def deploy_memmachine(
    service_name: str,
    openai_secret: str,
    postgres_host: str,
    neo4j_url: str
):
    """Deploy MemMachine Cloud Run service."""
    cmd = f"""
    gcloud run deploy {service_name} \
      --image gcr.io/memmachine-cloud/memmachine:latest \
      --platform managed \
      --region us-central1 \
      --allow-unauthenticated \
      --memory 2Gi \
      --cpu 2 \
      --timeout 300 \
      --set-env-vars POSTGRES_HOST={postgres_host},NEO4J_HOST={neo4j_url} \
      --set-secrets OPENAI_API_KEY={openai_secret}:latest \
      --project memmachine-cloud
    """
    await run_command(cmd)

    url = await get_service_url(service_name)

    return {
        "name": service_name,
        "url": url
    }

async def store_secret(name: str, value: str):
    """Store secret in Google Secret Manager."""
    cmd = f'echo -n "{value}" | gcloud secrets create {name} --data-file=- --project=memmachine-cloud'
    await run_command(cmd)
```

#### 1.3 Cleanup Endpoint

```python
@router.delete("/instances/{instance_id}")
async def delete_instance(
    instance_id: str,
    current_user: User = Depends(get_current_user)
):
    """Delete all resources for an instance."""

    deployment = await db.deployments.get(instance_id)

    if deployment.user_id != current_user.id:
        raise HTTPException(403, "Not authorized")

    # Delete in reverse order
    await delete_memmachine_service(f"memmachine-{instance_id}")
    await delete_neo4j_service(f"neo4j-{instance_id}")
    await delete_postgres_instance(f"memmachine-{instance_id}")
    await delete_secret(f"openai-key-{instance_id}")

    await db.deployments.delete(instance_id)

    return {"status": "deleted"}
```

---

### Phase 2: Database Schema (30 minutes)

**Supabase Table: `deployments`**

```sql
CREATE TABLE deployments (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES auth.users(id) NOT NULL,
  instance_id TEXT UNIQUE NOT NULL,

  -- Service URLs
  memmachine_url TEXT NOT NULL,
  neo4j_url TEXT NOT NULL,

  -- Resource names
  postgres_instance TEXT NOT NULL,
  memmachine_service TEXT NOT NULL,
  neo4j_service TEXT NOT NULL,
  openai_secret TEXT NOT NULL,

  -- Status
  status TEXT DEFAULT 'deploying',
  error_message TEXT,

  -- Timestamps
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  deleted_at TIMESTAMPTZ,

  -- Constraints
  CONSTRAINT valid_status CHECK (status IN ('deploying', 'running', 'error', 'deleting', 'deleted'))
);

CREATE INDEX idx_deployments_user ON deployments(user_id);
CREATE INDEX idx_deployments_instance ON deployments(instance_id);
```

---

### Phase 3: Frontend Updates (1 hour)

#### 3.1 Update Dashboard Deploy Button

**File:** `frontend/app/dashboard/page.tsx`

```typescript
const handleDeploy = async () => {
  setDeploying(true);

  try {
    const response = await fetch('/api/deploy', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        openai_api_key: openaiKey,
        instance_name: instanceName || `instance-${Date.now()}`
      })
    });

    const deployment = await response.json();

    // Poll for completion
    const checkStatus = setInterval(async () => {
      const status = await fetch(`/api/instances/${deployment.instance_id}`);
      const data = await status.json();

      if (data.status === 'running') {
        clearInterval(checkStatus);
        setDeploying(false);
        router.push(`/playground/${deployment.instance_id}`);
      }
    }, 5000);

  } catch (error) {
    setError(error.message);
    setDeploying(false);
  }
};
```

#### 3.2 Update Playground to Use User's Instance

**File:** `frontend/app/playground/[id]/page.tsx`

```typescript
const { data: instance } = await fetch(`/api/instances/${params.id}`);

// Use user's specific MemMachine URL
const memmachineUrl = instance.memmachine_url;

// Send messages to user's instance
const response = await fetch(`${memmachineUrl}/v1/chat`, {
  method: 'POST',
  body: JSON.stringify({
    session: {
      group_id: 'memcloud',
      agent_id: ['assistant'],
      user_id: [userId],
      session_id: params.id
    },
    messages: messages
  })
});
```

---

### Phase 4: Cost Optimization (1 hour)

#### 4.1 Resource Tiers

```python
DEPLOYMENT_TIERS = {
    "free": {
        "postgres": "db-f1-micro",  # Shared core
        "memmachine_memory": "512Mi",
        "neo4j_memory": "512Mi",
        "max_sessions": 10
    },
    "pro": {
        "postgres": "db-g1-small",  # 1 vCPU
        "memmachine_memory": "2Gi",
        "neo4j_memory": "2Gi",
        "max_sessions": 100
    }
}
```

#### 4.2 Auto-Shutdown for Inactive Instances

```python
@app.on_event("startup")
async def schedule_cleanup():
    """Shutdown instances inactive for 24 hours."""

    async def cleanup_inactive():
        while True:
            inactive = await db.deployments.find({
                "last_activity": {"$lt": datetime.now() - timedelta(hours=24)},
                "status": "running"
            })

            for deployment in inactive:
                await pause_instance(deployment.instance_id)

            await asyncio.sleep(3600)  # Check every hour

    asyncio.create_task(cleanup_inactive())
```

---

## Timeline & Effort

| Phase | Task | Time | Difficulty |
|-------|------|------|------------|
| 1 | Backend deployment API | 2h | ⭐⭐ |
| 2 | Database schema | 30min | ⭐ |
| 3 | Frontend integration | 1h | ⭐⭐ |
| 4 | Cost optimization | 1h | ⭐ |
| 5 | Testing & debugging | 1.5h | ⭐⭐⭐ |
| **Total** | | **6 hours** | ⭐⭐⭐ |

---

## Cost Implications

### Per User (Free Tier):
- **Cloud Run MemMachine:** $0.05/hour when active (free tier: 2M requests/month)
- **Cloud Run Neo4j:** $0.05/hour when active
- **Cloud SQL Micro:** $7/month (always on) or $0.01/hour (if can pause)
- **Total:** ~$15-20/month per active user (or $0.10/hour if can pause)

### Cost Mitigation:
1. **Auto-pause** inactive instances after 1 hour
2. **Free tier:** Limit to 100 active instances
3. **Paid tier:** $5/month/user covers infrastructure + profit
4. **Shared option:** Power users can opt for shared MemMachine at $0

---

## Rollout Strategy

### Week 1: MVP
- [ ] Implement deployment API
- [ ] Test with 1-2 users manually
- [ ] Verify isolation works

### Week 2: Beta
- [ ] Add dashboard UI
- [ ] Invite 10 beta testers
- [ ] Monitor costs

### Week 3: Production
- [ ] Add auto-pause
- [ ] Add pricing tiers
- [ ] Public launch

---

## Next Actions (Priority Order)

1. **Commit current working code** ✅
2. **Backup databases** ✅
3. **Implement deployment API** (backend/app/api/v1/endpoints/deployment.py)
4. **Test single manual deployment** (prove concept)
5. **Wire up frontend**
6. **Add cost controls**

---

**Want to start? I can implement Phase 1 (deployment API) right now!**
