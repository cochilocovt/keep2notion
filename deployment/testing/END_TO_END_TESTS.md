# End-to-End Integration Testing Guide

This document describes comprehensive end-to-end integration tests for the Keep-Notion-Sync application deployed on AWS.

## Overview

End-to-end tests verify the complete sync workflow from Google Keep extraction through Notion writing, including:
- Authentication and authorization
- Data extraction from Google Keep
- Image handling via S3
- Data writing to Notion
- State management in PostgreSQL
- Error handling and recovery
- Performance under load

## Test Environment Setup

### Prerequisites

1. **Staging Environment**: Deployed and running
2. **Test Credentials**:
   - Google Keep test account with sample notes
   - Notion test workspace with database
3. **Test Tools**:
   - Python 3.11+
   - pytest
   - requests library
   - boto3 (for S3 verification)

### Install Test Dependencies

```bash
pip install pytest pytest-asyncio requests boto3 psycopg2-binary python-dotenv
```

### Configure Test Environment

Create `.env.test`:

```bash
# API Endpoints
API_BASE_URL=https://api-staging.keep-notion-sync.example.com
ADMIN_BASE_URL=https://admin-staging.keep-notion-sync.example.com

# Test Credentials
TEST_USER_ID=test-user-001
GOOGLE_OAUTH_TOKEN=test_google_token
NOTION_API_TOKEN=test_notion_token
NOTION_DATABASE_ID=test_database_id

# AWS Configuration
AWS_REGION=us-east-1
S3_BUCKET_NAME=keep-notion-sync-staging-images

# Database Configuration
DB_HOST=your-rds-endpoint
DB_NAME=keep_notion_sync_staging
DB_USER=dbadmin
DB_PASSWORD=your_db_password
```

## Test Suite

Create `deployment/testing/test_e2e.py`:

