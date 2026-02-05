# Temporary Image Cleanup Configuration

This document describes the implementation of automatic cleanup for temporary images stored in S3 during the sync process.

## Overview

The Keep-Notion-Sync application temporarily stores images in S3 during the sync process:
1. Keep Extractor downloads images from Google Keep
2. Images are uploaded to S3
3. Notion Writer downloads images from S3 and uploads to Notion
4. Images should be deleted from S3 after successful upload to Notion

## Cleanup Strategies

### Strategy 1: S3 Lifecycle Rules (Primary)

S3 lifecycle rules automatically delete objects after a specified period. This is the most reliable method as it doesn't depend on application logic.

#### Configuration (Already in Terraform)

The lifecycle rule is configured in `deployment/terraform/s3.tf`:

```hcl
lifecycle_rule = [
  {
    id      = "delete-old-images"
    enabled = true
    
    expiration = {
      days = 7  # Delete images after 7 days
    }
    
    noncurrent_version_expiration = {
      days = 1
    }
    
    abort_incomplete_multipart_upload = {
      days_after_initiation = 1
    }
  }
]
```

#### Manual Configuration

If not using Terraform, configure via AWS CLI:

```bash
aws s3api put-bucket-lifecycle-configuration \
  --bucket keep-notion-sync-images-ACCOUNT_ID \
  --lifecycle-configuration '{
    "Rules": [
      {
        "Id": "delete-old-images",
        "Status": "Enabled",
        "Expiration": {
          "Days": 7
        },
        "NoncurrentVersionExpiration": {
          "NoncurrentDays": 1
        },
        "AbortIncompleteMultipartUpload": {
          "DaysAfterInitiation": 1
        }
      }
    ]
  }'
```

### Strategy 2: Application-Level Cleanup (Secondary)

Implement cleanup in the Notion Writer service after successful upload.

#### Implementation

Create `services/notion_writer/cleanup.py`:

```python
import boto3
import logging
from typing import List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class ImageCleanup:
    """Handle cleanup of temporary images from S3"""
    
    def __init__(self, s3_client=None, bucket_name: str = None):
        self.s3_client = s3_client or boto3.client('s3')
        self.bucket_name = bucket_name or os.getenv('S3_BUCKET_NAME')
    
    async def cleanup_after_upload(self, s3_urls: List[str]) -> dict:
        """
        Delete images from S3 after successful upload to Notion
        
        Args:
            s3_urls: List of S3 URLs to delete
        
        Returns:
            Dictionary with cleanup results
        """
        results = {
            'deleted': 0,
            'failed': 0,
            'errors': []
        }
        
        for s3_url in s3_urls:
            try:
                # Extract key from URL
                # Format: https://bucket.s3.region.amazonaws.com/key
                # or: s3://bucket/key
                key = self._extract_key_from_url(s3_url)
                
                # Delete object
                self.s3_client.delete_object(
                    Bucket=self.bucket_name,
                    Key=key
                )
                
                results['deleted'] += 1
                logger.info(f"Deleted temporary image: {key}")
                
            except Exception as e:
                results['failed'] += 1
                results['errors'].append({
                    'url': s3_url,
                    'error': str(e)
                })
                logger.error(f"Failed to delete image {s3_url}: {e}")
        
        return results
    
    def _extract_key_from_url(self, s3_url: str) -> str:
        """Extract S3 key from URL"""
        from urllib.parse import urlparse
        
        if s3_url.startswith('s3://'):
            # s3://bucket/key format
            parsed = urlparse(s3_url)
            return parsed.path.lstrip('/')
        else:
            # https://bucket.s3.region.amazonaws.com/key format
            parsed = urlparse(s3_url)
            return parsed.path.lstrip('/')
    
    async def cleanup_old_images(self, days: int = 7) -> dict:
        """
        Delete images older than specified days
        
        Args:
            days: Delete images older than this many days
        
        Returns:
            Dictionary with cleanup results
        """
        results = {
            'deleted': 0,
            'failed': 0,
            'errors': []
        }
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        try:
            # List objects in bucket
            paginator = self.s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=self.bucket_name)
            
            for page in pages:
                if 'Contents' not in page:
                    continue
                
                for obj in page['Contents']:
                    # Check if object is older than cutoff
                    if obj['LastModified'].replace(tzinfo=None) < cutoff_date:
                        try:
                            self.s3_client.delete_object(
                                Bucket=self.bucket_name,
                                Key=obj['Key']
                            )
                            results['deleted'] += 1
                            logger.info(f"Deleted old image: {obj['Key']}")
                        except Exception as e:
                            results['failed'] += 1
                            results['errors'].append({
                                'key': obj['Key'],
                                'error': str(e)
                            })
                            logger.error(f"Failed to delete {obj['Key']}: {e}")
        
        except Exception as e:
            logger.error(f"Failed to list objects: {e}")
            results['errors'].append({
                'operation': 'list_objects',
                'error': str(e)
            })
        
        return results
```

#### Usage in Notion Writer

Update `services/notion_writer/writer.py`:

