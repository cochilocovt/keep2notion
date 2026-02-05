"""
Manual test to verify the dashboard view works correctly.

This script creates some test data and then checks if the dashboard loads.
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'admin_project.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from sync_admin.models import SyncJob, SyncState, Credential
from django.utils import timezone
from datetime import timedelta
import uuid


def create_test_data():
    """Create some test data for the dashboard."""
    print("Creating test data...")
    
    # Create a test user credential
    try:
        cred = Credential.objects.get_or_create(
            user_id='test_user_dashboard',
            defaults={
                'google_oauth_token': 'test_token_encrypted',
                'notion_api_token': 'test_token_encrypted',
                'notion_database_id': 'test_db_id'
            }
        )
        print(f"✓ Created/found credential for test_user_dashboard")
    except Exception as e:
        print(f"✗ Error creating credential: {e}")
    
    # Create some test sync jobs
    jobs_data = [
        {
            'user_id': 'test_user_dashboard',
            'status': 'completed',
            'full_sync': True,
            'total_notes': 15,
            'processed_notes': 15,
            'failed_notes': 0,
            'created_at': timezone.now() - timedelta(hours=2),
            'completed_at': timezone.now() - timedelta(hours=1, minutes=30)
        },
        {
            'user_id': 'test_user_dashboard',
            'status': 'failed',
            'full_sync': False,
            'total_notes': 10,
            'processed_notes': 7,
            'failed_notes': 3,
            'error_message': 'Network timeout during sync',
            'created_at': timezone.now() - timedelta(hours=5),
            'completed_at': timezone.now() - timedelta(hours=4, minutes=30)
        },
        {
            'user_id': 'test_user_dashboard',
            'status': 'running',
            'full_sync': True,
            'total_notes': 25,
            'processed_notes': 12,
            'failed_notes': 0,
            'created_at': timezone.now() - timedelta(minutes=15)
        },
        {
            'user_id': 'test_user_dashboard',
            'status': 'queued',
            'full_sync': False,
            'total_notes': 0,
            'processed_notes': 0,
            'failed_notes': 0,
            'created_at': timezone.now() - timedelta(minutes=5)
        }
    ]
    
    for job_data in jobs_data:
        try:
            job = SyncJob.objects.create(
                job_id=uuid.uuid4(),
                **job_data
            )
            print(f"✓ Created sync job: {job.job_id} ({job.status})")
        except Exception as e:
            print(f"✗ Error creating sync job: {e}")
    
    # Create some sync state records
    for i in range(10):
        try:
            state = SyncState.objects.get_or_create(
                user_id='test_user_dashboard',
                keep_note_id=f'keep_note_dashboard_{i}',
                defaults={
                    'notion_page_id': f'notion_page_dashboard_{i}',
                    'keep_modified_at': timezone.now() - timedelta(days=i)
                }
            )
            if i == 0:
                print(f"✓ Created/found sync state records")
        except Exception as e:
            print(f"✗ Error creating sync state: {e}")
    
    print("\nTest data created successfully!")
    print("\nYou can now:")
    print("1. Run the development server: python3 manage.py runserver")
    print("2. Visit http://localhost:8000/ to see the dashboard")
    print("3. Visit http://localhost:8000/admin/ to see the Django admin")


def show_stats():
    """Show current database statistics."""
    print("\n" + "=" * 70)
    print("Current Database Statistics:")
    print("=" * 70)
    
    total_jobs = SyncJob.objects.count()
    completed = SyncJob.objects.filter(status='completed').count()
    failed = SyncJob.objects.filter(status='failed').count()
    running = SyncJob.objects.filter(status='running').count()
    queued = SyncJob.objects.filter(status='queued').count()
    
    print(f"Total Sync Jobs: {total_jobs}")
    print(f"  - Completed: {completed}")
    print(f"  - Failed: {failed}")
    print(f"  - Running: {running}")
    print(f"  - Queued: {queued}")
    
    total_states = SyncState.objects.count()
    print(f"\nTotal Sync States: {total_states}")
    
    total_users = Credential.objects.count()
    print(f"Total Users: {total_users}")
    
    print("=" * 70)


if __name__ == '__main__':
    print("Dashboard Manual Test")
    print("=" * 70)
    
    create_test_data()
    show_stats()
    
    print("\n✓ Manual test setup complete!")
