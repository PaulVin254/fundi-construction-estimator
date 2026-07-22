---
name: supabase_integration
description: Best practices for Supabase PostgreSQL database queries, authentication/session management, Row Level Security (RLS), and Supabase Storage bucket handling.
---

# Supabase Integration Skill

## Overview
This skill guides the agent when reading, writing, or refactoring Supabase database handlers (`utils/supabase_session_service.py`), SQL setup scripts (`SUPABASE_SETUP.sql`, `STORAGE_SETUP.sql`), and storage integrations.

## Core Directives
1. **Schema & Migration Alignment**: Check `SUPABASE_SETUP.sql` before altering table queries or adding columns.
2. **Session & Auth Management**: Use `SupabaseSessionService` for managing user sessions and state persistence instead of direct unauthenticated queries.
3. **Storage Buckets**: Refer to `STORAGE_SETUP.sql` for bucket names, policies, and public/private URL rules.
4. **Environment Variables**: Access keys via `os.getenv("SUPABASE_URL")` and `os.getenv("SUPABASE_KEY")` or `os.getenv("SUPABASE_SERVICE_ROLE_KEY")`.

## Verification Checklist
- [ ] Schema changes match `SUPABASE_SETUP.sql`.
- [ ] Error handling wraps all Supabase API network requests.
- [ ] Row Level Security (RLS) rules are respected.
