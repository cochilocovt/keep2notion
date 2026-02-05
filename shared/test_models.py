"""Unit tests for shared data models."""

import json
from dataclasses import asdict
from datetime import datetime

import pytest

from shared.models import (
    ImageAttachment,
    KeepNote,
    SyncJobRequest,
    SyncJobStatus,
    SyncStateRecord,
)


class TestImageAttachment:
    """Tests for ImageAttachment dataclass."""

    def test_create_image_attachment(self):
        """Test creating an ImageAttachment instance."""
        image = ImageAttachment(
            id="img123",
            s3_url="https://s3.amazonaws.com/bucket/image.jpg",
            filename="image.jpg"
        )
        
        assert image.id == "img123"
        assert image.s3_url == "https://s3.amazonaws.com/bucket/image.jpg"
        assert image.filename == "image.jpg"

    def test_image_attachment_serialization(self):
        """Test serializing ImageAttachment to dict."""
        image = ImageAttachment(
            id="img456",
            s3_url="https://s3.amazonaws.com/bucket/photo.png",
            filename="photo.png"
        )
        
        data = asdict(image)
        
        assert data == {
            "id": "img456",
            "s3_url": "https://s3.amazonaws.com/bucket/photo.png",
            "filename": "photo.png"
        }

    def test_image_attachment_deserialization(self):
        """Test deserializing dict to ImageAttachment."""
        data = {
            "id": "img789",
            "s3_url": "https://s3.amazonaws.com/bucket/pic.jpg",
            "filename": "pic.jpg"
        }
        
        image = ImageAttachment(**data)
        
        assert image.id == "img789"
        assert image.s3_url == "https://s3.amazonaws.com/bucket/pic.jpg"
        assert image.filename == "pic.jpg"


class TestKeepNote:
    """Tests for KeepNote dataclass."""

    def test_create_keep_note(self):
        """Test creating a KeepNote instance."""
        created = datetime(2024, 1, 1, 10, 0, 0)
        modified = datetime(2024, 1, 2, 15, 30, 0)
        
        note = KeepNote(
            id="note123",
            title="Test Note",
            content="This is a test note",
            created_at=created,
            modified_at=modified,
            labels=["work", "important"],
            images=[]
        )
        
        assert note.id == "note123"
        assert note.title == "Test Note"
        assert note.content == "This is a test note"
        assert note.created_at == created
        assert note.modified_at == modified
        assert note.labels == ["work", "important"]
        assert note.images == []

    def test_keep_note_with_images(self):
        """Test creating a KeepNote with images."""
        image1 = ImageAttachment(
            id="img1",
            s3_url="https://s3.amazonaws.com/bucket/img1.jpg",
            filename="img1.jpg"
        )
        image2 = ImageAttachment(
            id="img2",
            s3_url="https://s3.amazonaws.com/bucket/img2.jpg",
            filename="img2.jpg"
        )
        
        note = KeepNote(
            id="note456",
            title="Note with Images",
            content="Content",
            created_at=datetime(2024, 1, 1, 10, 0, 0),
            modified_at=datetime(2024, 1, 1, 10, 0, 0),
            labels=[],
            images=[image1, image2]
        )
        
        assert len(note.images) == 2
        assert note.images[0].id == "img1"
        assert note.images[1].id == "img2"

    def test_keep_note_serialization(self):
        """Test serializing KeepNote to dict."""
        created = datetime(2024, 1, 1, 10, 0, 0)
        modified = datetime(2024, 1, 2, 15, 30, 0)
        
        image = ImageAttachment(
            id="img1",
            s3_url="https://s3.amazonaws.com/bucket/img1.jpg",
            filename="img1.jpg"
        )
        
        note = KeepNote(
            id="note789",
            title="Serialization Test",
            content="Test content",
            created_at=created,
            modified_at=modified,
            labels=["test"],
            images=[image]
        )
        
        data = asdict(note)
        
        assert data["id"] == "note789"
        assert data["title"] == "Serialization Test"
        assert data["content"] == "Test content"
        assert data["created_at"] == created
        assert data["modified_at"] == modified
        assert data["labels"] == ["test"]
        assert len(data["images"]) == 1
        assert data["images"][0]["id"] == "img1"

    def test_keep_note_deserialization(self):
        """Test deserializing dict to KeepNote."""
        created = datetime(2024, 1, 1, 10, 0, 0)
        modified = datetime(2024, 1, 2, 15, 30, 0)
        
        data = {
            "id": "note999",
            "title": "Deserialization Test",
            "content": "Test content",
            "created_at": created,
            "modified_at": modified,
            "labels": ["label1", "label2"],
            "images": [
                {
                    "id": "img1",
                    "s3_url": "https://s3.amazonaws.com/bucket/img1.jpg",
                    "filename": "img1.jpg"
                }
            ]
        }
        
        # Deserialize images first
        images = [ImageAttachment(**img) for img in data["images"]]
        data["images"] = images
        
        note = KeepNote(**data)
        
        assert note.id == "note999"
        assert note.title == "Deserialization Test"
        assert note.content == "Test content"
        assert note.created_at == created
        assert note.modified_at == modified
        assert note.labels == ["label1", "label2"]
        assert len(note.images) == 1
        assert note.images[0].id == "img1"


