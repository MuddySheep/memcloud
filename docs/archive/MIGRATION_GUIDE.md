# Database Migration Guide - Multi-Tenant Resource Tracking

**Date:** 2025-10-14
**Migration:** `001_multi_tenant` - Add multi-tenant resource tracking fields
**Status:** ✅ Ready to Apply

---

## 📋 What This Migration Does

Adds 11 new fields to the `instances` table to track per-user isolated resources:

### Neo4j Configuration (4 fields)
- `neo4j_service_name` - Cloud Run service name for Neo4j
- `neo4j_url` - HTTP URL for Neo4j
- `neo4j_bolt_url` - Bolt protocol URL for Neo4j connections
- `neo4j_secret_name` - Secret Manager reference for Neo4j password

### PostgreSQL Configuration (6 fields)
- `postgres_instance_name` - Cloud SQL instance name
- `postgres_ip` - Public IP address
- `postgres_connection_name` - Full connection string (project:region:instance)
- `postgres_secret_name` - Secret Manager reference for PostgreSQL password
- `postgres_database` - Database name (default: "memmachine")
- `postgres_user` - PostgreSQL username (default: "postgres")

### OpenAI Configuration (1 field)
- `openai_secret_name` - Secret Manager reference for user's OpenAI API key

---

## 🚀 How to Run the Migration

### Option 1: Using the Helper Script (Recommended)

```bash
cd backend
python migrate.py upgrade
```

**Output:**
```
🚀 Applying database migrations...
INFO  [alembic.runtime.migration] Running upgrade  -> 001_multi_tenant, add multi-tenant resource tracking
✅ Migrations applied successfully!
```

### Option 2: Using Alembic Directly

```bash
cd backend
python -m alembic upgrade head
```

### Option 3: Check Current Status First

```bash
cd backend
python migrate.py current    # Show current database version
python migrate.py history    # Show all available migrations
```

---

## 📊 Migration Details

**Migration File:** `backend/alembic/versions/001_add_multi_tenant_resource_tracking.py`

**Revision ID:** `001_multi_tenant`
**Down Revision:** `None` (first migration)

**SQL Operations:**
```sql
-- Add Neo4j fields
ALTER TABLE instances ADD COLUMN neo4j_service_name VARCHAR(255);
ALTER TABLE instances ADD COLUMN neo4j_url VARCHAR(512);
ALTER TABLE instances ADD COLUMN neo4j_bolt_url VARCHAR(512);
ALTER TABLE instances ADD COLUMN neo4j_secret_name VARCHAR(255);

-- Add PostgreSQL fields
ALTER TABLE instances ADD COLUMN postgres_instance_name VARCHAR(255);
ALTER TABLE instances ADD COLUMN postgres_ip VARCHAR(50);
ALTER TABLE instances ADD COLUMN postgres_connection_name VARCHAR(512);
ALTER TABLE instances ADD COLUMN postgres_secret_name VARCHAR(255);
ALTER TABLE instances ADD COLUMN postgres_database VARCHAR(100) DEFAULT 'memmachine' NOT NULL;
ALTER TABLE instances ADD COLUMN postgres_user VARCHAR(100) DEFAULT 'postgres' NOT NULL;

-- Add OpenAI field
ALTER TABLE instances ADD COLUMN openai_secret_name VARCHAR(255);
```

---

## ⚠️ Pre-Migration Checklist

Before running the migration:

1. **✅ Backup Database (CRITICAL!)**
   ```bash
   # For Cloud SQL PostgreSQL
   gcloud sql export sql memcloud-postgres \
     gs://memmachine-cloud-backups/pre-migration-$(date +%Y%m%d-%H%M%S).sql \
     --database=memmachine \
     --project=memmachine-cloud
   ```

2. **✅ Check Database Connection**
   ```bash
   cd backend
   python -c "from app.db.database import check_db_health; import asyncio; print(asyncio.run(check_db_health()))"
   ```

3. **✅ Verify Alembic Setup**
   ```bash
   cd backend
   python migrate.py history
   ```

4. **✅ Stop Application (if running in production)**
   ```bash
   # Stop Cloud Run services temporarily
   gcloud run services update memcloud-api --max-instances=0 --region=us-central1
   ```

