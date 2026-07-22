---
name: gcp_migration
description: Guidance for migrating web app features, backend services, database handlers, and APIs to Google Cloud Platform (GCP) using Google Developer Knowledge MCP tools.
---

# GCP Migration & Knowledge Verification Skill

## Overview
This skill guides the agent when planning, building, refactoring, or deploying features onto **Google Cloud Platform (GCP)** (such as Cloud Run, Cloud Functions, Cloud SQL, Firestore, and IAM).

## MANDATORY MCP PRE-FLIGHT CHECK
Before writing GCP architecture plans, deployment scripts (`gcloud`, Dockerfiles, Terraform), or API integration code:
1. **Query Google Developer Knowledge MCP**: Call the `google-developer-knowledge` MCP server (`search_documents` or `answer_query`) for up-to-date documentation on the relevant GCP service.
2. **Verify API Schemas & Best Practices**: Check for breaking changes, modern SDK patterns (e.g., Python `google-cloud-*` SDKs), and current IAM security practices.
3. **Zero Hallucination Policy**: Never invent `gcloud` flags or SDK function signatures from memory when they can be verified via the MCP tool.

## Core Migration Areas
- **Cloud Run / Containerization**: Packaging Python / web backends into lightweight Docker containers for serverless execution.
- **Cloud Functions / Event Triggers**: Migrating serverless API endpoints and webhook triggers.
- **Database & Storage**: Connecting to Managed PostgreSQL / Cloud SQL / Firestore and Cloud Storage buckets.
- **Environment & Secrets**: Using GCP Secret Manager instead of raw `.env` files in production.

## Verification Checklist
- [ ] Searched official Google docs via MCP for target service.
- [ ] Confirmed authentication & IAM setup (Service Accounts / Application Default Credentials).
- [ ] Provided clean, verified deployment commands and code snippets.
