"""AWS S3 client for image storage."""

import logging
from typing import Optional

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class S3Client:
    """Handles S3 operations for image storage."""
    
    def __init__(
        self,
        bucket_name: str,
        region: str = "us-east-1",
        access_key_id: Optional[str] = None,
        secret_access_key: Optional[str] = None
    ):
        """
        Initialize S3 client.
        
        Args:
            bucket_name: S3 bucket name
            region: AWS region
            access_key_id: AWS access key ID (optional, uses default credentials if not provided)
            secret_access_key: AWS secret access key (optional)
        """
        self.bucket_name = bucket_name
        self.region = region
        
        # Initialize boto3 S3 client
        if access_key_id and secret_access_key:
            self.s3_client = boto3.client(
                's3',
                region_name=region,
                aws_access_key_id=access_key_id,
                aws_secret_access_key=secret_access_key
            )
        else:
            # Use default credentials (from environment or IAM role)
            self.s3_client = boto3.client('s3', region_name=region)
    
    async def upload_image(
        self,
        image_data: bytes,
        key: str,
        content_type: str = "image/jpeg"
    ) -> str:
        """
        Upload image to S3 with public read access.
        
        Args:
            image_data: Image binary data
            key: S3 object key (path)
            content_type: MIME type of the image
            
        Returns:
            S3 URL of the uploaded image
        """
        try:
            # Upload to S3 with public-read ACL so Notion can access the images
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=image_data,
                ContentType=content_type,
                ACL='public-read'  # Make images publicly accessible
            )
            
            # Generate S3 URL
            s3_url = f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{key}"
            
            logger.info(f"Successfully uploaded image to S3: {s3_url}")
            return s3_url
        
        except ClientError as e:
            logger.error(f"Failed to upload image to S3: {e}", exc_info=True)
            raise
    
    async def delete_image(self, key: str) -> bool:
        """
        Delete image from S3.
        
        Args:
            key: S3 object key (path)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=key
            )
            logger.info(f"Successfully deleted image from S3: {key}")
            return True
        
        except ClientError as e:
            logger.error(f"Failed to delete image from S3: {e}", exc_info=True)
            return False
    
    def generate_presigned_url(self, key: str, expiration: int = 3600) -> str:
        """
        Generate a presigned URL for temporary access to an S3 object.
        
        Args:
            key: S3 object key (path)
            expiration: URL expiration time in seconds (default: 1 hour)
            
        Returns:
            Presigned URL
        """
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': key},
                ExpiresIn=expiration
            )
            return url
        
        except ClientError as e:
            logger.error(f"Failed to generate presigned URL: {e}", exc_info=True)
            raise
