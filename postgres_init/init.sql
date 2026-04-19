-- ══════════════════════════════════════════════════
-- AI Platform - PostgreSQL Initialization
-- ══════════════════════════════════════════════════

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Processing tasks table (shared between Django + FastAPI)
CREATE TABLE IF NOT EXISTS processing_tasks (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id       INTEGER NOT NULL,
    filename      VARCHAR(255) NOT NULL,
    file_size     BIGINT,
    status        VARCHAR(20) DEFAULT 'pending'
                    CHECK (status IN ('pending','processing','completed','failed')),
    task_type     VARCHAR(50) DEFAULT 'summarize',
    result        TEXT,
    error_message TEXT,
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    updated_at    TIMESTAMPTZ DEFAULT NOW()
);

-- Index for fast lookups by user
CREATE INDEX IF NOT EXISTS idx_tasks_user_id ON processing_tasks(user_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status  ON processing_tasks(status);

-- Auto-update the updated_at column
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_processing_tasks_updated_at
    BEFORE UPDATE ON processing_tasks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
