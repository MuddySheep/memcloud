# MemCloud Directory Structure
## Clean, Organized, Production-Ready

**Last Updated:** October 2025

---

## 📂 Root Directory

```
memcloud/
├── README.md                          ← Original project README
├── README_DEPLOYMENT.md               ← **START HERE** - Deployment overview
├── DEPLOYMENT_MASTER_INDEX.md         ← Cloud comparison & decision guide
├── DEPLOY_GCP.md                      ← Google Cloud Platform deployment
├── DEPLOY_AWS.md                      ← Amazon Web Services deployment
├── DEPLOY_AZURE.md                    ← Microsoft Azure deployment
├── TROUBLESHOOTING_RUNBOOK.md         ← Error reference (25+ issues)
├── .gitignore                         ← Git ignore rules
├── backend/                           ← FastAPI backend service
├── frontend/                          ← Next.js frontend dashboard
├── memmachine-docker/                 ← Custom MemMachine Docker image
├── scripts/                           ← Utility scripts
└── docs/                              ← Documentation and archives
    ├── archive/                       ← Legacy docs and old code
    └── screenshots/                   ← UI screenshots
```

---

## 🎯 Quick Navigation

### For First-Time Users
1. **Read:** `README_DEPLOYMENT.md` (overview)
2. **Decide:** `DEPLOYMENT_MASTER_INDEX.md` (pick your cloud)
3. **Deploy:** `DEPLOY_GCP.md` or `DEPLOY_AWS.md` or `DEPLOY_AZURE.md`
4. **Troubleshoot:** `TROUBLESHOOTING_RUNBOOK.md` (if needed)

### For Engineers
- **Backend code:** `backend/`
- **Frontend code:** `frontend/`
- **Custom image:** `memmachine-docker/`
- **Deployment scripts:** `scripts/`

### For Reference
- **Old docs:** `docs/archive/`
- **Screenshots:** `docs/screenshots/`

---

## 📁 Detailed Structure

### `/backend/` - FastAPI Backend Service

```
backend/
├── Dockerfile                         ← Backend container image
├── requirements.txt                   ← Python dependencies
├── alembic/                           ← Database migrations
│   ├── env.py
│   └── versions/
├── app/
│   ├── main.py                        ← FastAPI application entry
│   ├── api/
│   │   └── v1/
│   │       ├── api.py                 ← API router
│   │       └── endpoints/
│   │           ├── deployment.py      ← Deployment orchestration
│   │           ├── instances.py       ← Instance management
│   │           └── playground.py      ← Testing endpoint
│   ├── core/
│   │   └── config.py                  ← Configuration management
│   ├── db/
│   │   └── database.py                ← Database connection (PUBLIC IP fix)
│   ├── models/
│   │   └── instance.py                ← SQLAlchemy models
│   ├── schemas/
│   │   └── deployment.py              ← Pydantic schemas
│   └── services/
│       ├── memmachine_deployer.py     ← Core deployment logic (Neo4j Aura)
│       └── config_template.yml        ← MemMachine config template
└── tests/
    └── test_deployment.py             ← Unit tests
```

**Key Features:**
- ✅ Neo4j Aura integration (NEW)
- ✅ PUBLIC IP database support (NEW)
- ✅ Multi-cloud deployment logic
- ✅ Async FastAPI with SQLAlchemy

---

### `/frontend/` - Next.js Dashboard

```
frontend/
├── Dockerfile                         ← Frontend container image
├── package.json                       ← Node.js dependencies
├── next.config.js                     ← Next.js configuration
├── app/
│   ├── page.tsx                       ← Landing page
│   ├── dashboard/
│   │   └── page.tsx                   ← Main dashboard
│   ├── playground/
│   │   └── page.tsx                   ← Testing interface
│   └── layout.tsx                     ← Root layout
├── components/
│   ├── deployment-form.tsx            ← Deploy new instance
│   ├── instance-list.tsx              ← List of instances
│   └── instance-card.tsx              ← Instance status card
└── lib/
    └── api.ts                         ← Backend API client
```

**Key Features:**
- ✅ Real-time deployment status
- ✅ Neo4j Aura credential input
- ✅ Instance management UI
- ✅ Responsive design

---

### `/memmachine-docker/` - Custom MemMachine Image

```
memmachine-docker/
├── Dockerfile                         ← Custom image with psycopg2 fix
├── startup.sh                         ← Container startup script
└── README.md                          ← Build instructions
```

**Critical Fix:**
```dockerfile
# Install psycopg2 to EXACT location where MemMachine expects it
RUN /usr/local/bin/python3 -m pip install --no-cache-dir \
    --target=/app/.venv/lib/python3.12/site-packages \
    psycopg2-binary
```

**Purpose:**
- Adds PostgreSQL support to MemMachine
- Generates configuration from environment variables
- Works on GCP, AWS, and Azure

---

