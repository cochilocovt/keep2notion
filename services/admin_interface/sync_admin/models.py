"""Django models for the sync_admin app."""

from django.db import models
import uuid


class SyncJob(models.Model):
    """Model for sync_jobs table."""
    
    STATUS_CHOICES = [
        ('queued', 'Queued'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    job_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.CharField(max_length=255)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES)
    full_sync = models.BooleanField(default=False)
    total_notes = models.IntegerField(default=0)
    processed_notes = models.IntegerField(default=0)
    failed_notes = models.IntegerField(default=0)
    error_message = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'sync_jobs'
        indexes = [
            models.Index(fields=['user_id', '-created_at'], name='idx_sync_jobs_user_created'),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"SyncJob {self.job_id} - {self.status}"


class SyncState(models.Model):
    """Model for sync_state table."""
    
    id = models.AutoField(primary_key=True)
    user_id = models.CharField(max_length=255)
    keep_note_id = models.CharField(max_length=255)
    notion_page_id = models.CharField(max_length=255)
    last_synced_at = models.DateTimeField(auto_now_add=True)
    keep_modified_at = models.DateTimeField()
    
    class Meta:
        db_table = 'sync_state'
        unique_together = [['user_id', 'keep_note_id']]
        indexes = [
            models.Index(fields=['user_id', 'keep_note_id'], name='idx_sync_state_user_note'),
        ]
    
    def __str__(self):
        return f"SyncState {self.user_id} - {self.keep_note_id}"


class Credential(models.Model):
    """Model for credentials table."""
    
    user_id = models.CharField(max_length=255, primary_key=True)
    google_oauth_token = models.TextField()  # Encrypted
    notion_api_token = models.TextField()    # Encrypted
    notion_database_id = models.CharField(max_length=255)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'credentials'
    
    def __str__(self):
        return f"Credential for {self.user_id}"


class SyncLog(models.Model):
    """Model for sync_logs table."""
    
    LEVEL_CHOICES = [
        ('INFO', 'Info'),
        ('WARNING', 'Warning'),
        ('ERROR', 'Error'),
    ]
    
    id = models.AutoField(primary_key=True)
    job_id = models.UUIDField()
    keep_note_id = models.CharField(max_length=255, null=True, blank=True)
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'sync_logs'
        indexes = [
            models.Index(fields=['job_id'], name='idx_sync_logs_job_id'),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"SyncLog {self.level} - {self.job_id}"