class TestSyncJobRequest:
    """Tests for SyncJobRequest dataclass."""

    def test_create_sync_job_request(self):
        """Test creating a SyncJobRequest instance."""
        request = SyncJobRequest(
            user_id="user123",
            full_sync=True
        )
        
        assert request.user_id == "user123"
        assert request.full_sync is True

    def test_sync_job_request_incremental(self):
        """Test creating an incremental sync request."""
        request = SyncJobRequest(
            user_id="user456",
            full_sync=False
        )
        
        assert request.user_id == "user456"
        assert request.full_sync is False

    def test_sync_job_request_serialization(self):
        """Test serializing SyncJobRequest to dict."""
        request = SyncJobRequest(
            user_id="user789",
            full_sync=True
        )
        
        data = asdict(request)
        
        assert data == {
            "user_id": "user789",
            "full_sync": True
        }

    def test_sync_job_request_deserialization(self):
        """Test deserializing dict to SyncJobRequest."""
        data = {
            "user_id": "user999",
            "full_sync": False
        }
        
        request = SyncJobRequest(**data)
        
        assert request.user_id == "user999"
        assert request.full_sync is False


class TestSyncJobStatus:
    """Tests for SyncJobStatus dataclass."""

    def test_create_sync_job_status_queued(self):
        """Test creating a queued SyncJobStatus."""
        created = datetime(2024, 1, 1, 10, 0, 0)
        
        status = SyncJobStatus(
            job_id="job123",
            status="queued",
            progress={},
            created_at=created,
            completed_at=None,
            error_message=None
        )
        
        assert status.job_id == "job123"
        assert status.status == "queued"
        assert status.progress == {}
        assert status.created_at == created
        assert status.completed_at is None
        assert status.error_message is None

    def test_create_sync_job_status_completed(self):
        """Test creating a completed SyncJobStatus."""
        created = datetime(2024, 1, 1, 10, 0, 0)
        completed = datetime(2024, 1, 1, 10, 30, 0)
        
        status = SyncJobStatus(
            job_id="job456",
            status="completed",
            progress={
                "total_notes": 100,
                "processed_notes": 100,
                "failed_notes": 0
            },
            created_at=created,
            completed_at=completed,
            error_message=None
        )
        
        assert status.job_id == "job456"
        assert status.status == "completed"
        assert status.progress["total_notes"] == 100
        assert status.progress["processed_notes"] == 100
        assert status.progress["failed_notes"] == 0
        assert status.completed_at == completed
        assert status.error_message is None

    def test_create_sync_job_status_failed(self):
        """Test creating a failed SyncJobStatus."""
        created = datetime(2024, 1, 1, 10, 0, 0)
        completed = datetime(2024, 1, 1, 10, 15, 0)
        
        status = SyncJobStatus(
            job_id="job789",
            status="failed",
            progress={
                "total_notes": 50,
                "processed_notes": 25,
                "failed_notes": 25
            },
            created_at=created,
            completed_at=completed,
            error_message="Network error occurred"
        )
        
        assert status.job_id == "job789"
        assert status.status == "failed"
        assert status.error_message == "Network error occurred"

    def test_sync_job_status_serialization(self):
        """Test serializing SyncJobStatus to dict."""
        created = datetime(2024, 1, 1, 10, 0, 0)
        completed = datetime(2024, 1, 1, 10, 30, 0)
        
        status = SyncJobStatus(
            job_id="job999",
            status="completed",
            progress={"total_notes": 10},
            created_at=created,
            completed_at=completed,
            error_message=None
        )
        
        data = asdict(status)
        
        assert data["job_id"] == "job999"
        assert data["status"] == "completed"
        assert data["progress"] == {"total_notes": 10}
        assert data["created_at"] == created
        assert data["completed_at"] == completed
        assert data["error_message"] is None

    def test_sync_job_status_deserialization(self):
        """Test deserializing dict to SyncJobStatus."""
        created = datetime(2024, 1, 1, 10, 0, 0)
        
        data = {
            "job_id": "job111",
            "status": "running",
            "progress": {"total_notes": 50, "processed_notes": 25},
            "created_at": created,
            "completed_at": None,
            "error_message": None
        }
        
        status = SyncJobStatus(**data)
        
        assert status.job_id == "job111"
        assert status.status == "running"
        assert status.progress["total_notes"] == 50
        assert status.progress["processed_notes"] == 25
        assert status.completed_at is None