### `/docs/archive/` - Legacy Documentation

```
docs/archive/
├── DOCUMENTATION_INDEX.md             ← Old documentation index
├── GCP_FIRST_TIME_SETUP.md            ← Detailed GCP setup (reference)
├── MEMMACHINE_CLOUD_DEPLOYMENT_GUIDE.md ← Original guide (psycopg2 discovery)
├── MIGRATION_GUIDE.md                 ← Old migration notes
├── MULTI_TENANT_PLAN.md               ← Old multi-tenant planning
├── WORKING_DEPLOYMENT_PLAN.md         ← Old deployment plan
├── helm/                              ← Kubernetes Helm charts (unused)
├── terraform/                         ← Terraform configs (unused)
├── neo4j-cloudrun/                    ← Old Neo4j Cloud Run (replaced by Aura)
├── memmachine-source/                 ← MemMachine source exploration
└── MemMachine/                        ← Old MemMachine experiments
```

**When to use:**
- Reference for original psycopg2 discovery process
- Detailed GCP project setup
- Historical context

---

### `/docs/screenshots/` - UI Screenshots

```
docs/screenshots/
├── Dashboardlatest.PNG
├── Memcloud Deploy.PNG
├── Memcloud Hero.PNG
├── Memcloud Landing.PNG
├── Playground1.PNG
├── Remove Failed.PNG
└── Setup Visualization.PNG
```

---

## 🚀 Deployment Guides at Root

### Primary Guides (Copy-Paste Ready)

| File | Cloud | Time | Cost | Purpose |
|------|-------|------|------|---------|
| `DEPLOY_GCP.md` | Google Cloud | ~20 min | $15-30/mo | Easiest, cheapest |
| `DEPLOY_AWS.md` | Amazon Web Services | ~25 min | $45-65/mo | Enterprise, compliance |
| `DEPLOY_AZURE.md` | Microsoft Azure | ~20 min | $30-55/mo | Microsoft ecosystem |

**All guides include:**
- ✅ Prerequisites checklist
- ✅ Step-by-step commands
- ✅ Verification at each stage
- ✅ Troubleshooting section
- ✅ Production checklist

### Support Guides

| File | Purpose |
|------|---------|
| `DEPLOYMENT_MASTER_INDEX.md` | Cloud comparison, decision guide |
| `TROUBLESHOOTING_RUNBOOK.md` | 25+ errors with solutions |
| `README_DEPLOYMENT.md` | Quick start, overview |

---

## 📊 File Count Summary

| Category | Count |
|----------|-------|
| **Deployment Guides** | 5 (GCP, AWS, Azure, Master Index, README) |
| **Backend Files** | ~30 (Python, Docker, configs) |
| **Frontend Files** | ~20 (TypeScript, React, Next.js) |
| **Docker Templates** | 3 (Dockerfile, startup.sh, README) |
| **Archive Docs** | 10+ (legacy reference) |
| **Total Lines** | ~15,000+ (documentation + code) |

---

## 🎯 What's Where?

### Want to deploy?
→ Root directory deployment guides

### Want to modify code?
→ `backend/` or `frontend/` directories

### Want to build custom image?
→ `memmachine-docker/` directory

### Need historical context?
→ `docs/archive/` directory

### Looking for UI screenshots?
→ `docs/screenshots/` directory

---

## 🧹 What We Cleaned Up

**Moved to `docs/archive/`:**
- ❌ Old markdown files (MIGRATION_GUIDE, MULTI_TENANT_PLAN, etc.)
- ❌ Unused Helm charts
- ❌ Unused Terraform configs
- ❌ Old Neo4j Cloud Run experiments
- ❌ Legacy code explorations

**Moved to `docs/screenshots/`:**
- ❌ All PNG/screenshot files from root

**Kept at root:**
- ✅ Primary deployment guides (DEPLOY_*.md)
- ✅ README and master index
- ✅ Troubleshooting guide
- ✅ Active code directories (backend, frontend, memmachine-docker)

---

## ✅ Verification

### Root Directory Should Have:
- [ ] 5 deployment guides (DEPLOY_GCP/AWS/AZURE, MASTER_INDEX, README_DEPLOYMENT)
- [ ] 1 troubleshooting guide
- [ ] 1 original README
- [ ] 3 code directories (backend, frontend, memmachine-docker)
- [ ] 1 docs directory
- [ ] 1 scripts directory
- [ ] NO random PNG files
- [ ] NO old/legacy markdown files

### All Checks Passed? ✅

---

## 🎉 Result

**Clean, organized, production-ready repository structure.**

Engineers can now:
1. **Quickly find** what they need
2. **Deploy fast** with clear guides
3. **Modify code** in organized directories
4. **Reference history** in archives

**This is GitHub best practices implemented correctly.**

---

*Document Version: 1.0*
*Created: October 2025*
*Status: Clean ✅*
