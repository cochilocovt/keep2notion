"""SQLAlchemy database models for the Google Keep to Notion sync application."""

from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Boolean, Text, DateTime, ForeignKey, Index, TypeDecorator
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func
import uuid


class UUID(TypeDecorator):
    """Platform-independent UUID type.
    
    Uses PostgreSQL's UUID type when available, otherwise uses
    CHAR(36), storing as stringified hex values.
    """
    impl = String
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        else:
            return dialect.type_descriptor(String(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return value
        else:
            if isinstance(value, uuid.UUID):
                return str(value)
            return value

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return value
        else:
            if isinstance(value, str):
                return uuid.UUID(value)
            return value


Base = declarative_base()


class SyncJob(Base):
    """Model for sync_jobs table."""
    __tablename__ = 'sync_jobs'
    
    job_id = Column(UUID(), primary_key=True)
    user_id = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False)
    full_sync = Column(Boolean, default=False)
    total_notes = Column(Integer, default=0)
    processed_notes = Column(Integer, default=0)
    failed_notes = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    completed_at = Column(DateTime, nullable=True)
    
    __table_args__ = (
        Index('idx_sync_jobs_user_created', 'user_id', 'created_at'),
    )


class SyncState(Base):
    """Model for sync_state table."""
    __tablename__ = 'sync_state'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(255), nullable=False)
    keep_note_id = Column(String(255), nullable=False)
    notion_page_id = Column(String(255), nullable=False)
    last_synced_at = Column(DateTime, nullable=False, server_default=func.now())
    keep_modified_at = Column(DateTime, nullable=False)
    
    __table_args__ = (
        Index('idx_sync_state_user_note', 'user_id', 'keep_note_id', unique=True),
    )


class Credential(Base):
    """Model for credentials table."""
    __tablename__ = 'credentials'
    
    user_id = Column(String(255), primary_key=True)
    google_oauth_token = Column(Text, nullable=False)  # Encrypted
    notion_api_token = Column(Text, nullable=False)    # Encrypted
    notion_database_id = Column(String(255), nullable=False)
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())


class SyncLog(Base):
    """Model for sync_logs table."""
    __tablename__ = 'sync_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(UUID(), ForeignKey('sync_jobs.job_id'), nullable=False)
    keep_note_id = Column(String(255), nullable=True)
    level = Column(String(20), nullable=False)  # INFO, WARNING, ERROR
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    
    __table_args__ = (
        Index('idx_sync_logs_job_id', 'job_id'),
    )