class TestSyncStateRecord:
    """Tests for SyncStateRecord dataclass."""

    def test_create_sync_state_record(self):
        """Test creating a SyncStateRecord instance."""
        last_synced = datetime(2024, 1, 1, 10, 0, 0)
        keep_modified = datetime(2024, 1, 1, 9, 0, 0)
        
        record = SyncStateRecord(
            user_id="user123",
            keep_note_id="note123",
            notion_page_id="page123",
            last_synced_at=last_synced,
            keep_modified_at=keep_modified
        )
        
        assert record.user_id == "user123"
        assert record.keep_note_id == "note123"
        assert record.notion_page_id == "page123"
        assert record.last_synced_at == last_synced
        assert record.keep_modified_at == keep_modified

    def test_sync_state_record_serialization(self):
        """Test serializing SyncStateRecord to dict."""
        last_synced = datetime(2024, 1, 1, 10, 0, 0)
        keep_modified = datetime(2024, 1, 1, 9, 0, 0)
        
        record = SyncStateRecord(
            user_id="user456",
            keep_note_id="note456",
            notion_page_id="page456",
            last_synced_at=last_synced,
            keep_modified_at=keep_modified
        )
        
        data = asdict(record)
        
        assert data == {
            "user_id": "user456",
            "keep_note_id": "note456",
            "notion_page_id": "page456",
            "last_synced_at": last_synced,
            "keep_modified_at": keep_modified
        }

    def test_sync_state_record_deserialization(self):
        """Test deserializing dict to SyncStateRecord."""
        last_synced = datetime(2024, 1, 1, 10, 0, 0)
        keep_modified = datetime(2024, 1, 1, 9, 0, 0)
        
        data = {
            "user_id": "user789",
            "keep_note_id": "note789",
            "notion_page_id": "page789",
            "last_synced_at": last_synced,
            "keep_modified_at": keep_modified
        }
        
        record = SyncStateRecord(**data)
        
        assert record.user_id == "user789"
        assert record.keep_note_id == "note789"
        assert record.notion_page_id == "page789"
        assert record.last_synced_at == last_synced
        assert record.keep_modified_at == keep_modified