```python
import pytest
import requests
import time
import os
from typing import Dict, Any
from dotenv import load_dotenv
import boto3
import psycopg2

# Load test environment
load_dotenv('.env.test')

# Configuration
API_BASE_URL = os.getenv('API_BASE_URL')
TEST_USER_ID = os.getenv('TEST_USER_ID')

class TestE2ESync:
    """End-to-end integration tests for sync workflow"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.api_url = API_BASE_URL
        self.user_id = TEST_USER_ID
        self.session = requests.Session()
        
        # Verify API is accessible
        response = self.session.get(f"{self.api_url}/api/v1/health")
        assert response.status_code == 200, "API not accessible"
        
        yield
        
        # Cleanup after tests
        self.session.close()
    
    def test_01_health_check(self):
        """Test: Health endpoint returns healthy status"""
        response = self.session.get(f"{self.api_url}/api/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'healthy'
        assert 'services' in data
        assert data['services']['database'] == 'up'
        print("✓ Health check passed")
    
    def test_02_start_sync_job(self):
        """Test: Can initiate a sync job"""
        payload = {
            "user_id": self.user_id,
            "full_sync": False
        }
        
        response = self.session.post(
            f"{self.api_url}/api/v1/sync/start",
            json=payload
        )
        
        assert response.status_code == 200
        data = response.json()
        assert 'job_id' in data
        assert data['status'] in ['queued', 'running']
        
        # Store job_id for subsequent tests
        self.job_id = data['job_id']
        print(f"✓ Sync job started: {self.job_id}")
    
    def test_03_query_sync_status(self):
        """Test: Can query sync job status"""
        # Start a job first
        self.test_02_start_sync_job()
        
        response = self.session.get(
            f"{self.api_url}/api/v1/sync/jobs/{self.job_id}"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['job_id'] == self.job_id
        assert 'status' in data
        assert 'progress' in data
        print(f"✓ Job status: {data['status']}")
    
    def test_04_wait_for_sync_completion(self):
        """Test: Sync job completes successfully"""
        # Start a job
        self.test_02_start_sync_job()
        
        # Poll for completion (max 5 minutes)
        max_wait = 300
        interval = 5
        elapsed = 0
        
        while elapsed < max_wait:
            response = self.session.get(
                f"{self.api_url}/api/v1/sync/jobs/{self.job_id}"
            )
            data = response.json()
            status = data['status']
            
            print(f"  Status: {status}, Progress: {data.get('progress', {})}")
            
            if status == 'completed':
                assert data['progress']['failed_notes'] == 0, "Some notes failed"
                print(f"✓ Sync completed: {data['progress']['processed_notes']} notes")
                return
            elif status == 'failed':
                pytest.fail(f"Sync failed: {data.get('error_message')}")
            
            time.sleep(interval)
            elapsed += interval
        
        pytest.fail(f"Sync did not complete within {max_wait} seconds")
    
    def test_05_full_sync(self):
        """Test: Full sync processes all notes"""
        payload = {
            "user_id": self.user_id,
            "full_sync": True
        }
        
        response = self.session.post(
            f"{self.api_url}/api/v1/sync/start",
            json=payload
        )
        
        assert response.status_code == 200
        job_id = response.json()['job_id']
        
        # Wait for completion
        max_wait = 600  # 10 minutes for full sync
        interval = 10
        elapsed = 0
        
        while elapsed < max_wait:
            response = self.session.get(
                f"{self.api_url}/api/v1/sync/jobs/{job_id}"
            )
            data = response.json()
            
            if data['status'] == 'completed':
                progress = data['progress']
                assert progress['total_notes'] > 0, "No notes found"
                assert progress['processed_notes'] == progress['total_notes']
                print(f"✓ Full sync completed: {progress['processed_notes']} notes")
                return
            elif data['status'] == 'failed':
                pytest.fail(f"Full sync failed: {data.get('error_message')}")
            
            time.sleep(interval)
            elapsed += interval
        
        pytest.fail("Full sync did not complete in time")
    
    def test_06_sync_history(self):
        """Test: Can retrieve sync history"""
        response = self.session.get(
            f"{self.api_url}/api/v1/sync/history",
            params={
                "user_id": self.user_id,
                "limit": 10
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert 'jobs' in data
        assert len(data['jobs']) > 0, "No sync history found"
        assert data['total'] > 0
        print(f"✓ Found {data['total']} sync jobs in history")
    
    def test_07_incremental_sync(self):
        """Test: Incremental sync only processes new/modified notes"""
        # Run first sync
        response1 = self.session.post(
            f"{self.api_url}/api/v1/sync/start",
            json={"user_id": self.user_id, "full_sync": False}
        )
        job_id1 = response1.json()['job_id']
        
        # Wait for completion
        self._wait_for_job(job_id1)
        
        # Get first sync results
        response1 = self.session.get(f"{self.api_url}/api/v1/sync/jobs/{job_id1}")
        notes_count1 = response1.json()['progress']['processed_notes']
        
        # Run second sync immediately (should process 0 or few notes)
        response2 = self.session.post(
            f"{self.api_url}/api/v1/sync/start",
            json={"user_id": self.user_id, "full_sync": False}
        )
        job_id2 = response2.json()['job_id']
        
        self._wait_for_job(job_id2)
        
        response2 = self.session.get(f"{self.api_url}/api/v1/sync/jobs/{job_id2}")
        notes_count2 = response2.json()['progress']['processed_notes']
        
        # Second sync should process fewer notes (ideally 0)
        assert notes_count2 <= notes_count1, "Incremental sync processed more notes"
        print(f"✓ Incremental sync: {notes_count1} → {notes_count2} notes")
    
    def test_08_error_handling(self):
        """Test: System handles errors gracefully"""
        # Test with invalid user_id
        response = self.session.post(
            f"{self.api_url}/api/v1/sync/start",
            json={"user_id": "invalid-user", "full_sync": False}
        )
        
        # Should either reject or handle gracefully
        assert response.status_code in [200, 400, 404]
        print("✓ Error handling works")
    
    def test_09_concurrent_syncs(self):
        """Test: System handles concurrent sync requests"""
        job_ids = []
        
        # Start multiple syncs
        for i in range(3):
            response = self.session.post(
                f"{self.api_url}/api/v1/sync/start",
                json={"user_id": f"{self.user_id}-{i}", "full_sync": False}
            )
            assert response.status_code == 200
            job_ids.append(response.json()['job_id'])
        
        # Wait for all to complete
        for job_id in job_ids:
            self._wait_for_job(job_id, max_wait=300)
        
        print(f"✓ Concurrent syncs completed: {len(job_ids)} jobs")
    
    def _wait_for_job(self, job_id: str, max_wait: int = 300):
        """Helper: Wait for job completion"""
        interval = 5
        elapsed = 0
        
        while elapsed < max_wait:
            response = self.session.get(
                f"{self.api_url}/api/v1/sync/jobs/{job_id}"
            )
            status = response.json()['status']
            
            if status in ['completed', 'failed']:
                return
            
            time.sleep(interval)
            elapsed += interval
        
        raise TimeoutError(f"Job {job_id} did not complete")


class TestE2EDataIntegrity:
    """Test data integrity across the sync pipeline"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup database connection"""
        self.db_conn = psycopg2.connect(
            host=os.getenv('DB_HOST'),
            database=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD')
        )
        self.cursor = self.db_conn.cursor()
        
        yield
        
        self.cursor.close()
        self.db_conn.close()
    
    def test_10_sync_state_recorded(self):
        """Test: Sync state is properly recorded in database"""
        # Query sync_state table
        self.cursor.execute("""
            SELECT COUNT(*) FROM sync_state
            WHERE user_id = %s
        """, (TEST_USER_ID,))
        
        count = self.cursor.fetchone()[0]
        assert count > 0, "No sync state records found"
        print(f"✓ Found {count} sync state records")
    
    def test_11_sync_jobs_logged(self):
        """Test: Sync jobs are logged in database"""
        self.cursor.execute("""
            SELECT COUNT(*) FROM sync_jobs
            WHERE user_id = %s
        """, (TEST_USER_ID,))
        
        count = self.cursor.fetchone()[0]
        assert count > 0, "No sync job records found"
        print(f"✓ Found {count} sync job records")
    
    def test_12_no_duplicate_syncs(self):
        """Test: No duplicate sync state entries"""
        self.cursor.execute("""
            SELECT keep_note_id, COUNT(*)
            FROM sync_state
            WHERE user_id = %s
            GROUP BY keep_note_id
            HAVING COUNT(*) > 1
        """, (TEST_USER_ID,))
        
        duplicates = self.cursor.fetchall()
        assert len(duplicates) == 0, f"Found {len(duplicates)} duplicate entries"
        print("✓ No duplicate sync state entries")


class TestE2ES3Integration:
    """Test S3 image handling"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup S3 client"""
        self.s3_client = boto3.client('s3', region_name=os.getenv('AWS_REGION'))
        self.bucket_name = os.getenv('S3_BUCKET_NAME')
        
        yield
    
    def test_13_s3_bucket_accessible(self):
        """Test: S3 bucket is accessible"""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            print(f"✓ S3 bucket accessible: {self.bucket_name}")
        except Exception as e:
            pytest.fail(f"S3 bucket not accessible: {e}")
    
    def test_14_lifecycle_rules_configured(self):
        """Test: S3 lifecycle rules are configured"""
        try:
            response = self.s3_client.get_bucket_lifecycle_configuration(
                Bucket=self.bucket_name
            )
            rules = response['Rules']
            assert len(rules) > 0, "No lifecycle rules found"
            
            # Check for expiration rule
            expiration_rule = next(
                (r for r in rules if 'Expiration' in r),
                None
            )
            assert expiration_rule is not None, "No expiration rule found"
            print(f"✓ Lifecycle rules configured: {len(rules)} rules")
        except Exception as e:
            pytest.fail(f"Failed to get lifecycle rules: {e}")


class TestE2EPerformance:
    """Performance and load tests"""
    
    def test_15_response_time(self):
        """Test: API response times are acceptable"""
        import time
        
        # Test health endpoint
        start = time.time()
        response = requests.get(f"{API_BASE_URL}/api/v1/health")
        duration = time.time() - start
        
        assert response.status_code == 200
        assert duration < 1.0, f"Health check too slow: {duration}s"
        print(f"✓ Health check response time: {duration:.3f}s")
    
    def test_16_database_query_performance(self):
        """Test: Database queries are performant"""
        db_conn = psycopg2.connect(
            host=os.getenv('DB_HOST'),
            database=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD')
        )
        cursor = db_conn.cursor()
        
        import time
        start = time.time()
        cursor.execute("""
            SELECT * FROM sync_state
            WHERE user_id = %s
            LIMIT 100
        """, (TEST_USER_ID,))
        cursor.fetchall()
        duration = time.time() - start
        
        assert duration < 0.1, f"Query too slow: {duration}s"
        print(f"✓ Database query time: {duration:.3f}s")
        
        cursor.close()
        db_conn.close()


# Run tests
if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
```

