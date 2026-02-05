"""Database operations for the Google Keep to Notion sync application."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.dialects.postgresql import insert

from shared.db_models import Base, SyncJob, SyncState, Credential, SyncLog
from shared.config import get_database_url


class DatabaseOperations:
    """Handles all database operations for the sync application."""
    
    def __init__(self, database_url: Optional[str] = None):
        """Initialize database connection."""
        self.database_url = database_url or get_database_url()
        self.engine = create_engine(self.database_url, pool_pre_ping=True)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
    
    def create_tables(self):
        """Create all tables in the database."""
        Base.metadata.create_all(bind=self.engine)
    
    def get_session(self) -> Session:
        """Get a new database session."""
        return self.SessionLocal()
    
    # Sync State Operations
    
    def get_sync_state_by_user(self, user_id: str) -> List[SyncState]:
        """
        Get all sync state records for a user.
        
        Args:
            user_id: The user ID to query
            
        Returns:
            List of SyncState records
        """
        with self.get_session() as session:
            stmt = select(SyncState).where(SyncState.user_id == user_id)
            result = session.execute(stmt)
            return list(result.scalars().all())
    
    def get_sync_record(
        self, 
        user_id: str, 
        keep_note_id: str
    ) -> Optional[SyncState]:
        """
        Get a specific sync state record by user_id and keep_note_id.
        
        Args:
            user_id: The user ID
            keep_note_id: The Google Keep note ID
            
        Returns:
            SyncState record or None if not found
        """
        with self.get_session() as session:
            stmt = select(SyncState).where(
                SyncState.user_id == user_id,
                SyncState.keep_note_id == keep_note_id
            )
            result = session.execute(stmt)
            return result.scalar_one_or_none()
    
    def upsert_sync_state(
        self,
        user_id: str,
        keep_note_id: str,
        notion_page_id: str,
        keep_modified_at: datetime
    ) -> SyncState:
        """
        Insert or update a sync state record.
        
        Args:
            user_id: The user ID
            keep_note_id: The Google Keep note ID
            notion_page_id: The Notion page ID
            keep_modified_at: The last modified timestamp from Keep
            
        Returns:
            The created or updated SyncState record
        """
        with self.get_session() as session:
            # Use PostgreSQL's INSERT ... ON CONFLICT DO UPDATE
            stmt = insert(SyncState).values(
                user_id=user_id,
                keep_note_id=keep_note_id,
                notion_page_id=notion_page_id,
                keep_modified_at=keep_modified_at,
                last_synced_at=datetime.utcnow()
            )
            
            # On conflict, update the record
            stmt = stmt.on_conflict_do_update(
                index_elements=['user_id', 'keep_note_id'],
                set_={
                    'notion_page_id': stmt.excluded.notion_page_id,
                    'keep_modified_at': stmt.excluded.keep_modified_at,
                    'last_synced_at': datetime.utcnow()
                }
            )
            
            session.execute(stmt)
            session.commit()
            
            # Fetch and return the record
            return self.get_sync_record(user_id, keep_note_id)
    
    def delete_sync_state(
        self,
        user_id: str,
        keep_note_id: Optional[str] = None
    ) -> int:
        """
        Delete sync state records for a user.
        
        Args:
            user_id: The user ID
            keep_note_id: Optional specific Keep note ID. If None, deletes all records for user.
            
        Returns:
            Number of records deleted
        """
        with self.get_session() as session:
            if keep_note_id:
                # Delete specific record
                result = session.query(SyncState).filter(
                    SyncState.user_id == user_id,
                    SyncState.keep_note_id == keep_note_id
                ).delete()
            else:
                # Delete all records for user
                result = session.query(SyncState).filter(
                    SyncState.user_id == user_id
                ).delete()
            
            session.commit()
            return result

    
    # Credential Management Operations
    
    def store_credentials(
        self,
        user_id: str,
        google_oauth_token: str,
        notion_api_token: str,
        notion_database_id: str,
        encryption_service: 'EncryptionService'
    ) -> Credential:
        """
        Store or update user credentials with encryption.
        
        Args:
            user_id: The user ID
            google_oauth_token: Google OAuth token (will be encrypted)
            notion_api_token: Notion API token (will be encrypted)
            notion_database_id: Notion database ID
            encryption_service: Encryption service for encrypting tokens
            
        Returns:
            The created or updated Credential record
        """
        with self.get_session() as session:
            # Encrypt tokens
            encrypted_google_token = encryption_service.encrypt(google_oauth_token)
            encrypted_notion_token = encryption_service.encrypt(notion_api_token)
            
            # Check if credential exists
            credential = session.query(Credential).filter(
                Credential.user_id == user_id
            ).first()
            
            if credential:
                # Update existing
                credential.google_oauth_token = encrypted_google_token
                credential.notion_api_token = encrypted_notion_token
                credential.notion_database_id = notion_database_id
                credential.updated_at = datetime.utcnow()
            else:
                # Create new
                credential = Credential(
                    user_id=user_id,
                    google_oauth_token=encrypted_google_token,
                    notion_api_token=encrypted_notion_token,
                    notion_database_id=notion_database_id
                )
                session.add(credential)
            
            session.commit()
            session.refresh(credential)
            return credential
    
    def get_credentials(
        self,
        user_id: str,
        encryption_service: 'EncryptionService'
    ) -> Optional[dict]:
        """
        Retrieve and decrypt user credentials.
        
        Args:
            user_id: The user ID
            encryption_service: Encryption service for decrypting tokens
            
        Returns:
            Dictionary with decrypted credentials or None if not found
        """
        with self.get_session() as session:
            credential = session.query(Credential).filter(
                Credential.user_id == user_id
            ).first()
            
            if not credential:
                return None
            
            # Decrypt tokens
            return {
                'user_id': credential.user_id,
                'google_oauth_token': encryption_service.decrypt(credential.google_oauth_token),
                'notion_api_token': encryption_service.decrypt(credential.notion_api_token),
                'notion_database_id': credential.notion_database_id,
                'updated_at': credential.updated_at
            }
    
    def delete_credentials(self, user_id: str) -> bool:
        """
        Delete user credentials.
        
        Args:
            user_id: The user ID
            
        Returns:
            True if credentials were deleted, False if not found
        """
        with self.get_session() as session:
            credential = session.query(Credential).filter(
                Credential.user_id == user_id
            ).first()
            
            if credential:
                session.delete(credential)
                session.commit()
                return True
            
            return False

    
    # Sync Job Tracking Operations
    
    def create_sync_job(
        self,
        job_id: UUID,
        user_id: str,
        full_sync: bool = False
    ) -> SyncJob:
        """
        Create a new sync job.
        
        Args:
            job_id: Unique job identifier
            user_id: The user ID
            full_sync: Whether this is a full sync or incremental
            
        Returns:
            The created SyncJob record
        """
        with self.get_session() as session:
            sync_job = SyncJob(
                job_id=job_id,
                user_id=user_id,
                status='queued',
                full_sync=full_sync
            )
            session.add(sync_job)
            session.commit()
            session.refresh(sync_job)
            return sync_job
    
    def update_sync_job(
        self,
        job_id: UUID,
        status: Optional[str] = None,
        total_notes: Optional[int] = None,
        processed_notes: Optional[int] = None,
        failed_notes: Optional[int] = None,
        error_message: Optional[str] = None,
        completed_at: Optional[datetime] = None
    ) -> Optional[SyncJob]:
        """
        Update a sync job with progress information.
        
        Args:
            job_id: The job ID to update
            status: New status (queued, running, completed, failed)
            total_notes: Total number of notes to process
            processed_notes: Number of notes processed so far
            failed_notes: Number of notes that failed
            error_message: Error message if job failed
            completed_at: Completion timestamp
            
        Returns:
            The updated SyncJob record or None if not found
        """
        with self.get_session() as session:
            sync_job = session.query(SyncJob).filter(
                SyncJob.job_id == job_id
            ).first()
            
            if not sync_job:
                return None
            
            if status is not None:
                sync_job.status = status
            if total_notes is not None:
                sync_job.total_notes = total_notes
            if processed_notes is not None:
                sync_job.processed_notes = processed_notes
            if failed_notes is not None:
                sync_job.failed_notes = failed_notes
            if error_message is not None:
                sync_job.error_message = error_message
            if completed_at is not None:
                sync_job.completed_at = completed_at
            
            session.commit()
            session.refresh(sync_job)
            return sync_job
    
    def get_sync_job(self, job_id: UUID) -> Optional[SyncJob]:
        """
        Get a sync job by ID.
        
        Args:
            job_id: The job ID
            
        Returns:
            SyncJob record or None if not found
        """
        with self.get_session() as session:
            return session.query(SyncJob).filter(
                SyncJob.job_id == job_id
            ).first()
    
    def get_sync_jobs_by_user(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[SyncJob]:
        """
        Get sync jobs for a user with pagination.
        
        Args:
            user_id: The user ID
            limit: Maximum number of jobs to return
            offset: Number of jobs to skip
            
        Returns:
            List of SyncJob records
        """
        with self.get_session() as session:
            stmt = select(SyncJob).where(
                SyncJob.user_id == user_id
            ).order_by(
                SyncJob.created_at.desc()
            ).limit(limit).offset(offset)
            
            result = session.execute(stmt)
            return list(result.scalars().all())
    
    def get_sync_jobs(
        self,
        user_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> tuple[List[SyncJob], int]:
        """
        Get sync jobs with optional user filtering and pagination.
        
        Args:
            user_id: Optional user ID to filter by
            limit: Maximum number of jobs to return
            offset: Number of jobs to skip
            
        Returns:
            Tuple of (list of SyncJob records, total count)
        """
        with self.get_session() as session:
            # Build base query
            stmt = select(SyncJob)
            count_stmt = select(SyncJob)
            
            # Apply user filter if provided
            if user_id:
                stmt = stmt.where(SyncJob.user_id == user_id)
                count_stmt = count_stmt.where(SyncJob.user_id == user_id)
            
            # Get total count
            from sqlalchemy import func as sql_func
            total_count = session.execute(
                select(sql_func.count()).select_from(count_stmt.subquery())
            ).scalar()
            
            # Apply ordering and pagination
            stmt = stmt.order_by(
                SyncJob.created_at.desc()
            ).limit(limit).offset(offset)
            
            result = session.execute(stmt)
            jobs = list(result.scalars().all())
            
            return jobs, total_count
    
    def increment_sync_job_progress(
        self,
        job_id: UUID,
        processed: int = 1,
        failed: int = 0
    ) -> Optional[SyncJob]:
        """
        Increment sync job progress counters.
        
        Args:
            job_id: The job ID
            processed: Number of notes to add to processed count
            failed: Number of notes to add to failed count
            
        Returns:
            The updated SyncJob record or None if not found
        """
        with self.get_session() as session:
            sync_job = session.query(SyncJob).filter(
                SyncJob.job_id == job_id
            ).first()
            
            if not sync_job:
                return None
            
            sync_job.processed_notes += processed
            sync_job.failed_notes += failed
            
            session.commit()
            session.refresh(sync_job)
            return sync_job
    
    # Sync Log Operations
    
    def add_sync_log(
        self,
        job_id: UUID,
        level: str,
        message: str,
        keep_note_id: Optional[str] = None
    ) -> SyncLog:
        """
        Add a log entry for a sync job.
        
        Args:
            job_id: The job ID
            level: Log level (INFO, WARNING, ERROR)
            message: Log message
            keep_note_id: Optional Keep note ID related to this log
            
        Returns:
            The created SyncLog record
        """
        with self.get_session() as session:
            sync_log = SyncLog(
                job_id=job_id,
                level=level,
                message=message,
                keep_note_id=keep_note_id
            )
            session.add(sync_log)
            session.commit()
            session.refresh(sync_log)
            return sync_log
    
    def get_sync_logs(
        self,
        job_id: UUID,
        limit: int = 100
    ) -> List[SyncLog]:
        """
        Get log entries for a sync job.
        
        Args:
            job_id: The job ID
            limit: Maximum number of logs to return
            
        Returns:
            List of SyncLog records
        """
        with self.get_session() as session:
            stmt = select(SyncLog).where(
                SyncLog.job_id == job_id
            ).order_by(
                SyncLog.created_at.asc()
            ).limit(limit)
            
            result = session.execute(stmt)
            return list(result.scalars().all())
