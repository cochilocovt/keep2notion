"""Tests for database operations."""

import pytest
from datetime import datetime
from uuid import uuid4
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from shared.db_models import Base
from shared.db_operations import DatabaseOperations
from shared.encryption import EncryptionService


@pytest.fixture
def db_ops():
    """Create a test database operations instance with in-memory SQLite."""
    # Use in-memory SQLite for testing
    db = DatabaseOperations(database_url="sqlite:///:memory:")
    db.create_tables()
    return db


@pytest.fixture
def encryption_service():
    """Create an encryption service for testing."""
    return EncryptionService()


def test_create_and_get_sync_job(db_ops):
    """Test creating and retrieving a sync job."""
    job_id = uuid4()
    user_id = "test_user_1"
    
    # Create sync job
    job = db_ops.create_sync_job(job_id, user_id, full_sync=True)
    
    assert job.job_id == job_id
    assert job.user_id == user_id
    assert job.status == "queued"
    assert job.full_sync is True
    assert job.total_notes == 0
    assert job.processed_notes == 0
    assert job.failed_notes == 0
    
    # Retrieve sync job
    retrieved_job = db_ops.get_sync_job(job_id)
    assert retrieved_job is not None
    assert retrieved_job.job_id == job_id
    assert retrieved_job.user_id == user_id


def test_update_sync_job(db_ops):
    """Test updating a sync job."""
    job_id = uuid4()
    user_id = "test_user_2"
    
    # Create sync job
    db_ops.create_sync_job(job_id, user_id)
    
    # Update sync job
    updated_job = db_ops.update_sync_job(
        job_id,
        status="running",
        total_notes=10,
        processed_notes=5,
        failed_notes=1
    )
    
    assert updated_job.status == "running"
    assert updated_job.total_notes == 10
    assert updated_job.processed_notes == 5
    assert updated_job.failed_notes == 1


def test_increment_sync_job_progress(db_ops):
    """Test incrementing sync job progress."""
    job_id = uuid4()
    user_id = "test_user_3"
    
    # Create sync job
    db_ops.create_sync_job(job_id, user_id)
    db_ops.update_sync_job(job_id, total_notes=10)
    
    # Increment progress
    db_ops.increment_sync_job_progress(job_id, processed=1, failed=0)
    job = db_ops.get_sync_job(job_id)
    assert job.processed_notes == 1
    assert job.failed_notes == 0
    
    # Increment again
    db_ops.increment_sync_job_progress(job_id, processed=2, failed=1)
    job = db_ops.get_sync_job(job_id)
    assert job.processed_notes == 3
    assert job.failed_notes == 1


def test_get_sync_jobs_by_user(db_ops):
    """Test retrieving sync jobs for a user."""
    user_id = "test_user_4"
    
    # Create multiple jobs
    job_ids = [uuid4() for _ in range(3)]
    for job_id in job_ids:
        db_ops.create_sync_job(job_id, user_id)
    
    # Retrieve jobs
    jobs = db_ops.get_sync_jobs_by_user(user_id, limit=10)
    assert len(jobs) == 3
    assert all(job.user_id == user_id for job in jobs)


def test_upsert_sync_state(db_ops):
    """Test inserting and updating sync state."""
    user_id = "test_user_5"
    keep_note_id = "keep_note_1"
    notion_page_id = "notion_page_1"
    modified_at = datetime.utcnow()
    
    # Insert new record
    state = db_ops.upsert_sync_state(
        user_id, keep_note_id, notion_page_id, modified_at
    )
    assert state.user_id == user_id
    assert state.keep_note_id == keep_note_id
    assert state.notion_page_id == notion_page_id
    
    # Update existing record
    new_notion_page_id = "notion_page_2"
    updated_state = db_ops.upsert_sync_state(
        user_id, keep_note_id, new_notion_page_id, modified_at
    )
    assert updated_state.notion_page_id == new_notion_page_id
    
    # Verify only one record exists
    all_states = db_ops.get_sync_state_by_user(user_id)
    assert len(all_states) == 1


