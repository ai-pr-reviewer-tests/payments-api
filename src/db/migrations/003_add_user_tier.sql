-- Add user_tier column to users table
-- Applied: 2025-03-25

-- BUG: NOT NULL without DEFAULT will fail on non-empty tables
-- PostgreSQL will reject this if the users table has any existing rows
ALTER TABLE users ADD COLUMN user_tier VARCHAR(20) NOT NULL;

-- Update queries to include user_tier
-- NOTE: No rollback migration provided