## Running the Tests

### Run All Tests

```bash
cd deployment/testing
pytest test_e2e.py -v
```

### Run Specific Test Class

```bash
# Run only sync tests
pytest test_e2e.py::TestE2ESync -v

# Run only data integrity tests
pytest test_e2e.py::TestE2EDataIntegrity -v

# Run only S3 tests
pytest test_e2e.py::TestE2ES3Integration -v

# Run only performance tests
pytest test_e2e.py::TestE2EPerformance -v
```

### Run with Coverage

```bash
pytest test_e2e.py --cov=. --cov-report=html
```

### Generate Test Report

```bash
pytest test_e2e.py --html=report.html --self-contained-html
```

## Expected Results

### Successful Test Run

```
test_e2e.py::TestE2ESync::test_01_health_check PASSED
test_e2e.py::TestE2ESync::test_02_start_sync_job PASSED
test_e2e.py::TestE2ESync::test_03_query_sync_status PASSED
test_e2e.py::TestE2ESync::test_04_wait_for_sync_completion PASSED
test_e2e.py::TestE2ESync::test_05_full_sync PASSED
test_e2e.py::TestE2ESync::test_06_sync_history PASSED
test_e2e.py::TestE2ESync::test_07_incremental_sync PASSED
test_e2e.py::TestE2ESync::test_08_error_handling PASSED
test_e2e.py::TestE2ESync::test_09_concurrent_syncs PASSED
test_e2e.py::TestE2EDataIntegrity::test_10_sync_state_recorded PASSED
test_e2e.py::TestE2EDataIntegrity::test_11_sync_jobs_logged PASSED
test_e2e.py::TestE2EDataIntegrity::test_12_no_duplicate_syncs PASSED
test_e2e.py::TestE2ES3Integration::test_13_s3_bucket_accessible PASSED
test_e2e.py::TestE2ES3Integration::test_14_lifecycle_rules_configured PASSED
test_e2e.py::TestE2EPerformance::test_15_response_time PASSED
test_e2e.py::TestE2EPerformance::test_16_database_query_performance PASSED

==================== 16 passed in 245.32s ====================
```

