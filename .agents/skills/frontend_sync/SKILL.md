---
name: frontend_sync
description: |
  Frontend synchronization and CI/CD verification skill for Fundi Construction Estimator.
  Automatically maps backend API changes (main.py, estimate schemas) to the React + Vite frontend
  (ironclad-construction-ai), runs TypeScript & build checks, pushes to GitHub, and handles deployment rollbacks.
---

# Frontend Synchronization & CI/CD Skill

## Overview
This skill provides instructions for automatically synchronizing backend API changes (in `main.py`, `estimate_delivery.py`, or Pydantic models) with the connected **React + Vite + TypeScript frontend** located at:
`C:\Users\user\Desktop\Website Information\Paul Personal Portfolio\ironclad-construction-ai`

---

## Core Directives

### 1. Backend-to-Frontend API Contract Mapping
Whenever API routes (`/api/consult-fundi`, `/api/generate-estimate`), estimate payload structures (`<ESTIMATE_DATA>`), or dynamic tools change:
* **Typescript Interfaces**: Update TypeScript types inside `src/types/` in `ironclad-construction-ai`.
* **API Fetch Clients**: Verify fetch payloads, request headers, and response parsing.
* **UI Components**: Update React calculator components (`src/components/Calculator.tsx` or `src/components/EstimateReport.tsx`).

---

### 2. Rigorous Local Verification Suite
Before committing any frontend modifications:
1. Navigate to the frontend directory:
   ```bash
   cd "C:\Users\user\Desktop\Website Information\Paul Personal Portfolio\ironclad-construction-ai"
   ```
2. Run TypeScript type checking:
   ```bash
   npx tsc --noEmit
   ```
3. Run Vite production build:
   ```bash
   npm run build
   ```
*If any build or type error occurs, HALT immediately and fix the issue before committing.*

---

### 3. Git Commit & Push Protocol
Once verification passes:
1. Stage modified frontend files:
   ```bash
   git add src/
   ```
2. Commit with conventional commit message:
   ```bash
   git commit -m "feat(frontend): sync API contract changes from backend agent"
   ```
3. Push to `main` branch to trigger Azure Blob Storage deployment workflow:
   ```bash
   git push origin main
   ```

---

### 4. Deployment Monitoring & Automated Rollback
1. Monitor GitHub Actions workflow status:
   ```bash
   git log -n 1
   ```
2. **Automated Rollback Safeguard**:
   If the GitHub Actions build fails or Azure Blob upload fails:
   ```bash
   git revert HEAD --no-edit
   git push origin main
   ```
   *This ensures live production on Azure Blob Storage (`stfundiestimatorweb`) never stays broken.*
