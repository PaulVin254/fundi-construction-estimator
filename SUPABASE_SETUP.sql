-- =============================================================================
-- Supabase Session Storage Table Creation
-- =============================================================================
-- This SQL creates the table needed for Supabase persistent session storage.
-- Copy and paste this into your Supabase SQL Editor to create the table.
-- 
-- Steps:
-- 1. Go to https://app.supabase.com/
-- 2. Select your project
-- 3. Go to SQL Editor
-- 4. Click "New Query" 
-- 5. Copy and paste the SQL below
-- 6. Click "Run"
-- =============================================================================

CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    app_name TEXT NOT NULL,
    user_id TEXT NOT NULL,
    user_name TEXT,
    user_email TEXT,
    user_phone TEXT,
    history JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_app_name ON sessions(app_name);

-- Enable Row Level Security (optional - for production)
-- ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;

-- Grant access to anon role (required for Supabase)
GRANT SELECT, INSERT, UPDATE, DELETE ON sessions TO anon;

-- Create a function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create a trigger to call the function
CREATE TRIGGER update_sessions_updated_at BEFORE UPDATE ON sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- Supabase Material Prices Cache Table
-- =============================================================================
CREATE TABLE IF NOT EXISTS material_prices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    material_key TEXT UNIQUE NOT NULL,
    material_name TEXT NOT NULL,
    unit TEXT NOT NULL,
    category TEXT NOT NULL,
    price_nairobi NUMERIC NOT NULL,
    price_mombasa NUMERIC NOT NULL,
    price_upcountry NUMERIC NOT NULL,
    source TEXT NOT NULL DEFAULT 'baseline_qs',
    last_verified_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_material_prices_key ON material_prices(material_key);
CREATE INDEX IF NOT EXISTS idx_material_prices_category ON material_prices(category);

GRANT SELECT, INSERT, UPDATE, DELETE ON material_prices TO anon;

CREATE TRIGGER update_material_prices_updated_at BEFORE UPDATE ON material_prices
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