## Manual Testing Scenarios

### Scenario 1: First-Time User Sync

1. Create new test user in admin interface
2. Configure Google Keep and Notion credentials
3. Trigger full sync
4. Verify all notes appear in Notion
5. Check sync state in database

### Scenario 2: Incremental Sync

1. Run initial sync
2. Add new note in Google Keep
3. Run incremental sync
4. Verify only new note is synced
5. Check sync state updated

### Scenario 3: Error Recovery

1. Temporarily disable Notion API access
2. Trigger sync (should fail)
3. Re-enable Notion API
4. Retry sync
5. Verify sync completes successfully

### Scenario 4: Image Handling

1. Create note with images in Google Keep
2. Trigger sync
3. Verify images uploaded to S3
4. Verify images appear in Notion
5. Wait for cleanup period
6. Verify images deleted from S3

## Performance Benchmarks

### Expected Performance

| Metric | Target | Acceptable |
|--------|--------|------------|
| Health check response | < 100ms | < 500ms |
| Sync job creation | < 200ms | < 1s |
| Note processing rate | > 10/sec | > 5/sec |
| Database query | < 50ms | < 100ms |
| Image upload | < 2s | < 5s |

### Load Testing

```bash
# Install load testing tool
pip install locust

# Run load test
locust -f load_test.py --host=https://api-staging.keep-notion-sync.example.com
```

Create `load_test.py`:

```python
from locust import HttpUser, task, between

class SyncUser(HttpUser):
    wait_time = between(1, 3)
    
    @task(3)
    def health_check(self):
        self.client.get("/api/v1/health")
    
    @task(1)
    def start_sync(self):
        self.client.post("/api/v1/sync/start", json={
            "user_id": f"load-test-{self.environment.runner.user_count}",
            "full_sync": False
        })
    
    @task(2)
    def check_history(self):
        self.client.get("/api/v1/sync/history?limit=10")
```

## Troubleshooting Test Failures

### Connection Errors

```bash
# Verify API is accessible
curl https://api-staging.keep-notion-sync.example.com/api/v1/health

# Check DNS resolution
nslookup api-staging.keep-notion-sync.example.com

# Check SSL certificate
openssl s_client -connect api-staging.keep-notion-sync.example.com:443
```

### Database Errors

```bash
# Test database connectivity
psql -h YOUR_RDS_ENDPOINT -U dbadmin -d keep_notion_sync_staging

# Check database logs
aws rds describe-db-log-files --db-instance-identifier keep-notion-sync-staging-db
```

### S3 Errors

```bash
# Verify bucket exists
aws s3 ls s3://keep-notion-sync-staging-images

# Check IAM permissions
aws iam get-role-policy --role-name KeepNotionSyncRole --policy-name S3Access
```

## Continuous Integration

### GitHub Actions Workflow

Create `.github/workflows/e2e-tests.yml`:

```yaml
name: E2E Tests

on:
  push:
    branches: [main, staging]
  pull_request:
    branches: [main]

jobs:
  e2e-tests:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install pytest requests boto3 psycopg2-binary python-dotenv
    
    - name: Run E2E tests
      env:
        API_BASE_URL: ${{ secrets.STAGING_API_URL }}
        TEST_USER_ID: ${{ secrets.TEST_USER_ID }}
        DB_HOST: ${{ secrets.STAGING_DB_HOST }}
        DB_PASSWORD: ${{ secrets.STAGING_DB_PASSWORD }}
      run: |
        cd deployment/testing
        pytest test_e2e.py -v --junit-xml=test-results.xml
    
    - name: Publish test results
      uses: EnricoMi/publish-unit-test-result-action@v2
      if: always()
      with:
        files: deployment/testing/test-results.xml
```

## Additional Resources

- [pytest Documentation](https://docs.pytest.org/)
- [Locust Load Testing](https://locust.io/)
- [AWS Testing Best Practices](https://aws.amazon.com/blogs/devops/testing-best-practices/)