```python
from .cleanup import ImageCleanup

class NotionWriter:
    def __init__(self, s3_client):
        self.s3_client = s3_client
        self.cleanup = ImageCleanup(s3_client)
    
    async def create_page(self, api_token: str, database_id: str, note: dict):
        """Create a new Notion page with automatic cleanup"""
        from notion_client import Client
        notion = Client(auth=api_token)
        
        # Track S3 URLs for cleanup
        s3_urls = [img['s3_url'] for img in note.get('images', [])]
        
        try:
            # Create page with images
            response = notion.pages.create(
                parent={"database_id": database_id},
                properties=self._build_properties(note),
                children=self._build_children(note)
            )
            
            # Cleanup images after successful upload
            if s3_urls:
                cleanup_results = await self.cleanup.cleanup_after_upload(s3_urls)
                logger.info(
                    f"Cleanup completed: {cleanup_results['deleted']} deleted, "
                    f"{cleanup_results['failed']} failed"
                )
            
            return {
                "page_id": response["id"],
                "url": response["url"]
            }
            
        except Exception as e:
            # Don't cleanup on failure - images might be needed for retry
            logger.error(f"Failed to create page, keeping images for retry: {e}")
            raise
```

### Strategy 3: Scheduled Cleanup Job (Tertiary)

Run a periodic cleanup job using Kubernetes CronJob.

#### Kubernetes CronJob Configuration

Create `deployment/kubernetes/cleanup-cronjob.yaml`:

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: s3-image-cleanup
  namespace: keep-notion-sync
spec:
  # Run daily at 2 AM
  schedule: "0 2 * * *"
  successfulJobsHistoryLimit: 3
  failedJobsHistoryLimit: 3
  concurrencyPolicy: Forbid
  jobTemplate:
    spec:
      template:
        metadata:
          labels:
            app: s3-cleanup
        spec:
          serviceAccountName: keep-notion-sync-sa
          restartPolicy: OnFailure
          containers:
          - name: cleanup
            image: ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/keep-notion-sync/notion-writer:latest
            command:
            - python
            - -c
            - |
              import asyncio
              import os
              from cleanup import ImageCleanup
              
              async def main():
                  cleanup = ImageCleanup()
                  days = int(os.getenv('CLEANUP_DAYS', '7'))
                  results = await cleanup.cleanup_old_images(days)
                  print(f"Cleanup completed: {results}")
              
              asyncio.run(main())
            env:
            - name: S3_BUCKET_NAME
              valueFrom:
                configMapKeyRef:
                  name: keep-notion-sync-config
                  key: S3_BUCKET_NAME
            - name: AWS_REGION
              valueFrom:
                configMapKeyRef:
                  name: keep-notion-sync-config
                  key: AWS_REGION
            - name: CLEANUP_DAYS
              value: "7"
            resources:
              requests:
                memory: "128Mi"
                cpu: "100m"
              limits:
                memory: "256Mi"
                cpu: "200m"
```

Deploy the CronJob:

```bash
kubectl apply -f deployment/kubernetes/cleanup-cronjob.yaml
```

#### Manual Cleanup Script

Create `deployment/scripts/cleanup-s3-images.sh`:

```bash
#!/bin/bash
# Manual S3 Image Cleanup Script
# Usage: ./cleanup-s3-images.sh [BUCKET_NAME] [DAYS]

set -e

BUCKET_NAME=${1:-keep-notion-sync-images}
DAYS=${2:-7}
AWS_REGION=${AWS_REGION:-us-east-1}

echo "Cleaning up images older than $DAYS days from bucket: $BUCKET_NAME"

# Calculate cutoff date
CUTOFF_DATE=$(date -u -d "$DAYS days ago" +%Y-%m-%dT%H:%M:%S)

echo "Cutoff date: $CUTOFF_DATE"

# List and delete old objects
aws s3api list-objects-v2 \
  --bucket $BUCKET_NAME \
  --region $AWS_REGION \
  --query "Contents[?LastModified<'$CUTOFF_DATE'].Key" \
  --output text | \
while read -r key; do
  if [ -n "$key" ]; then
    echo "Deleting: $key"
    aws s3api delete-object \
      --bucket $BUCKET_NAME \
      --key "$key" \
      --region $AWS_REGION
  fi
done

echo "Cleanup completed!"
```

Make it executable:

```bash
chmod +x deployment/scripts/cleanup-s3-images.sh
```

## Monitoring Cleanup

### CloudWatch Metrics

Track cleanup operations:

```python
import boto3

cloudwatch = boto3.client('cloudwatch')

def publish_cleanup_metrics(results: dict):
    """Publish cleanup metrics to CloudWatch"""
    cloudwatch.put_metric_data(
        Namespace='KeepNotionSync',
        MetricData=[
            {
                'MetricName': 'ImagesDeleted',
                'Value': results['deleted'],
                'Unit': 'Count'
            },
            {
                'MetricName': 'ImageDeletionFailures',
                'Value': results['failed'],
                'Unit': 'Count'
            }
        ]
    )