def test_get_sync_record(db_ops):
    """Test retrieving a specific sync record."""
    user_id = "test_user_6"
    keep_note_id = "keep_note_2"
    notion_page_id = "notion_page_3"
    modified_at = datetime.utcnow()
    
    # Create record
    db_ops.upsert_sync_state(user_id, keep_note_id, notion_page_id, modified_at)
    
    # Retrieve record
    record = db_ops.get_sync_record(user_id, keep_note_id)
    assert record is not None
    assert record.user_id == user_id
    assert record.keep_note_id == keep_note_id
    assert record.notion_page_id == notion_page_id
    
    # Try to retrieve non-existent record
    non_existent = db_ops.get_sync_record(user_id, "non_existent_note")
    assert non_existent is None


def test_store_and_get_credentials(db_ops, encryption_service):
    """Test storing and retrieving encrypted credentials."""
    user_id = "test_user_7"
    google_token = "google_oauth_token_123"
    notion_token = "notion_api_token_456"
    database_id = "notion_db_789"
    
    # Store credentials
    credential = db_ops.store_credentials(
        user_id, google_token, notion_token, database_id, encryption_service
    )
    assert credential.user_id == user_id
    
    # Retrieve and decrypt credentials
    retrieved = db_ops.get_credentials(user_id, encryption_service)
    assert retrieved is not None
    assert retrieved['user_id'] == user_id
    assert retrieved['google_oauth_token'] == google_token
    assert retrieved['notion_api_token'] == notion_token
    assert retrieved['notion_database_id'] == database_id


def test_update_credentials(db_ops, encryption_service):
    """Test updating existing credentials."""
    user_id = "test_user_8"
    
    # Store initial credentials
    db_ops.store_credentials(
        user_id, "old_google_token", "old_notion_token", "old_db_id", encryption_service
    )
    
    # Update credentials
    new_google_token = "new_google_token"
    new_notion_token = "new_notion_token"
    new_db_id = "new_db_id"
    
    db_ops.store_credentials(
        user_id, new_google_token, new_notion_token, new_db_id, encryption_service
    )
    
    # Retrieve and verify
    retrieved = db_ops.get_credentials(user_id, encryption_service)
    assert retrieved['google_oauth_token'] == new_google_token
    assert retrieved['notion_api_token'] == new_notion_token
    assert retrieved['notion_database_id'] == new_db_id


def test_delete_credentials(db_ops, encryption_service):
    """Test deleting credentials."""
    user_id = "test_user_9"
    
    # Store credentials
    db_ops.store_credentials(
        user_id, "token1", "token2", "db_id", encryption_service
    )
    
    # Delete credentials
    result = db_ops.delete_credentials(user_id)
    assert result is True
    
    # Verify deletion
    retrieved = db_ops.get_credentials(user_id, encryption_service)
    assert retrieved is None
    
    # Try to delete non-existent credentials
    result = db_ops.delete_credentials("non_existent_user")
    assert result is False


def test_add_and_get_sync_logs(db_ops):
    """Test adding and retrieving sync logs."""
    job_id = uuid4()
    user_id = "test_user_10"
    
    # Create sync job
    db_ops.create_sync_job(job_id, user_id)
    
    # Add logs
    db_ops.add_sync_log(job_id, "INFO", "Starting sync")
    db_ops.add_sync_log(job_id, "WARNING", "Note failed", keep_note_id="note_1")
    db_ops.add_sync_log(job_id, "ERROR", "Critical error")
    
    # Retrieve logs
    logs = db_ops.get_sync_logs(job_id)
    assert len(logs) == 3
    assert logs[0].level == "INFO"
    assert logs[1].level == "WARNING"
    assert logs[1].keep_note_id == "note_1"
    assert logs[2].level == "ERROR"


def test_encryption_service():
    """Test encryption and decryption."""
    service = EncryptionService()
    
    plaintext = "sensitive_data_123"
    encrypted = service.encrypt(plaintext)
    
    # Verify encrypted is different from plaintext
    assert encrypted != plaintext
    
    # Verify decryption works
    decrypted = service.decrypt(encrypted)
    assert decrypted == plaintext


def test_encryption_empty_string():
    """Test encryption with empty string."""
    service = EncryptionService()
    
    encrypted = service.encrypt("")
    assert encrypted == ""
    
    decrypted = service.decrypt("")
    assert decrypted == ""


# Additional CRUD Tests


def test_get_nonexistent_sync_job(db_ops):
    """Test retrieving a non-existent sync job."""
    non_existent_id = uuid4()
    job = db_ops.get_sync_job(non_existent_id)
    assert job is None


def test_update_nonexistent_sync_job(db_ops):
    """Test updating a non-existent sync job."""
    non_existent_id = uuid4()
    result = db_ops.update_sync_job(non_existent_id, status="running")
    assert result is None


