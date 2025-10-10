# MemCloud Backend Deployment Script for Cloud Run
# Production Forcing Framework Compliant

param(
    [string]$Environment = "production",
    [string]$ProjectId = "memmachine-cloud",
    [string]$Region = "us-central1",
    [string]$ServiceName = "memcloud-api"
)

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  MemCloud Backend Deployment" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Environment: $Environment" -ForegroundColor Green
Write-Host "Project: $ProjectId" -ForegroundColor Green
Write-Host "Region: $Region" -ForegroundColor Green
Write-Host "Service: $ServiceName" -ForegroundColor Green
Write-Host ""

# Step 1: Set project
Write-Host "[1/6] Setting GCP project..." -ForegroundColor Yellow
gcloud config set project $ProjectId

# Step 2: Build container image
Write-Host "[2/6] Building container image..." -ForegroundColor Yellow
$ImageName = "gcr.io/$ProjectId/$ServiceName"
gcloud builds submit --tag $ImageName ..\backend

if ($LASTEXITCODE -ne 0) {
    Write-Host "Build failed!" -ForegroundColor Red
    exit 1
}

# Step 3: Deploy to Cloud Run
Write-Host "[3/6] Deploying to Cloud Run..." -ForegroundColor Yellow

gcloud run deploy $ServiceName `
    --image $ImageName `
    --region $Region `
    --platform managed `
    --allow-unauthenticated `
    --set-env-vars "ENVIRONMENT=$Environment,GCP_PROJECT_ID=$ProjectId" `
    --set-cloudsql-instances "memmachine-cloud:us-central1:memmachine-db" `
    --memory 512Mi `
    --cpu 1 `
    --min-instances 0 `
    --max-instances 10 `
    --timeout 300 `
    --concurrency 80 `
    --port 8080

if ($LASTEXITCODE -ne 0) {
    Write-Host "Deployment failed!" -ForegroundColor Red
    exit 1
}

# Step 4: Get service URL
Write-Host "[4/6] Getting service URL..." -ForegroundColor Yellow
$ServiceUrl = gcloud run services describe $ServiceName --region $Region --format "value(status.url)"

Write-Host ""
Write-Host "Service URL: $ServiceUrl" -ForegroundColor Green

# Step 5: Health check
Write-Host "[5/6] Running health check..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

try {
    $Response = Invoke-WebRequest -Uri "$ServiceUrl/health" -UseBasicParsing
    Write-Host "Health check passed!" -ForegroundColor Green
    Write-Host "Status: $($Response.StatusCode)" -ForegroundColor Green
} catch {
    Write-Host "Health check failed!" -ForegroundColor Red
    Write-Host "Error: $_" -ForegroundColor Red
}

# Step 6: Summary
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Deployment Complete!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Service URL: $ServiceUrl" -ForegroundColor Green
Write-Host "API Docs: $ServiceUrl/docs" -ForegroundColor Green
Write-Host "Health Check: $ServiceUrl/health" -ForegroundColor Green
Write-Host ""
Write-Host "View logs:" -ForegroundColor Yellow
Write-Host "  gcloud run services logs read $ServiceName --region $Region" -ForegroundColor White
Write-Host ""
