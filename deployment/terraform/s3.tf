# S3 Module for Keep-Notion-Sync Image Storage

module "s3" {
  source  = "terraform-aws-modules/s3-bucket/aws"
  version = "~> 3.0"

  bucket = "${var.s3_bucket_name}-${local.account_id}"
  
  # Block public access
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true

  # Versioning
  versioning = {
    enabled = false  # Not needed for temporary image storage
  }

  # Server-side encryption
  server_side_encryption_configuration = {
    rule = {
      apply_server_side_encryption_by_default = {
        sse_algorithm = "AES256"
      }
      bucket_key_enabled = true
    }
  }

  # Lifecycle rules for automatic cleanup
  lifecycle_rule = [
    {
      id      = "delete-old-images"
      enabled = true
      
      expiration = {
        days = var.s3_lifecycle_expiration_days
      }
      
      noncurrent_version_expiration = {
        days = 1
      }
      
      abort_incomplete_multipart_upload = {
        days_after_initiation = 1
      }
    }
  ]

  # CORS configuration for potential web uploads
  cors_rule = [
    {
      allowed_headers = ["*"]
      allowed_methods = ["GET", "PUT", "POST"]
      allowed_origins = ["*"]  # Restrict this in production
      expose_headers  = ["ETag"]
      max_age_seconds = 3000
    }
  ]

  # Logging
  logging = {
    target_bucket = aws_s3_bucket.logs.id
    target_prefix = "s3-access-logs/"
  }

  tags = local.common_tags
}

# S3 Bucket for Access Logs
resource "aws_s3_bucket" "logs" {
  bucket = "${var.s3_bucket_name}-logs-${local.account_id}"

  tags = merge(
    local.common_tags,
    {
      Name = "${var.project_name}-logs"
    }
  )
}

resource "aws_s3_bucket_lifecycle_configuration" "logs" {
  bucket = aws_s3_bucket.logs.id

  rule {
    id     = "delete-old-logs"
    status = "Enabled"

    expiration {
      days = 90
    }
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "logs" {
  bucket = aws_s3_bucket.logs.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "logs" {
  bucket = aws_s3_bucket.logs.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# IAM Policy for S3 Access
resource "aws_iam_policy" "s3_access" {
  name        = "${var.project_name}-s3-access"
  description = "Policy for Keep-Notion-Sync services to access S3 bucket"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          module.s3.s3_bucket_arn,
          "${module.s3.s3_bucket_arn}/*"
        ]
      }
    ]
  })

  tags = local.common_tags
}

# CloudWatch Alarms for S3
resource "aws_cloudwatch_metric_alarm" "s3_4xx_errors" {
  alarm_name          = "${var.project_name}-s3-4xx-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "4xxErrors"
  namespace           = "AWS/S3"
  period              = "300"
  statistic           = "Sum"
  threshold           = "10"
  alarm_description   = "This metric monitors S3 4xx errors"
  alarm_actions       = []  # Add SNS topic ARN for notifications

  dimensions = {
    BucketName = module.s3.s3_bucket_id
  }

  tags = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "s3_5xx_errors" {
  alarm_name          = "${var.project_name}-s3-5xx-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "5xxErrors"
  namespace           = "AWS/S3"
  period              = "300"
  statistic           = "Sum"
  threshold           = "5"
  alarm_description   = "This metric monitors S3 5xx errors"
  alarm_actions       = []  # Add SNS topic ARN for notifications

  dimensions = {
    BucketName = module.s3.s3_bucket_id
  }

  tags = local.common_tags
}

# Outputs
output "s3_bucket_id" {
  description = "S3 bucket ID"
  value       = module.s3.s3_bucket_id
}

output "s3_bucket_regional_domain_name" {
  description = "S3 bucket regional domain name"
  value       = module.s3.s3_bucket_bucket_regional_domain_name
}

output "s3_access_policy_arn" {
  description = "IAM policy ARN for S3 access"
  value       = aws_iam_policy.s3_access.arn
}