---

## ✅ Post-Migration Verification

After running the migration, verify it succeeded:

### 1. Check Migration Status
```bash
cd backend
python migrate.py current
```

**Expected Output:**
```
001_multi_tenant (head)
```

### 2. Verify New Columns Exist
```sql
-- Connect to database
psql -h [DB_HOST] -U [DB_USER] -d memmachine

-- Check columns
\d instances

-- Should see all 11 new columns:
-- neo4j_service_name, neo4j_url, neo4j_bolt_url, neo4j_secret_name
-- postgres_instance_name, postgres_ip, postgres_connection_name, postgres_secret_name
-- postgres_database, postgres_user, openai_secret_name
```

### 3. Test Application Startup
```bash
cd backend
python -m app.main
```

**Expected:** No errors, application starts successfully

### 4. Test Deployment Endpoint
```bash
curl -X POST http://localhost:8000/api/v1/deployment/deploy \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Instance",
    "openai_api_key": "sk-test-...",
    "user_id": "test-user-123"
  }'
```

**Expected:** Deployment starts, instance record created with new fields

---

## 🔄 Rollback (If Needed)

If something goes wrong, you can rollback:

```bash
cd backend
python migrate.py downgrade
```

This will remove all 11 new columns from the `instances` table.

**⚠️ WARNING:** Rolling back will **DELETE** all data in the new columns!

---

## 🐛 Troubleshooting

### Error: "alembic: command not found"

**Solution:** Use python -m:
```bash
python -m alembic upgrade head
```

### Error: "Can't locate revision identified by '001_multi_tenant'"

**Solution:** Check migration file exists:
```bash
ls backend/alembic/versions/
```

Should see: `001_add_multi_tenant_resource_tracking.py`

### Error: "column already exists"

**Cause:** Migration already applied or columns added manually

**Solution:** Mark migration as complete without running it:
```bash
cd backend
python -m alembic stamp 001_multi_tenant
```

### Error: "asyncpg.exceptions._base.InternalClientError"

**Cause:** Database connection issue

**Solutions:**
1. Check `.env` file has correct database credentials
2. Ensure database is accessible from your location
3. For Cloud SQL, enable Cloud SQL Admin API
4. Check firewall rules allow your IP

---

## 📦 Files Created/Modified

**New Files:**
- `backend/alembic.ini` - Alembic configuration
- `backend/alembic/env.py` - Alembic environment setup
- `backend/alembic/script.py.mako` - Migration template
- `backend/alembic/versions/001_add_multi_tenant_resource_tracking.py` - Migration script
- `backend/migrate.py` - Helper script for running migrations

**Modified Files:**
- `backend/app/models/instance.py` - Added 11 new fields

---

## 🎯 Next Steps After Migration

Once migration is complete:

1. **✅ Restart Application**
   ```bash
   # If stopped for migration
   gcloud run services update memcloud-api --max-instances=10 --region=us-central1
   ```

2. **✅ Update Frontend** (Phase 3)
   - Connect dashboard to deployment API
   - Update playground to use user-specific instances

3. **✅ Deploy to Production**
   ```bash
   cd backend
   gcloud builds submit --config=cloudbuild.yaml .
   gcloud run deploy memcloud-api --image=gcr.io/memmachine-cloud/memcloud-api:latest
   ```

4. **✅ Monitor Logs**
   ```bash
   gcloud run services logs read memcloud-api --limit=100
   ```

---

## 💡 Migration Best Practices

1. **Always backup before migrating** ✅
2. **Test migrations in development first** ✅
3. **Run migrations during low-traffic periods**
4. **Have rollback plan ready**
5. **Monitor application after migration**
6. **Document any issues encountered**

---

## 📞 Need Help?

- Check `MULTI_TENANT_IMPLEMENTATION_STATUS.md` for architecture details
- Check `MULTI_TENANT_PLAN.md` for original implementation plan
- Review migration logs: `backend/alembic.log` (if exists)

---

**✅ Migration is ready to apply!**

Run: `cd backend && python migrate.py upgrade`