def test_complete_sync_job_workflow(db_ops):
    """Test complete sync job lifecycle from creation to completion."""
    job_id = uuid4()
    user_id = "test_user_workflow"
    
    # Create job
    job = db_ops.create_sync_job(job_id, user_id, full_sync=True)
    assert job.status == "queued"
    
    # Start job
    db_ops.update_sync_job(job_id, status="running", total_notes=100)
    job = db_ops.get_sync_job(job_id)
    assert job.status == "running"
    assert job.total_notes == 100
    
    # Process notes
    for i in range(95):
        db_ops.increment_sync_job_progress(job_id, processed=1, failed=0)
    
    # Some failures
    for i in range(5):
        db_ops.increment_sync_job_progress(job_id, processed=0, failed=1)
    
    job = db_ops.get_sync_job(job_id)
    assert job.processed_notes == 95
    assert job.failed_notes == 5
    
    # Complete job
    completed_time = datetime.utcnow()
    db_ops.update_sync_job(job_id, status="completed", completed_at=completed_time)
    job = db_ops.get_sync_job(job_id)
    assert job.status == "completed"
    assert job.completed_at is not None


def test_failed_sync_job_with_error_message(db_ops):
    """Test sync job failure with error message."""
    job_id = uuid4()
    user_id = "test_user_failed"
    
    db_ops.create_sync_job(job_id, user_id)
    db_ops.update_sync_job(job_id, status="running", total_notes=10)
    
    # Simulate failure
    error_msg = "Network timeout while connecting to Google Keep API"
    db_ops.update_sync_job(
        job_id,
        status="failed",
        error_message=error_msg,
        completed_at=datetime.utcnow()
    )
    
    job = db_ops.get_sync_job(job_id)
    assert job.status == "failed"
    assert job.error_message == error_msg
    assert job.completed_at is not None


def test_sync_jobs_pagination(db_ops):
    """Test pagination of sync jobs."""
    user_id = "test_user_pagination"
    
    # Create 25 jobs
    job_ids = [uuid4() for _ in range(25)]
    for job_id in job_ids:
        db_ops.create_sync_job(job_id, user_id)
    
    # Get first page
    page1 = db_ops.get_sync_jobs_by_user(user_id, limit=10, offset=0)
    assert len(page1) == 10
    
    # Get second page
    page2 = db_ops.get_sync_jobs_by_user(user_id, limit=10, offset=10)
    assert len(page2) == 10
    
    # Get third page
    page3 = db_ops.get_sync_jobs_by_user(user_id, limit=10, offset=20)
    assert len(page3) == 5
    
    # Verify no overlap
    page1_ids = {job.job_id for job in page1}
    page2_ids = {job.job_id for job in page2}
    page3_ids = {job.job_id for job in page3}
    
    assert len(page1_ids & page2_ids) == 0
    assert len(page1_ids & page3_ids) == 0
    assert len(page2_ids & page3_ids) == 0


def test_sync_jobs_ordering(db_ops):
    """Test that sync jobs are ordered by created_at descending."""
    user_id = "test_user_ordering"
    
    # Create jobs with slight delays to ensure different timestamps
    import time
    job_ids = []
    for i in range(5):
        job_id = uuid4()
        db_ops.create_sync_job(job_id, user_id)
        job_ids.append(job_id)
        time.sleep(0.01)  # Small delay to ensure different timestamps
    
    # Retrieve jobs
    jobs = db_ops.get_sync_jobs_by_user(user_id, limit=10)
    
    # Verify ordering (most recent first)
    for i in range(len(jobs) - 1):
        assert jobs[i].created_at >= jobs[i + 1].created_at


# Sync State Query Tests


def test_get_sync_state_empty(db_ops):
    """Test getting sync state for user with no records."""
    user_id = "test_user_no_state"
    states = db_ops.get_sync_state_by_user(user_id)
    assert len(states) == 0


def test_sync_state_multiple_notes(db_ops):
    """Test sync state with multiple notes for same user."""
    user_id = "test_user_multi_notes"
    modified_at = datetime.utcnow()
    
    # Create multiple sync state records
    note_ids = [f"keep_note_{i}" for i in range(10)]
    for note_id in note_ids:
        db_ops.upsert_sync_state(
            user_id, note_id, f"notion_page_{note_id}", modified_at
        )
    
    # Retrieve all states
    states = db_ops.get_sync_state_by_user(user_id)
    assert len(states) == 10
    
    # Verify all notes are present
    retrieved_note_ids = {state.keep_note_id for state in states}
    assert retrieved_note_ids == set(note_ids)


