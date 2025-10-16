# Security Guidelines for MemCloud

## 🔒 Credential Management

### ❌ NEVER Commit These to Git

- API keys (OpenAI, etc.)
- Database passwords
- Service account keys (`.json`, `.pem`)
- Environment files with real credentials (`.env.production`, `.env.local`)
- Cloud provider credentials
- Neo4j Aura passwords
- Any file containing `sk-`, passwords, or tokens

### ✅ How to Handle Secrets

#### For Development (Local)
```bash
# Use .env files (git-ignored)
cp .env.template.txt backend/.env
# Edit with your local credentials
```

#### For Production (Cloud)

**GCP:**
```bash
# Store in Secret Manager
echo "your-secret" | gcloud secrets create SECRET_NAME --data-file=-

# Mount in Cloud Run
gcloud run services update SERVICE \
  --set-secrets="ENV_VAR=SECRET_NAME:latest"
```

**AWS:**
```bash
# Store in Secrets Manager
aws secretsmanager create-secret \
  --name SECRET_NAME \
  --secret-string "your-secret"

# Reference in ECS task definition
```

**Azure:**
```bash
# Store in Key Vault
az keyvault secret set \
  --vault-name VAULT_NAME \
  --name SECRET_NAME \
  --value "your-secret"

# Reference in Container Instance
```

---

## 🛡️ Security Checklist

### Before Committing Code

- [ ] Run `git status` and check for .env files
- [ ] Search for API keys: `grep -r "sk-" --include="*.py" --include="*.ts" .`
- [ ] Search for passwords: `grep -r "password.*=" --include="*.py" .`
- [ ] Verify .gitignore includes all secret files
- [ ] Check that only template files are committed

### Before Deploying

- [ ] Secrets stored in cloud provider's secret manager
- [ ] No hardcoded credentials in Dockerfiles
- [ ] Environment variables set via cloud console or CLI
- [ ] Service accounts have minimal required permissions
- [ ] Database allows connections only from known IPs or VPCs

### After Deployment

- [ ] Rotate any credentials that were accidentally exposed
- [ ] Enable audit logging
- [ ] Set up monitoring for unauthorized access
- [ ] Configure budget alerts to detect abuse

---

## 🔍 Security Audit

### Files That Are Safe to Commit

✅ `.env.template.txt` - Template only, no real values
✅ `backend/.env` - Development defaults only
✅ `backend/.env.production` - Templates with YOUR_* placeholders
✅ `frontend/.env.production` - Public URLs only (if no secrets)
✅ Deployment guides (use placeholder values)

### Files That Should NEVER Be Committed

❌ Any `.env` file with real credentials
❌ Service account JSON keys
❌ Files containing `sk-proj-` or real API keys
❌ Database connection strings with real passwords
❌ Cloud provider credential files

---

## 🚨 If Credentials Are Accidentally Committed

### Immediate Actions

1. **Rotate all compromised credentials immediately**
   ```bash
   # GCP
   gcloud secrets versions add SECRET_NAME --data-file=-

   # AWS
   aws secretsmanager rotate-secret --secret-id SECRET_NAME

   # Azure
   az keyvault secret set --vault-name VAULT --name SECRET --value NEW_VALUE
   ```

2. **Remove from Git history**
   ```bash
   # Use BFG Repo-Cleaner or git-filter-repo
   git filter-repo --path PATH_TO_SECRET --invert-paths
   ```

3. **Force push (if safe)**
   ```bash
   git push origin main --force
   ```

4. **Verify removal**
   ```bash
   # Check entire git history
   git log -p --all -- PATH_TO_FILE
   ```

5. **Update .gitignore** to prevent recurrence

---

## 🔐 Best Practices

### API Keys

- Use environment variables
- Rotate regularly (every 90 days)
- Use different keys for dev/staging/production
- Implement rate limiting
- Monitor usage for anomalies

### Database Credentials

- Use strong, random passwords (32+ characters)
- Store in secret managers
- Use least-privilege database users
- Enable SSL/TLS for connections
- Rotate passwords quarterly

### Cloud Provider Access

- Use service accounts with minimal permissions
- Enable MFA for all human accounts
- Use short-lived credentials when possible
- Audit access logs regularly
- Implement IP allow lists

### Neo4j Aura

- Use strong passwords (provided by Aura)
- Don't commit connection URIs with embedded passwords
- Use environment variables for credentials
- Enable audit logging in Aura console

---

## 📝 Environment Variable Template

### Backend (.env)

```bash
# Development Environment
ENVIRONMENT=development
DEBUG=True

# Database (use localhost for local dev)
DB_HOST=localhost
DB_NAME=memcloud_dev
DB_USER=postgres
DB_PASSWORD=dev_password_change_me
USE_CLOUD_SQL_CONNECTOR=False

# API
PORT=8000

# Security
SECRET_KEY=dev-secret-key-change-in-production
```

### Frontend (.env.local)

```bash
# Development Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
```

---

## 🎯 Production Deployment

### Environment Variables (Cloud Run / ECS / Container Instances)

Set these via cloud console or CLI, **NEVER** in code:

```bash
# Database
DB_HOST=your-db-host
DB_PASSWORD=from-secret-manager
DB_NAME=your-db-name

# Cloud Config
GCP_PROJECT_ID=your-project
GCP_REGION=us-central1

# Keys (from secret manager)
OPENAI_API_KEY=from-secret-manager
```

### Secrets Manager

Store these in your cloud provider's secret manager:

- `database-password`
- `openai-api-key`
- `neo4j-password` (if using self-hosted)
- `session-secret-key`

---

## ✅ Current Status

**Last Security Audit:** October 2025

**Findings:**
- ✅ All .env files sanitized with templates
- ✅ .gitignore comprehensive
- ✅ No hardcoded credentials in code
- ✅ Deployment guides use placeholder values
- ✅ Documentation includes security best practices

**Action Items:**
- ✅ Cleared production .env files
- ✅ Added comprehensive .gitignore
- ✅ Created security documentation
- ⏳ Verify no credentials in git history (user action required)

---

## 📞 Security Contact

If you discover a security vulnerability:

1. **DO NOT** create a public GitHub issue
2. Email security contact (if applicable)
3. Include details of the vulnerability
4. Allow 90 days for remediation before public disclosure

---

*Last Updated: October 2025*
*Version: 1.0*
