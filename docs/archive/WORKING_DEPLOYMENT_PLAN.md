# Working MemMachine Deployment Plan - With Proper Networking

## Mission: Get Memory Storage + Retrieval Working

## Problem We're Solving
Current deployment has services isolated - MemMachine can't talk to Neo4j or PostgreSQL.

## Solution: Three Options (Best to Worst)

### Option 1: Neo4j Aura + Cloud SQL (RECOMMENDED) 💰 ~$75/month

**Why Best**:
- ✅ Fully managed - no VM maintenance
- ✅ No VPC connector needed (saves $80/month)
- ✅ Neo4j Aura has free tier for testing
- ✅ Built-in backups and monitoring
- ✅ Scales automatically
- ✅ Secure by default

**Architecture**:
```
┌─────────────────────┐
│  MemMachine         │
│  Cloud Run          │
│  (HTTP/HTTPS only)  │
└──────┬──────────────┘
       │
       ├─────> Neo4j Aura (managed)
       │       bolt+s://xxxxx.databases.neo4j.io:7687
       │       (secured with SSL)
       │
       └─────> Cloud SQL PostgreSQL
               (via Cloud SQL Proxy built into Cloud Run)
```

**Steps**:
1. Create Neo4j Aura free tier account
2. Get connection string (bolt+s://...)
3. Update MemMachine env vars with Aura connection
4. Cloud SQL already works with Cloud Run (just needs connection name)
5. Deploy!

**Cost**: $0-65/month Neo4j + $7/month PostgreSQL = **$7-72/month**

### Option 2: Neo4j on Compute Engine + VPC 💰 ~$110/month

**Why Acceptable**:
- ✅ Full control over Neo4j
- ✅ Can optimize for performance
- ✅ One-time setup, then stable
- ❌ Requires VPC connector ($80/month always on)
- ❌ Manual VM maintenance
- ❌ Need to configure backups

**Architecture**:
```
┌─────────────────────┐      ┌──────────────┐
│  MemMachine         │      │   VPC        │
│  Cloud Run          │─────>│  Connector   │
│                     │      │  us-central1 │
└─────────────────────┘      └──────┬───────┘
                                    │
                            Private │ Network
                                    │
                        ┌───────────┴────────┐
                        │                    │
                  ┌─────▼──────┐      ┌─────▼──────┐
                  │   Neo4j    │      │ PostgreSQL │
                  │  e2-micro  │      │ Cloud SQL  │
                  │  :7687     │      │ (private)  │
                  └────────────┘      └────────────┘
```

**Steps**:
1. Create VPC network
2. Create VPC connector for Cloud Run
3. Deploy Neo4j on e2-micro Compute Engine
4. Deploy PostgreSQL with private IP
5. Configure firewall rules
6. Update MemMachine to use VPC connector
7. Deploy!

**Cost**: $15/month VM + $80/month VPC + $7/month PostgreSQL = **$102/month**

### Option 3: Full GKE Deployment 💰 ~$150/month

**Why Not Recommended**:
- ❌ Most expensive
- ❌ Most complex
- ❌ Overkill for single-tenant deployments
- ✅ Best for multi-tenant at scale

**Skip this for now** - only consider if we're running 50+ instances.

---

## RECOMMENDED IMPLEMENTATION: Option 1 (Neo4j Aura)

### Phase 1: Setup Neo4j Aura

1. **Sign up for Neo4j Aura Free Tier**
   ```
   Website: https://neo4j.com/cloud/aura/
   Free tier: 200k nodes, 400k relationships
   Perfect for testing!
   ```

2. **Create Database**
   - Region: us-central1 (same as Cloud Run)
   - Name: memcloud-neo4j
   - Get connection string
   - Save credentials to Secret Manager

3. **Test Connection**
   ```bash
   # From local machine or Cloud Shell
   cypher-shell -a "bolt+s://xxxxx.databases.neo4j.io" \
     -u neo4j -p "password"
   ```

### Phase 2: Configure PostgreSQL Cloud SQL

1. **Enable Private IP** (Optional but better)
   ```bash
   gcloud sql instances patch postgres-instance-name \
     --network=default \
     --enable-ip-aliasing
   ```

2. **Or Use Public IP with Cloud SQL Proxy**
   - Cloud Run has built-in Cloud SQL proxy
   - Just need instance connection name
   - Add to Cloud Run deployment

### Phase 3: Update MemMachine Deployment

**Updated deployer code** (`backend/app/services/memmachine_deployer.py`):

```python
async def deploy_complete_stack(
    self,
    user_id: str,
    instance_name: str,
    openai_api_key: str,
    neo4j_connection_string: str = None,  # NEW: For Aura
    use_managed_neo4j: bool = True,       # NEW: Skip Neo4j Cloud Run
) -> Instance:
    """Deploy MemMachine with working networking"""

    # 1. Deploy PostgreSQL Cloud SQL (same as before)
    postgres_instance = await self._deploy_cloud_sql(instance_id, postgres_password)

    # 2. Setup Neo4j - CHANGED
    if use_managed_neo4j and neo4j_connection_string:
        # Use Neo4j Aura - no deployment needed!
        neo4j_uri = neo4j_connection_string
        neo4j_password = await self._get_secret(f"neo4j-aura-password-{instance_id}")
    else:
        # Deploy Neo4j on Cloud Run (won't work without VPC)
        neo4j_service = await self._deploy_neo4j(instance_id, neo4j_password)
        neo4j_uri = f"bolt://{neo4j_service.url}:7687"

    # 3. Deploy MemMachine with correct connection strings
    memmachine_service = await self._deploy_memmachine(
        instance_id=instance_id,
        openai_api_key=openai_api_key,
        postgres_connection=postgres_connection_string,  # Cloud SQL connection name
        neo4j_uri=neo4j_uri,
        neo4j_password=neo4j_password,
    )

    return instance
```

**Environment variables for MemMachine**:
```bash
# Instead of hostname that doesn't resolve:
NEO4J_URI=bolt+s://xxxxx.databases.neo4j.io:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=<from-secret>

# PostgreSQL via Cloud SQL Proxy:
DB_HOST=/cloudsql/PROJECT:REGION:INSTANCE
# Or with public IP:
DB_HOST=<cloud-sql-ip>
DB_NAME=memmachine
DB_USER=memmachine
DB_PASSWORD=<from-secret>

# OpenAI:
OPENAI_API_KEY=<from-secret>
```

### Phase 4: Test Memory Operations

Once deployed with proper networking:

```bash
# 1. Store a memory
curl -X POST "$MEMMACHINE_URL/v1/memories" \
  -H "Content-Type: application/json" \
  -d '{
    "session": {
      "group_id": "test",
      "agent_id": ["assistant"],
      "user_id": ["brandon"],
      "session_id": "session_001"
    },
    "producer": "brandon",
    "produced_for": "assistant",
    "episode_content": "Brandon loves building AI systems",
    "episode_type": "message",
    "metadata": {}
  }'

# Should return: {"id": "episode-xxx", "status": "stored"}
# NOT: Internal Server Error or timeout

# 2. Search memories
curl -X POST "$MEMMACHINE_URL/v1/memories/search" \
  -H "Content-Type: application/json" \
  -d '{
    "session": {
      "group_id": "test",
      "agent_id": ["assistant"],
      "user_id": ["brandon"],
      "session_id": "session_001"
    },
    "query": "What does Brandon like?",
    "limit": 5
  }'

# Should return: [{"content": "Brandon loves building AI systems", ...}]
```

### Phase 5: Add Chat Wrapper

Once memory works, add chat endpoint:

**New file**: `backend/app/api/v1/endpoints/chat.py`

```python
from fastapi import APIRouter
from openai import AsyncOpenAI
import httpx

router = APIRouter()

@router.post("/v1/chat")
async def chat(
    session: SessionInfo,
    messages: List[Message],
):
    """Chat endpoint that uses memory"""

    # 1. Search relevant memories
    memories = await search_memories(
        memmachine_url=MEMMACHINE_URL,
        session=session,
        query=messages[-1].content,
        limit=5
    )

    # 2. Build context from memories
    context = "\\n".join([m.content for m in memories])

    # 3. Call OpenAI with context
    client = AsyncOpenAI()
    response = await client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": f"Context from memory: {context}"},
            *[{"role": m.role, "content": m.content} for m in messages]
        ]
    )

    # 4. Store conversation to memory
    await store_memory(
        memmachine_url=MEMMACHINE_URL,
        session=session,
        producer=session.user_id[0],
        content=messages[-1].content,
        episode_type="user_message"
    )

    await store_memory(
        memmachine_url=MEMMACHINE_URL,
        session=session,
        producer=session.agent_id[0],
        content=response.choices[0].message.content,
        episode_type="assistant_message"
    )

    # 5. Return response
    return {"content": response.choices[0].message.content}
```

## Implementation Timeline

### Week 1: Get Memory Working
- [ ] Day 1: Sign up for Neo4j Aura, create database
- [ ] Day 2: Update deployer to use Aura connection
- [ ] Day 3: Deploy new test instance
- [ ] Day 4: Test memory store + search
- [ ] Day 5: Verify persistence and search quality

### Week 2: Add Chat
- [ ] Day 1: Implement chat endpoint wrapper
- [ ] Day 2: Test with OpenAI integration
- [ ] Day 3: Add memory retrieval to chat
- [ ] Day 4: Test full conversation flow
- [ ] Day 5: Deploy and test playground

### Week 3: Dashboard Updates
- [ ] Day 1: Add "Memory Working" indicator
- [ ] Day 2: Add "Chat Enabled" indicator
- [ ] Day 3: Auto-detect capabilities on deployment
- [ ] Day 4: Update UI for different instance types
- [ ] Day 5: Document and polish

## Success Criteria

Instance is "working" when:
- ✅ Memory store completes in < 2 seconds
- ✅ Memory search returns relevant results
- ✅ No timeouts or connection errors
- ✅ Data persists across service restarts
- ✅ Can retrieve memories from previous sessions
- ✅ (Later) Chat maintains context across messages

## Cost Comparison

| Solution | Setup Time | Monthly Cost | Maintenance |
|----------|------------|--------------|-------------|
| **Neo4j Aura** | 1 hour | $7-72 | None |
| Neo4j on VM | 1 day | $102 | Medium |
| Full GKE | 1 week | $150+ | High |

**Recommendation**: Start with Neo4j Aura. It's cheaper, faster to setup, and we can always migrate to self-hosted later if needed.

## Next Action Items

1. **Immediate** (Do this next):
   - Sign up for Neo4j Aura free tier
   - Get connection string
   - Update deployer code to accept Aura connection

2. **Short-term** (This week):
   - Deploy new test instance with Aura
   - Test memory operations
   - Verify no timeouts

3. **Medium-term** (Next week):
   - Add chat wrapper endpoint
   - Test end-to-end conversation flow
   - Update playground to use chat endpoint

4. **Long-term** (Future):
   - Add capability indicators to dashboard
   - Support both managed and self-hosted options
   - Optimize for multi-tenant scale

## Files to Modify

1. `backend/app/services/memmachine_deployer.py`
   - Add `use_managed_neo4j` parameter
   - Skip Neo4j Cloud Run deployment if using Aura
   - Update env vars with proper connection strings

2. `backend/app/api/v1/endpoints/chat.py` (NEW)
   - Create chat wrapper endpoint
   - Integrate OpenAI + MemMachine

3. `frontend/app/playground/[id]/page.tsx`
   - Update to call `/v1/chat` endpoint
   - Already done! Just needs working backend

4. `backend/app/api/v1/endpoints/deployment.py`
   - Accept Neo4j connection string in deploy request
   - Or auto-provision Aura instance

## WE'RE SO CLOSE!

The infrastructure is there. The code is there. The frontend is there.

**We just need to connect Neo4j properly and we're DONE!** 🚀