def test_sync_state_multiple_users(db_ops):
    """Test sync state isolation between users."""
    user1 = "test_user_1_isolation"
    user2 = "test_user_2_isolation"
    modified_at = datetime.utcnow()
    
    # Create records for user 1
    for i in range(5):
        db_ops.upsert_sync_state(
            user1, f"note_{i}", f"page_{i}", modified_at
        )
    
    # Create records for user 2
    for i in range(3):
        db_ops.upsert_sync_state(
            user2, f"note_{i}", f"page_{i}", modified_at
        )
    
    # Verify isolation
    user1_states = db_ops.get_sync_state_by_user(user1)
    user2_states = db_ops.get_sync_state_by_user(user2)
    
    assert len(user1_states) == 5
    assert len(user2_states) == 3
    assert all(state.user_id == user1 for state in user1_states)
    assert all(state.user_id == user2 for state in user2_states)


def test_sync_state_upsert_idempotency(db_ops):
    """Test that upserting same record multiple times is idempotent."""
    user_id = "test_user_idempotent"
    keep_note_id = "keep_note_idempotent"
    notion_page_id = "notion_page_idempotent"
    modified_at = datetime.utcnow()
    
    # Insert multiple times
    for _ in range(5):
        db_ops.upsert_sync_state(user_id, keep_note_id, notion_page_id, modified_at)
    
    # Verify only one record exists
    states = db_ops.get_sync_state_by_user(user_id)
    assert len(states) == 1
    assert states[0].keep_note_id == keep_note_id


def test_sync_state_timestamp_tracking(db_ops):
    """Test that sync state tracks timestamps correctly."""
    user_id = "test_user_timestamps"
    keep_note_id = "keep_note_ts"
    notion_page_id = "notion_page_ts"
    
    # First sync
    first_modified = datetime(2024, 1, 1, 12, 0, 0)
    state1 = db_ops.upsert_sync_state(
        user_id, keep_note_id, notion_page_id, first_modified
    )
    assert state1.keep_modified_at == first_modified
    first_synced_at = state1.last_synced_at
    
    # Update after modification
    import time
    time.sleep(0.01)
    second_modified = datetime(2024, 1, 2, 12, 0, 0)
    state2 = db_ops.upsert_sync_state(
        user_id, keep_note_id, notion_page_id, second_modified
    )
    assert state2.keep_modified_at == second_modified
    assert state2.last_synced_at > first_synced_at


# Encryption Tests


def test_encryption_with_special_characters(encryption_service):
    """Test encryption with special characters."""
    special_text = "token!@#$%^&*()_+-=[]{}|;':\",./<>?"
    encrypted = encryption_service.encrypt(special_text)
    decrypted = encryption_service.decrypt(encrypted)
    assert decrypted == special_text


def test_encryption_with_unicode(encryption_service):
    """Test encryption with unicode characters."""
    unicode_text = "Hello 世界 🌍 Привет"
    encrypted = encryption_service.encrypt(unicode_text)
    decrypted = encryption_service.decrypt(encrypted)
    assert decrypted == unicode_text


def test_encryption_with_long_text(encryption_service):
    """Test encryption with long text."""
    long_text = "a" * 10000
    encrypted = encryption_service.encrypt(long_text)
    decrypted = encryption_service.decrypt(encrypted)
    assert decrypted == long_text
    assert len(encrypted) > len(long_text)  # Encrypted should be longer


def test_encryption_different_keys_produce_different_results():
    """Test that different encryption keys produce different results."""
    plaintext = "sensitive_data"
    
    service1 = EncryptionService()
    service2 = EncryptionService()
    
    encrypted1 = service1.encrypt(plaintext)
    encrypted2 = service2.encrypt(plaintext)
    
    # Different keys should produce different ciphertexts
    assert encrypted1 != encrypted2
    
    # Each service can decrypt its own ciphertext
    assert service1.decrypt(encrypted1) == plaintext
    assert service2.decrypt(encrypted2) == plaintext


