# =============================================================================
# Google Cloud Platform (GCP) Vertex AI Setup Script (PowerShell)
# Use this script to authenticate your $300 GCP Free Trial Account
# =============================================================================

Write-Host "Starting GCP Vertex AI Setup for Fundi Construction Estimator..." -ForegroundColor Cyan

# 1. Login to Google Cloud CLI
Write-Host "Step 1: Logging into Google Cloud Account..." -ForegroundColor Yellow
gcloud auth login

# 2. Get active or prompt for Project ID
$PROJECT_ID = (gcloud config get-value project 2>$null)

if (-not $PROJECT_ID -or $PROJECT_ID -eq "(unset)") {
    Write-Host "Available GCP Projects under your account:" -ForegroundColor Yellow
    gcloud projects list
    $PROJECT_ID = Read-Host "Enter your GCP Project ID"
    gcloud config set project $PROJECT_ID
} else {
    Write-Host "Using active GCP Project: $PROJECT_ID" -ForegroundColor Green
}

# 3. Enable Vertex AI API
Write-Host "Step 2: Enabling Vertex AI API (aiplatform.googleapis.com)..." -ForegroundColor Yellow
gcloud services enable aiplatform.googleapis.com

# 4. Authenticate Application Default Credentials (ADC)
Write-Host "Step 3: Setting up Application Default Credentials (ADC)..." -ForegroundColor Yellow
gcloud auth application-default login

Write-Host "=============================================================================" -ForegroundColor Cyan
Write-Host "GCP Vertex AI Setup Complete!" -ForegroundColor Green
Write-Host "Project ID: $PROJECT_ID" -ForegroundColor White
Write-Host "Region: us-central1" -ForegroundColor White
Write-Host "Make sure GOOGLE_CLOUD_PROJECT in your .env file matches: $PROJECT_ID" -ForegroundColor Yellow
Write-Host "=============================================================================" -ForegroundColor Cyan
