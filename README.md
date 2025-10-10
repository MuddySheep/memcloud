# 🌥️ MemCloud - MemMachine-in-a-Box for GCP

> One-click MemMachine deployments to Google Cloud Platform

**Built for the [Memories That Last Hackathon](https://lu.ma/memoriesthatlast)**

---

## 🚀 What is MemCloud?

MemCloud is a deployment platform that makes it ridiculously easy to deploy [MemMachine](https://github.com/MemMachine/MemMachine) instances to Google Cloud Platform. No DevOps knowledge required - just enter your OpenAI API key and click deploy.

### ✨ Features

- **60-Second Deployments** - From click to running instance in under a minute
- **Fully Managed** - Cloud SQL (PostgreSQL + pgvector), Neo4j, and MemMachine automatically configured
- **Production-Ready** - Auto-scaling, health checks, monitoring, and backups included
- **Cost-Effective** - Scale to zero when idle, pay only for what you use

---

## 🏗️ Architecture

MemCloud deploys three core components to GCP:

1. **Cloud SQL (PostgreSQL 15)** - Profile memory storage with pgvector extension
2. **Neo4j on Cloud Run** - Graph-based episodic memory
3. **MemMachine on Cloud Run** - The main memory service

All connected and configured automatically using the Cloud SQL Connector and service mesh.

---

## 🌐 Live Demo

- **Frontend**: https://memcloud-frontend-576223366889.us-central1.run.app
- **Backend API**: https://memcloud-api-576223366889.us-central1.run.app
- **API Docs**: https://memcloud-api-576223366889.us-central1.run.app/docs

---

## 🛠️ Tech Stack

### Backend
- **FastAPI** - Modern async Python web framework
- **SQLAlchemy** - ORM with async support
- **Cloud SQL Connector** - Secure database connections
- **Structlog** - Structured JSON logging
- **Pydantic** - Data validation and settings

### Frontend
- **Next.js 14** - React framework with App Router
- **Tailwind CSS** - Utility-first CSS
- **TypeScript** - Type-safe JavaScript
- **Lucide Icons** - Beautiful icon set

### Infrastructure
- **Cloud Run** - Serverless container platform
- **Cloud SQL** - Managed PostgreSQL
- **Secret Manager** - Secure credential storage
- **Cloud Build** - Automated Docker builds

---

## 📁 Project Structure

```
Memcloud/
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── api/v1/         # API endpoints
│   │   ├── core/           # Configuration
│   │   ├── db/             # Database connection
│   │   ├── models/         # SQLAlchemy models
│   │   └── services/       # Business logic
│   ├── Dockerfile          # Backend container
│   └── requirements.txt
│
├── frontend/               # Next.js frontend
│   ├── app/               # App router pages
│   ├── components/        # React components
│   ├── lib/              # Utilities
│   ├── Dockerfile        # Frontend container
│   └── package.json
│
└── memmachine-source/    # Original MemMachine source
```

---

## 🚀 Getting Started

### Prerequisites
- Google Cloud Platform account
- `gcloud` CLI installed
- Docker installed (for local development)

### Local Development

1. **Backend Setup**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
uvicorn app.main:app --reload
```

2. **Frontend Setup**
```bash
cd frontend
npm install
npm run dev
```

3. **Access**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Deploy to GCP

1. **Configure GCP**
```bash
gcloud config set project YOUR_PROJECT_ID
gcloud auth login
```

2. **Deploy Backend**
```bash
cd backend
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/memcloud-api
gcloud run deploy memcloud-api --image gcr.io/YOUR_PROJECT_ID/memcloud-api --region us-central1
```

3. **Deploy Frontend**
```bash
cd frontend
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/memcloud-frontend
gcloud run deploy memcloud-frontend --image gcr.io/YOUR_PROJECT_ID/memcloud-frontend --region us-central1
```

---

## 🎯 How It Works

1. **User clicks "Deploy"** on the dashboard
2. **Backend receives request** with instance name and OpenAI API key
3. **Orchestrator deploys**:
   - Creates Cloud SQL instance
   - Deploys Neo4j to Cloud Run
   - Deploys MemMachine to Cloud Run
   - Configures networking and secrets
4. **User receives URL** to their running MemMachine instance

---

## 🔒 Security

- All secrets stored in GCP Secret Manager
- Non-root Docker containers
- CORS properly configured
- Database connections via Cloud SQL Connector
- IAM-based access control

---

## 📊 Production Forcing Framework (PFF)

This project follows PFF principles:

- ✅ **Structured Logging** - JSON logs with request IDs
- ✅ **Health Checks** - Liveness and readiness probes
- ✅ **Error Handling** - Graceful degradation
- ✅ **Auto-scaling** - Scale to zero when idle
- ✅ **Security** - Secrets management and non-root containers
- ✅ **Monitoring** - Cloud Logging integration

---

## 🤝 Contributing

This project was built for the Memories That Last Hackathon. Feel free to fork and adapt for your own use!

---

## 📄 License

MIT License - see LICENSE file for details

---

## 🙏 Acknowledgments

- [MemMachine](https://github.com/MemMachine/MemMachine) - The amazing memory system we're deploying
- [Anthropic](https://anthropic.com) - For Claude and the hackathon
- Google Cloud Platform - For the infrastructure

---

## 📧 Contact

Built with ❤️ by [@MuddySheep](https://github.com/MuddySheep)

For questions or issues, please open an issue on GitHub.

---

**🎊 MemCloud - Making MemMachine deployment effortless! 🎊**