def test_credentials_encryption_roundtrip(db_ops, encryption_service):
    """Test full encryption roundtrip for credentials."""
    user_id = "test_user_encryption_roundtrip"
    
    # Test with various token formats
    test_cases = [
        ("simple_token", "another_token", "db_123"),
        ("token-with-dashes", "token_with_underscores", "db-456"),
        ("very.long.token.with.many.parts.separated.by.dots", "short", "db_789"),
        ("token!@#$%", "token^&*()", "db_special"),
    ]
    
    for google_token, notion_token, db_id in test_cases:
        # Store credentials
        db_ops.store_credentials(
            user_id, google_token, notion_token, db_id, encryption_service
        )
        
        # Retrieve and verify
        retrieved = db_ops.get_credentials(user_id, encryption_service)
        assert retrieved['google_oauth_token'] == google_token
        assert retrieved['notion_api_token'] == notion_token
        assert retrieved['notion_database_id'] == db_id


def test_credentials_not_stored_as_plaintext(db_ops, encryption_service):
    """Test that credentials are not stored as plaintext in database."""
    user_id = "test_user_plaintext_check"
    google_token = "secret_google_token_123"
    notion_token = "secret_notion_token_456"
    db_id = "db_789"
    
    # Store credentials
    credential = db_ops.store_credentials(
        user_id, google_token, notion_token, db_id, encryption_service
    )
    
    # Verify stored values are encrypted (not equal to plaintext)
    assert credential.google_oauth_token != google_token
    assert credential.notion_api_token != notion_token
    # Database ID is not encrypted
    assert credential.notion_database_id == db_id


# Sync Log Tests


def test_sync_logs_ordering(db_ops):
    """Test that sync logs are ordered by creation time."""
    job_id = uuid4()
    user_id = "test_user_log_ordering"
    
    db_ops.create_sync_job(job_id, user_id)
    
    # Add logs with slight delays
    import time
    messages = ["First log", "Second log", "Third log"]
    for msg in messages:
        db_ops.add_sync_log(job_id, "INFO", msg)
        time.sleep(0.01)
    
    # Retrieve logs
    logs = db_ops.get_sync_logs(job_id)
    
    # Verify ordering (chronological)
    assert len(logs) == 3
    assert logs[0].message == "First log"
    assert logs[1].message == "Second log"
    assert logs[2].message == "Third log"


def test_sync_logs_with_note_id(db_ops):
    """Test sync logs with associated note IDs."""
    job_id = uuid4()
    user_id = "test_user_log_note_id"
    
    db_ops.create_sync_job(job_id, user_id)
    
    # Add logs with and without note IDs
    db_ops.add_sync_log(job_id, "INFO", "Starting sync")
    db_ops.add_sync_log(job_id, "INFO", "Processing note", keep_note_id="note_1")
    db_ops.add_sync_log(job_id, "ERROR", "Failed to process note", keep_note_id="note_2")
    
    logs = db_ops.get_sync_logs(job_id)
    assert len(logs) == 3
    assert logs[0].keep_note_id is None
    assert logs[1].keep_note_id == "note_1"
    assert logs[2].keep_note_id == "note_2"


def test_sync_logs_different_levels(db_ops):
    """Test sync logs with different log levels."""
    job_id = uuid4()
    user_id = "test_user_log_levels"
    
    db_ops.create_sync_job(job_id, user_id)
    
    # Add logs with different levels
    db_ops.add_sync_log(job_id, "INFO", "Info message")
    db_ops.add_sync_log(job_id, "WARNING", "Warning message")
    db_ops.add_sync_log(job_id, "ERROR", "Error message")
    
    logs = db_ops.get_sync_logs(job_id)
    assert len(logs) == 3
    
    levels = {log.level for log in logs}
    assert levels == {"INFO", "WARNING", "ERROR"}


def test_sync_logs_limit(db_ops):
    """Test sync logs retrieval with limit."""
    job_id = uuid4()
    user_id = "test_user_log_limit"
    
    db_ops.create_sync_job(job_id, user_id)
    
    # Add many logs
    for i in range(50):
        db_ops.add_sync_log(job_id, "INFO", f"Log message {i}")
    
    # Retrieve with limit
    logs = db_ops.get_sync_logs(job_id, limit=20)
    assert len(logs) == 20


# Performance Tests