```

### CloudWatch Alarms

Create alarm for cleanup failures:

```hcl
resource "aws_cloudwatch_metric_alarm" "cleanup_failures" {
  alarm_name          = "keep-notion-sync-cleanup-failures"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "ImageDeletionFailures"
  namespace           = "KeepNotionSync"
  period              = "86400"  # Daily
  statistic           = "Sum"
  threshold           = "10"
  alarm_description   = "Alert when image cleanup has too many failures"
  alarm_actions       = []  # Add SNS topic ARN
  
  tags = local.common_tags
}
```

### S3 Metrics

Monitor S3 bucket size:

```bash
# Get bucket size
aws cloudwatch get-metric-statistics \
  --namespace AWS/S3 \
  --metric-name BucketSizeBytes \
  --dimensions Name=BucketName,Value=keep-notion-sync-images Name=StorageType,Value=StandardStorage \
  --start-time $(date -u -d '1 day ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 86400 \
  --statistics Average

# Get number of objects
aws cloudwatch get-metric-statistics \
  --namespace AWS/S3 \
  --metric-name NumberOfObjects \
  --dimensions Name=BucketName,Value=keep-notion-sync-images Name=StorageType,Value=AllStorageTypes \
  --start-time $(date -u -d '1 day ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 86400 \
  --statistics Average
```

## Testing Cleanup

### Unit Tests

Create `services/notion_writer/test_cleanup.py`:

```python
import pytest
from unittest.mock import Mock, patch
from cleanup import ImageCleanup
from datetime import datetime, timedelta

@pytest.fixture
def cleanup():
    s3_client = Mock()
    return ImageCleanup(s3_client=s3_client, bucket_name='test-bucket')

@pytest.mark.asyncio
async def test_cleanup_after_upload(cleanup):
    """Test cleanup after successful upload"""
    s3_urls = [
        's3://test-bucket/keep-images/note1/image1.jpg',
        's3://test-bucket/keep-images/note1/image2.jpg'
    ]
    
    results = await cleanup.cleanup_after_upload(s3_urls)
    
    assert results['deleted'] == 2
    assert results['failed'] == 0
    assert cleanup.s3_client.delete_object.call_count == 2

@pytest.mark.asyncio
async def test_cleanup_old_images(cleanup):
    """Test cleanup of old images"""
    # Mock list_objects_v2 response
    old_date = datetime.now() - timedelta(days=10)
    recent_date = datetime.now() - timedelta(days=1)
    
    cleanup.s3_client.get_paginator.return_value.paginate.return_value = [
        {
            'Contents': [
                {'Key': 'old-image.jpg', 'LastModified': old_date},
                {'Key': 'recent-image.jpg', 'LastModified': recent_date}
            ]
        }
    ]
    
    results = await cleanup.cleanup_old_images(days=7)
    
    # Should only delete old image
    assert results['deleted'] == 1
    assert cleanup.s3_client.delete_object.call_count == 1
```

### Integration Test

```bash
# Upload test image
aws s3 cp test-image.jpg s3://keep-notion-sync-images/test/test-image.jpg

# Wait for lifecycle rule (or run manual cleanup)
sleep 10

# Verify cleanup (should fail if lifecycle is working)
aws s3 ls s3://keep-notion-sync-images/test/
```

## Best Practices

1. **Multiple Layers**: Use both S3 lifecycle rules and application cleanup
2. **Graceful Failure**: Don't fail sync if cleanup fails
3. **Retry Logic**: Keep images if Notion upload fails for retry
4. **Monitoring**: Track cleanup metrics and failures
5. **Cost Optimization**: Shorter retention = lower costs
6. **Compliance**: Ensure cleanup meets data retention requirements

## Troubleshooting

### Images Not Being Deleted

1. **Check lifecycle rule**:
   ```bash
   aws s3api get-bucket-lifecycle-configuration \
     --bucket keep-notion-sync-images
   ```

2. **Verify IAM permissions**:
   - Service account needs `s3:DeleteObject` permission

3. **Check CronJob logs**:
   ```bash
   kubectl logs -l app=s3-cleanup -n keep-notion-sync
   ```

### High S3 Costs

1. **Check bucket size**:
   ```bash
   aws s3 ls s3://keep-notion-sync-images --recursive --summarize
   ```

2. **Reduce retention period**: Change lifecycle rule to 3-5 days

3. **Enable S3 Intelligent-Tiering**: For cost optimization

## Security Considerations

1. **Least Privilege**: Grant only `s3:DeleteObject` permission
2. **Audit Logging**: Enable S3 access logging
3. **Versioning**: Disable versioning for temporary storage
4. **Encryption**: Images are encrypted at rest (configured in S3 module)

## Additional Resources

- [S3 Lifecycle Configuration](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lifecycle-mgmt.html)
- [Kubernetes CronJobs](https://kubernetes.io/docs/concepts/workloads/controllers/cron-jobs/)
- [S3 Cost Optimization](https://aws.amazon.com/s3/cost-optimization/)
