-- Add user_tier column to users table
-- Applied: 2025-03-25

ALTER TABLE users ADD COLUMN user_tier VARCHAR(20) NOT NULL;

-- Update queries to include user_tier
-- NOTE: No rollback migration provided
