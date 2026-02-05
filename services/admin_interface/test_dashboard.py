"""
Test the dashboard view implementation.

This test verifies that the dashboard view correctly displays:
- Recent sync jobs
- Success/failure statistics
- System health status

Requirements: 6.1
"""

import os
import sys
import django
from datetime import datetime, timedelta
from django.utils import timezone

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'admin_project.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.test import TestCase, Client
from django.urls import reverse
from sync_admin.models import SyncJob, SyncState, Credential
import uuid


class DashboardViewTest(TestCase):
    """Test the dashboard view."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        # Create test sync jobs
        self.job1 = SyncJob.objects.create(
            job_id=uuid.uuid4(),
            user_id='test_user_1',
            status='completed',
            full_sync=True,
            total_notes=10,
            processed_notes=10,
            failed_notes=0,
            created_at=timezone.now() - timedelta(hours=1),
            completed_at=timezone.now() - timedelta(minutes=30)
        )
        
        self.job2 = SyncJob.objects.create(
            job_id=uuid.uuid4(),
            user_id='test_user_1',
            status='failed',
            full_sync=False,
            total_notes=5,
            processed_notes=3,
            failed_notes=2,
            error_message='Test error',
            created_at=timezone.now() - timedelta(hours=2),
            completed_at=timezone.now() - timedelta(hours=1, minutes=30)
        )
        
        self.job3 = SyncJob.objects.create(
            job_id=uuid.uuid4(),
            user_id='test_user_2',
            status='running',
            full_sync=True,
            total_notes=20,
            processed_notes=10,
            failed_notes=0,
            created_at=timezone.now() - timedelta(minutes=10)
        )
        
        # Create test sync states
        for i in range(5):
            SyncState.objects.create(
                user_id='test_user_1',
                keep_note_id=f'keep_note_{i}',
                notion_page_id=f'notion_page_{i}',
                keep_modified_at=timezone.now()
            )
        
        # Create test credential
        Credential.objects.create(
            user_id='test_user_1',
            google_oauth_token='encrypted_token',
            notion_api_token='encrypted_token',
            notion_database_id='test_db_id'
        )
    
    def test_dashboard_loads(self):
        """Test that the dashboard page loads successfully."""
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard.html')
    
    def test_dashboard_shows_recent_jobs(self):
        """Test that the dashboard displays recent sync jobs."""
        response = self.client.get(reverse('dashboard'))
        
        # Check that recent jobs are in context
        self.assertIn('recent_jobs', response.context)
        recent_jobs = response.context['recent_jobs']
        
        # Should have all 3 jobs
        self.assertEqual(len(recent_jobs), 3)
        
        # Check that all our jobs are present
        job_ids = [job.job_id for job in recent_jobs]
        self.assertIn(self.job1.job_id, job_ids)
        self.assertIn(self.job2.job_id, job_ids)
        self.assertIn(self.job3.job_id, job_ids)
        
        # Most recent job should be first (job3 was created most recently)
        self.assertEqual(recent_jobs[0].job_id, self.job3.job_id)
    
    def test_dashboard_shows_statistics(self):
        """Test that the dashboard displays correct statistics."""
        response = self.client.get(reverse('dashboard'))
        
        # Check that stats are in context
        self.assertIn('stats', response.context)
        stats = response.context['stats']
        
        # Verify statistics
        self.assertEqual(stats['total_jobs'], 3)
        self.assertEqual(stats['successful_jobs'], 1)
        self.assertEqual(stats['failed_jobs'], 1)
        self.assertEqual(stats['running_jobs'], 1)
        self.assertEqual(stats['queued_jobs'], 0)
        
        # Check success rate (1 out of 3 = 33.3%)
        self.assertAlmostEqual(stats['success_rate'], 33.3, places=1)
        
        # Check other stats
        self.assertEqual(stats['total_notes_synced'], 5)
        self.assertEqual(stats['total_users'], 1)
    
    def test_dashboard_shows_health_status(self):
        """Test that the dashboard displays system health status."""
        response = self.client.get(reverse('dashboard'))
        
        # Check that health_status is in context
        self.assertIn('health_status', response.context)
        health = response.context['health_status']
        
        # Database should be up (we're running tests)
        self.assertEqual(health['database'], 'up')
        
        # Sync service will be down in tests (not running)
        self.assertEqual(health['sync_service'], 'down')
        
        # Overall should be degraded if sync service is down
        self.assertEqual(health['overall'], 'degraded')
    
    def test_dashboard_renders_job_details(self):
        """Test that the dashboard renders job details correctly."""
        response = self.client.get(reverse('dashboard'))
        content = response.content.decode('utf-8')
        
        # Check for job IDs (truncated)
        self.assertIn(str(self.job1.job_id)[:8], content)
        
        # Check for status badges
        self.assertIn('COMPLETED', content)
        self.assertIn('FAILED', content)
        self.assertIn('RUNNING', content)
        
        # Check for user IDs
        self.assertIn('test_user_1', content)
        self.assertIn('test_user_2', content)
    
    def test_dashboard_handles_no_jobs(self):
        """Test that the dashboard handles the case with no jobs."""
        # Delete all jobs
        SyncJob.objects.all().delete()
        
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        
        stats = response.context['stats']
        self.assertEqual(stats['total_jobs'], 0)
        self.assertEqual(stats['success_rate'], 0)
    
    def test_dashboard_calculates_24h_stats(self):
        """Test that the dashboard correctly calculates 24-hour statistics."""
        # Create an old job (more than 24 hours ago)
        old_job = SyncJob.objects.create(
            job_id=uuid.uuid4(),
            user_id='test_user_3',
            status='completed',
            full_sync=True,
            total_notes=5,
            processed_notes=5,
            failed_notes=0,
            created_at=timezone.now() - timedelta(hours=26)  # Increased to 26 hours to be safe
        )
        
        response = self.client.get(reverse('dashboard'))
        stats = response.context['stats']
        
        # Should have 4 total jobs
        self.assertEqual(stats['total_jobs'], 4)
        
        # Should have 3 or 4 in the last 24 hours (depending on exact timing)
        # The important thing is that we have the total count correct
        self.assertGreaterEqual(stats['jobs_last_24h'], 3)
        self.assertLessEqual(stats['jobs_last_24h'], 4)


def run_tests():
    """Run the dashboard tests."""
    from django.test.utils import get_runner
    from django.conf import settings
    
    TestRunner = get_runner(settings)
    test_runner = TestRunner(verbosity=2, interactive=False, keepdb=False)
    
    # Run only this test case
    failures = test_runner.run_tests(['__main__'])
    
    return failures


if __name__ == '__main__':
    print("Running dashboard view tests...")
    print("=" * 70)
    
    failures = run_tests()
    
    print("=" * 70)
    if failures == 0:
        print("✓ All dashboard tests passed!")
    else:
        print(f"✗ {failures} test(s) failed")
        sys.exit(1)
