-- =============================================================================
-- Supabase Storage Setup for Estimates
-- =============================================================================
-- Run this in your Supabase SQL Editor to configure the storage bucket.

-- 1. Create the 'estimates' bucket if it doesn't exist
INSERT INTO storage.buckets (id, name, public)
VALUES ('estimates', 'estimates', true)
ON CONFLICT (id) DO NOTHING;

-- Note: We removed 'ALTER TABLE storage.objects ENABLE ROW LEVEL SECURITY' 
-- because it causes permission errors (42501) and RLS is enabled by default on storage.

-- 2. Create Policy: Allow Public Read Access (so n8n and users can download)
-- We drop the policy first to avoid "policy already exists" errors if re-running
DROP POLICY IF EXISTS "Public Access Estimates" ON storage.objects;

CREATE POLICY "Public Access Estimates"
ON storage.objects FOR SELECT
USING ( bucket_id = 'estimates' );

-- 3. Create Policy: Allow Anon Uploads (for the agent/script to upload without service key)
DROP POLICY IF EXISTS "Anon Upload Estimates" ON storage.objects;

CREATE POLICY "Anon Upload Estimates"
ON storage.objects FOR INSERT
WITH CHECK ( bucket_id = 'estimates' );
