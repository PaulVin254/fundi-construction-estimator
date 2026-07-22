#!/usr/bin/env bash
# =============================================================================
# Google Cloud Platform (GCP) Vertex AI Setup Script
# Use this script to authenticate your $300 GCP Free Trial Account
# =============================================================================

set -e

echo "🚀 Starting GCP Vertex AI Setup for Fundi Construction Estimator..."

# 1. Login to Google Cloud CLI (Make sure to select the email with the $300 credit)
echo "🔑 Step 1: Logging into Google Cloud Account..."
gcloud auth login

# 2. Get active or prompt for Project ID
PROJECT_ID=$(gcloud config get-value project 2>/dev/null)

if [ -z "$PROJECT_ID" ] || [ "$PROJECT_ID" == "(unset)" ]; then
    echo "📋 Available GCP Projects under your account:"
    gcloud projects list
    read -p "👉 Enter your GCP Project ID (from $300 trial account): " PROJECT_ID
    gcloud config set project "$PROJECT_ID"
else
    echo "✅ Using active GCP Project: $PROJECT_ID"
fi

# 3. Enable Vertex AI API
echo "⚡ Step 2: Enabling Vertex AI API (aiplatform.googleapis.com)..."
gcloud services enable aiplatform.googleapis.com

# 4. Authenticate Application Default Credentials (ADC)
echo "🔐 Step 3: Setting up Application Default Credentials (ADC)..."
gcloud auth application-default login

echo "============================================================================="
echo "🎉 GCP Vertex AI Setup Complete!"
echo "Project ID: $PROJECT_ID"
echo "Region: us-central1"
echo "Make sure GOOGLE_CLOUD_PROJECT in your .env file matches: $PROJECT_ID"
echo "============================================================================="
