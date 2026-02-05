"""Unit tests for sync_admin models."""

from django.test import TestCase
from django.utils import timezone
from datetime import datetime, timedelta
import uuid
from .models import SyncJob, SyncState, Credential, SyncLog


class SyncJobModelTest(TestCase):
    """Test cases for SyncJob model."""
    
    def test_create_sync_job(self):
        """Test creating a sync job with default values."""
        job = SyncJob.objects.create(
            user_id='test_user',
            status='queued'
        )
        
        self.assertIsNotNone(job.job_id)
        self.assertEqual(job.user_id, 'test_user')
        self.assertEqual(job.status, 'queued')
        self.assertFalse(job.full_sync)
        self.assertEqual(job.total_notes, 0)
        self.assertEqual(job.processed_notes, 0)
        self.assertEqual(job.failed_notes, 0)
        self.assertIsNone(job.error_message)
        self.assertIsNotNone(job.created_at)
        self.assertIsNone(job.completed_at)
    
    def test_sync_job_with_custom_values(self):
        """Test creating a sync job with custom values."""
        job_id = uuid.uuid4()
        completed_at = timezone.now()
        
        job = SyncJob.objects.create(
            job_id=job_id,
            user_id='test_user',
            status='completed',
            full_sync=True,
            total_notes=100,
            processed_notes=95,
            failed_notes=5,
            error_message='Some notes failed',
            completed_at=completed_at
        )
        
        self.assertEqual(job.job_id, job_id)
        self.assertTrue(job.full_sync)
        self.assertEqual(job.total_notes, 100)
        self.assertEqual(job.processed_notes, 95)
        self.assertEqual(job.failed_notes, 5)
        self.assertEqual(job.error_message, 'Some notes failed')
        self.assertEqual(job.completed_at, completed_at)
    
    def test_sync_job_status_choices(self):
        """Test that all status choices are valid."""
        valid_statuses = ['queued', 'running', 'completed', 'failed']
        
        for status in valid_statuses:
            job = SyncJob.objects.create(
                user_id='test_user',
                status=status
            )
            self.assertEqual(job.status, status)
    
    def test_sync_job_str_representation(self):
        """Test string representation of SyncJob."""
        job = SyncJob.objects.create(
            user_id='test_user',
            status='running'
        )
        
        expected = f"SyncJob {job.job_id} - running"
        self.assertEqual(str(job), expected)
    
    def test_sync_job_ordering(self):
        """Test that sync jobs are ordered by created_at descending."""
        # Create jobs with different timestamps
        job1 = SyncJob.objects.create(user_id='user1', status='queued')
        job2 = SyncJob.objects.create(user_id='user2', status='queued')
        job3 = SyncJob.objects.create(user_id='user3', status='queued')
        
        jobs = list(SyncJob.objects.all())
        
        # Most recent should be first
        self.assertEqual(jobs[0].job_id, job3.job_id)
        self.assertEqual(jobs[1].job_id, job2.job_id)
        self.assertEqual(jobs[2].job_id, job1.job_id)


class SyncStateModelTest(TestCase):
    """Test cases for SyncState model."""
    
    def test_create_sync_state(self):
        """Test creating a sync state record."""
        keep_modified_at = timezone.now() - timedelta(days=1)
        
        state = SyncState.objects.create(
            user_id='test_user',
            keep_note_id='keep_123',
            notion_page_id='notion_456',
            keep_modified_at=keep_modified_at
        )
        
        self.assertIsNotNone(state.id)
        self.assertEqual(state.user_id, 'test_user')
        self.assertEqual(state.keep_note_id, 'keep_123')
        self.assertEqual(state.notion_page_id, 'notion_456')
        self.assertIsNotNone(state.last_synced_at)
        self.assertEqual(state.keep_modified_at, keep_modified_at)
    
    def test_sync_state_unique_constraint(self):
        """Test that user_id and keep_note_id combination is unique."""
        keep_modified_at = timezone.now()
        
        SyncState.objects.create(
            user_id='test_user',
            keep_note_id='keep_123',
            notion_page_id='notion_456',
            keep_modified_at=keep_modified_at
        )
        
        # Attempting to create duplicate should raise an error
        with self.assertRaises(Exception):
            SyncState.objects.create(
                user_id='test_user',
                keep_note_id='keep_123',
                notion_page_id='notion_789',
                keep_modified_at=keep_modified_at
            )
    
    def test_sync_state_str_representation(self):
        """Test string representation of SyncState."""
        state = SyncState.objects.create(
            user_id='test_user',
            keep_note_id='keep_123',
            notion_page_id='notion_456',
            keep_modified_at=timezone.now()
        )
        
        expected = "SyncState test_user - keep_123"
        self.assertEqual(str(state), expected)
    
    def test_sync_state_query_by_user(self):
        """Test querying sync states by user_id."""
        keep_modified_at = timezone.now()
        
        SyncState.objects.create(
            user_id='user1',
            keep_note_id='keep_1',
            notion_page_id='notion_1',
            keep_modified_at=keep_modified_at
        )
        SyncState.objects.create(
            user_id='user1',
            keep_note_id='keep_2',
            notion_page_id='notion_2',
            keep_modified_at=keep_modified_at
        )
        SyncState.objects.create(
            user_id='user2',
            keep_note_id='keep_3',
            notion_page_id='notion_3',
            keep_modified_at=keep_modified_at
        )
        
        user1_states = SyncState.objects.filter(user_id='user1')
        self.assertEqual(user1_states.count(), 2)


