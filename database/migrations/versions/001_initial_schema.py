"""Initial schema

Revision ID: 001
Revises: 
Create Date: 2026-02-01

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create sync_jobs table
    op.execute("""
        CREATE TABLE IF NOT EXISTS sync_jobs (
            job_id UUID PRIMARY KEY,
            user_id VARCHAR(255) NOT NULL,
            status VARCHAR(50) NOT NULL,
            full_sync BOOLEAN DEFAULT FALSE,
            total_notes INTEGER DEFAULT 0,
            processed_notes INTEGER DEFAULT 0,
            failed_notes INTEGER DEFAULT 0,
            error_message TEXT,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            completed_at TIMESTAMP
        )
    """)
    
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_sync_jobs_user_created 
        ON sync_jobs(user_id, created_at DESC)
    """)
    
    # Create sync_state table
    op.execute("""
        CREATE TABLE IF NOT EXISTS sync_state (
            id SERIAL PRIMARY KEY,
            user_id VARCHAR(255) NOT NULL,
            keep_note_id VARCHAR(255) NOT NULL,
            notion_page_id VARCHAR(255) NOT NULL,
            last_synced_at TIMESTAMP NOT NULL DEFAULT NOW(),
            keep_modified_at TIMESTAMP NOT NULL,
            UNIQUE (user_id, keep_note_id)
        )
    """)
    
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_sync_state_user_note 
        ON sync_state(user_id, keep_note_id)
    """)
    
    # Create credentials table
    op.execute("""
        CREATE TABLE IF NOT EXISTS credentials (
            user_id VARCHAR(255) PRIMARY KEY,
            google_oauth_token TEXT NOT NULL,
            notion_api_token TEXT NOT NULL,
            notion_database_id VARCHAR(255) NOT NULL,
            updated_at TIMESTAMP NOT NULL DEFAULT NOW()
        )
    """)
    
    # Create sync_logs table
    op.execute("""
        CREATE TABLE IF NOT EXISTS sync_logs (
            id SERIAL PRIMARY KEY,
            job_id UUID NOT NULL REFERENCES sync_jobs(job_id),
            keep_note_id VARCHAR(255),
            level VARCHAR(20) NOT NULL,
            message TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT NOW()
        )
    """)
    
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_sync_logs_job_id 
        ON sync_logs(job_id)
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS sync_logs CASCADE")
    op.execute("DROP TABLE IF EXISTS credentials CASCADE")
    op.execute("DROP TABLE IF EXISTS sync_state CASCADE")
    op.execute("DROP TABLE IF EXISTS sync_jobs CASCADE")
