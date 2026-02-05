"""Django admin configuration for sync_admin models."""

from django.contrib import admin
from .models import SyncJob, SyncState, Credential, SyncLog


@admin.register(SyncJob)
class SyncJobAdmin(admin.ModelAdmin):
    """Admin interface for SyncJob model."""
    
    list_display = ['job_id', 'user_id', 'status', 'total_notes', 'processed_notes', 
                    'failed_notes', 'created_at', 'completed_at']
    list_filter = ['status', 'full_sync', 'created_at']
    search_fields = ['job_id', 'user_id']
    readonly_fields = ['job_id', 'created_at', 'completed_at']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Job Information', {
            'fields': ('job_id', 'user_id', 'status', 'full_sync')
        }),
        ('Progress', {
            'fields': ('total_notes', 'processed_notes', 'failed_notes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'completed_at')
        }),
        ('Error Details', {
            'fields': ('error_message',),
            'classes': ('collapse',)
        }),
    )


@admin.register(SyncState)
class SyncStateAdmin(admin.ModelAdmin):
    """Admin interface for SyncState model."""
    
    list_display = ['id', 'user_id', 'keep_note_id', 'notion_page_id', 
                    'last_synced_at', 'keep_modified_at']
    list_filter = ['last_synced_at', 'keep_modified_at']
    search_fields = ['user_id', 'keep_note_id', 'notion_page_id']
    readonly_fields = ['last_synced_at']
    ordering = ['-last_synced_at']


@admin.register(Credential)
class CredentialAdmin(admin.ModelAdmin):
    """Admin interface for Credential model."""
    
    list_display = ['user_id', 'notion_database_id', 'updated_at']
    search_fields = ['user_id', 'notion_database_id']
    readonly_fields = ['updated_at']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user_id',)
        }),
        ('Google Keep Credentials', {
            'fields': ('google_oauth_token',),
            'description': 'Encrypted OAuth token for Google Keep access'
        }),
        ('Notion Credentials', {
            'fields': ('notion_api_token', 'notion_database_id'),
            'description': 'Encrypted API token and database ID for Notion access'
        }),
        ('Metadata', {
            'fields': ('updated_at',)
        }),
    )
    
    def get_form(self, request, obj=None, **kwargs):
        """Customize form to show password-style input for tokens."""
        form = super().get_form(request, obj, **kwargs)
        if 'google_oauth_token' in form.base_fields:
            form.base_fields['google_oauth_token'].widget.attrs['style'] = 'width: 600px;'
        if 'notion_api_token' in form.base_fields:
            form.base_fields['notion_api_token'].widget.attrs['style'] = 'width: 600px;'
        return form


@admin.register(SyncLog)
class SyncLogAdmin(admin.ModelAdmin):
    """Admin interface for SyncLog model."""
    
    list_display = ['id', 'job_id', 'level', 'keep_note_id', 'message_preview', 'created_at']
    list_filter = ['level', 'created_at']
    search_fields = ['job_id', 'keep_note_id', 'message']
    readonly_fields = ['created_at']
    ordering = ['-created_at']
    
    def message_preview(self, obj):
        """Show a preview of the message."""
        if len(obj.message) > 100:
            return obj.message[:100] + '...'
        return obj.message
    message_preview.short_description = 'Message'
    
    fieldsets = (
        ('Log Information', {
            'fields': ('job_id', 'level', 'keep_note_id', 'created_at')
        }),
        ('Message', {
            'fields': ('message',)
        }),
    )