class CredentialModelTest(TestCase):
    """Test cases for Credential model."""
    
    def test_create_credential(self):
        """Test creating a credential record."""
        cred = Credential.objects.create(
            user_id='test_user',
            google_oauth_token='encrypted_google_token',
            notion_api_token='encrypted_notion_token',
            notion_database_id='db_123'
        )
        
        self.assertEqual(cred.user_id, 'test_user')
        self.assertEqual(cred.google_oauth_token, 'encrypted_google_token')
        self.assertEqual(cred.notion_api_token, 'encrypted_notion_token')
        self.assertEqual(cred.notion_database_id, 'db_123')
        self.assertIsNotNone(cred.updated_at)
    
    def test_credential_unique_user_id(self):
        """Test that user_id is unique."""
        Credential.objects.create(
            user_id='test_user',
            google_oauth_token='token1',
            notion_api_token='token2',
            notion_database_id='db_123'
        )
        
        # Attempting to create duplicate should raise an error
        with self.assertRaises(Exception):
            Credential.objects.create(
                user_id='test_user',
                google_oauth_token='token3',
                notion_api_token='token4',
                notion_database_id='db_456'
            )
    
    def test_credential_update_timestamp(self):
        """Test that updated_at is automatically updated."""
        cred = Credential.objects.create(
            user_id='test_user',
            google_oauth_token='token1',
            notion_api_token='token2',
            notion_database_id='db_123'
        )
        
        original_updated_at = cred.updated_at
        
        # Update the credential
        cred.google_oauth_token = 'new_token'
        cred.save()
        
        # Refresh from database
        cred.refresh_from_db()
        
        # updated_at should be different (newer)
        self.assertGreaterEqual(cred.updated_at, original_updated_at)
    
    def test_credential_str_representation(self):
        """Test string representation of Credential."""
        cred = Credential.objects.create(
            user_id='test_user',
            google_oauth_token='token1',
            notion_api_token='token2',
            notion_database_id='db_123'
        )
        
        expected = "Credential for test_user"
        self.assertEqual(str(cred), expected)


class SyncLogModelTest(TestCase):
    """Test cases for SyncLog model."""
    
    def test_create_sync_log(self):
        """Test creating a sync log entry."""
        job_id = uuid.uuid4()
        
        log = SyncLog.objects.create(
            job_id=job_id,
            level='INFO',
            message='Test log message'
        )
        
        self.assertIsNotNone(log.id)
        self.assertEqual(log.job_id, job_id)
        self.assertIsNone(log.keep_note_id)
        self.assertEqual(log.level, 'INFO')
        self.assertEqual(log.message, 'Test log message')
        self.assertIsNotNone(log.created_at)
    
    def test_sync_log_with_note_id(self):
        """Test creating a sync log with keep_note_id."""
        job_id = uuid.uuid4()
        
        log = SyncLog.objects.create(
            job_id=job_id,
            keep_note_id='keep_123',
            level='ERROR',
            message='Failed to sync note'
        )
        
        self.assertEqual(log.keep_note_id, 'keep_123')
        self.assertEqual(log.level, 'ERROR')
    
    def test_sync_log_level_choices(self):
        """Test that all log level choices are valid."""
        job_id = uuid.uuid4()
        valid_levels = ['INFO', 'WARNING', 'ERROR']
        
        for level in valid_levels:
            log = SyncLog.objects.create(
                job_id=job_id,
                level=level,
                message=f'Test {level} message'
            )
            self.assertEqual(log.level, level)
    
    def test_sync_log_str_representation(self):
        """Test string representation of SyncLog."""
        job_id = uuid.uuid4()
        
        log = SyncLog.objects.create(
            job_id=job_id,
            level='WARNING',
            message='Test warning'
        )
        
        expected = f"SyncLog WARNING - {job_id}"
        self.assertEqual(str(log), expected)
    
    def test_sync_log_ordering(self):
        """Test that sync logs are ordered by created_at descending."""
        job_id = uuid.uuid4()
        
        log1 = SyncLog.objects.create(job_id=job_id, level='INFO', message='First')
        log2 = SyncLog.objects.create(job_id=job_id, level='INFO', message='Second')
        log3 = SyncLog.objects.create(job_id=job_id, level='INFO', message='Third')
        
        logs = list(SyncLog.objects.all())
        
        # Most recent should be first
        self.assertEqual(logs[0].id, log3.id)
        self.assertEqual(logs[1].id, log2.id)
        self.assertEqual(logs[2].id, log1.id)
    
    def test_sync_log_query_by_job_id(self):
        """Test querying sync logs by job_id."""
        job_id_1 = uuid.uuid4()
        job_id_2 = uuid.uuid4()
        
        SyncLog.objects.create(job_id=job_id_1, level='INFO', message='Job 1 log 1')
        SyncLog.objects.create(job_id=job_id_1, level='INFO', message='Job 1 log 2')
        SyncLog.objects.create(job_id=job_id_2, level='INFO', message='Job 2 log 1')
        
        job1_logs = SyncLog.objects.filter(job_id=job_id_1)
        self.assertEqual(job1_logs.count(), 2)
        
        job2_logs = SyncLog.objects.filter(job_id=job_id_2)
        self.assertEqual(job2_logs.count(), 1)