def test_sync_state_query_performance_large_dataset(db_ops):
    """Test sync state query performance with 10,000 notes."""
    import time
    
    user_id = "test_user_performance"
    modified_at = datetime.utcnow()
    
    # Create 10,000 sync state records
    print("\nCreating 10,000 sync state records...")
    start_time = time.time()
    
    for i in range(10000):
        db_ops.upsert_sync_state(
            user_id,
            f"keep_note_{i}",
            f"notion_page_{i}",
            modified_at
        )
    
    creation_time = time.time() - start_time
    print(f"Created 10,000 records in {creation_time:.2f} seconds")
    
    # Query all records and measure time
    query_start = time.time()
    states = db_ops.get_sync_state_by_user(user_id)
    query_time = (time.time() - query_start) * 1000  # Convert to milliseconds
    
    print(f"Query time: {query_time:.2f}ms")
    
    # Verify results
    assert len(states) == 10000
    
    # Requirement: queries should return within 100ms for up to 10,000 notes
    assert query_time < 100, f"Query took {query_time:.2f}ms, expected < 100ms"


def test_sync_record_lookup_performance_large_dataset(db_ops):
    """Test individual sync record lookup performance with large dataset."""
    import time
    
    user_id = "test_user_lookup_performance"
    modified_at = datetime.utcnow()
    
    # Create 10,000 records
    print("\nCreating 10,000 records for lookup test...")
    for i in range(10000):
        db_ops.upsert_sync_state(
            user_id,
            f"keep_note_{i}",
            f"notion_page_{i}",
            modified_at
        )
    
    # Test lookup performance for various records
    lookup_times = []
    test_indices = [0, 100, 1000, 5000, 9999]
    
    for idx in test_indices:
        lookup_start = time.time()
        record = db_ops.get_sync_record(user_id, f"keep_note_{idx}")
        lookup_time = (time.time() - lookup_start) * 1000
        lookup_times.append(lookup_time)
        
        assert record is not None
        assert record.keep_note_id == f"keep_note_{idx}"
    
    avg_lookup_time = sum(lookup_times) / len(lookup_times)
    print(f"Average lookup time: {avg_lookup_time:.2f}ms")
    
    # Individual lookups should be fast (< 10ms)
    assert avg_lookup_time < 10, f"Average lookup took {avg_lookup_time:.2f}ms, expected < 10ms"


def test_sync_jobs_query_performance(db_ops):
    """Test sync jobs query performance with many jobs."""
    import time
    
    user_id = "test_user_jobs_performance"
    
    # Create 1,000 sync jobs
    print("\nCreating 1,000 sync jobs...")
    for i in range(1000):
        job_id = uuid4()
        db_ops.create_sync_job(job_id, user_id)
    
    # Query with pagination
    query_start = time.time()
    jobs = db_ops.get_sync_jobs_by_user(user_id, limit=50, offset=0)
    query_time = (time.time() - query_start) * 1000
    
    print(f"Query time for 50 jobs: {query_time:.2f}ms")
    
    assert len(jobs) == 50
    assert query_time < 100, f"Query took {query_time:.2f}ms, expected < 100ms"


# Edge Cases and Error Handling


def test_increment_progress_on_nonexistent_job(db_ops):
    """Test incrementing progress on non-existent job."""
    non_existent_id = uuid4()
    result = db_ops.increment_sync_job_progress(non_existent_id, processed=1)
    assert result is None


def test_get_credentials_nonexistent_user(db_ops, encryption_service):
    """Test getting credentials for non-existent user."""
    result = db_ops.get_credentials("nonexistent_user", encryption_service)
    assert result is None


def test_sync_state_with_same_note_different_users(db_ops):
    """Test that same note ID can exist for different users."""
    user1 = "test_user_1_same_note"
    user2 = "test_user_2_same_note"
    keep_note_id = "shared_note_id"
    modified_at = datetime.utcnow()
    
    # Create same note ID for different users
    db_ops.upsert_sync_state(user1, keep_note_id, "page_1", modified_at)
    db_ops.upsert_sync_state(user2, keep_note_id, "page_2", modified_at)
    
    # Verify both records exist
    record1 = db_ops.get_sync_record(user1, keep_note_id)
    record2 = db_ops.get_sync_record(user2, keep_note_id)
    
    assert record1 is not None
    assert record2 is not None
    assert record1.notion_page_id == "page_1"
    assert record2.notion_page_id == "page_2"


def test_sync_logs_for_nonexistent_job(db_ops):
    """Test getting logs for non-existent job."""
    non_existent_id = uuid4()
    logs = db_ops.get_sync_logs(non_existent_id)
    assert len(logs) == 0
