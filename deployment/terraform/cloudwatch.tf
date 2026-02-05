# AWS CloudWatch Configuration for Keep-Notion-Sync

# Log Groups for Each Service
resource "aws_cloudwatch_log_group" "api_gateway" {
  name              = "/aws/eks/${var.project_name}/api-gateway"
  retention_in_days = 30

  tags = local.common_tags
}

resource "aws_cloudwatch_log_group" "admin_interface" {
  name              = "/aws/eks/${var.project_name}/admin-interface"
  retention_in_days = 30

  tags = local.common_tags
}

resource "aws_cloudwatch_log_group" "sync_service" {
  name              = "/aws/eks/${var.project_name}/sync-service"
  retention_in_days = 30

  tags = local.common_tags
}

resource "aws_cloudwatch_log_group" "keep_extractor" {
  name              = "/aws/eks/${var.project_name}/keep-extractor"
  retention_in_days = 30

  tags = local.common_tags
}

resource "aws_cloudwatch_log_group" "notion_writer" {
  name              = "/aws/eks/${var.project_name}/notion-writer"
  retention_in_days = 30

  tags = local.common_tags
}

# Log Group for Application Errors
resource "aws_cloudwatch_log_group" "application_errors" {
  name              = "/aws/eks/${var.project_name}/errors"
  retention_in_days = 90

  tags = local.common_tags
}

# Metric Filters for Error Tracking
resource "aws_cloudwatch_log_metric_filter" "api_gateway_errors" {
  name           = "${var.project_name}-api-gateway-errors"
  log_group_name = aws_cloudwatch_log_group.api_gateway.name
  pattern        = "[time, request_id, level = ERROR, ...]"

  metric_transformation {
    name      = "APIGatewayErrors"
    namespace = "KeepNotionSync"
    value     = "1"
    unit      = "Count"
  }
}

resource "aws_cloudwatch_log_metric_filter" "sync_service_errors" {
  name           = "${var.project_name}-sync-service-errors"
  log_group_name = aws_cloudwatch_log_group.sync_service.name
  pattern        = "[time, request_id, level = ERROR, ...]"

  metric_transformation {
    name      = "SyncServiceErrors"
    namespace = "KeepNotionSync"
    value     = "1"
    unit      = "Count"
  }
}

resource "aws_cloudwatch_log_metric_filter" "keep_extractor_errors" {
  name           = "${var.project_name}-keep-extractor-errors"
  log_group_name = aws_cloudwatch_log_group.keep_extractor.name
  pattern        = "[time, request_id, level = ERROR, ...]"

  metric_transformation {
    name      = "KeepExtractorErrors"
    namespace = "KeepNotionSync"
    value     = "1"
    unit      = "Count"
  }
}

resource "aws_cloudwatch_log_metric_filter" "notion_writer_errors" {
  name           = "${var.project_name}-notion-writer-errors"
  log_group_name = aws_cloudwatch_log_group.notion_writer.name
  pattern        = "[time, request_id, level = ERROR, ...]"

  metric_transformation {
    name      = "NotionWriterErrors"
    namespace = "KeepNotionSync"
    value     = "1"
    unit      = "Count"
  }
}

# Metric Filter for Sync Job Completion
resource "aws_cloudwatch_log_metric_filter" "sync_job_completed" {
  name           = "${var.project_name}-sync-job-completed"
  log_group_name = aws_cloudwatch_log_group.sync_service.name
  pattern        = "[time, request_id, level, message = \"Sync job completed\", ...]"

  metric_transformation {
    name      = "SyncJobsCompleted"
    namespace = "KeepNotionSync"
    value     = "1"
    unit      = "Count"
  }
}

resource "aws_cloudwatch_log_metric_filter" "sync_job_failed" {
  name           = "${var.project_name}-sync-job-failed"
  log_group_name = aws_cloudwatch_log_group.sync_service.name
  pattern        = "[time, request_id, level, message = \"Sync job failed\", ...]"

  metric_transformation {
    name      = "SyncJobsFailed"
    namespace = "KeepNotionSync"
    value     = "1"
    unit      = "Count"
  }
}

# CloudWatch Alarms for Application Errors
resource "aws_cloudwatch_metric_alarm" "api_gateway_high_errors" {
  alarm_name          = "${var.project_name}-api-gateway-high-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "APIGatewayErrors"
  namespace           = "KeepNotionSync"
  period              = "300"
  statistic           = "Sum"
  threshold           = "10"
  alarm_description   = "API Gateway error rate is too high"
  treat_missing_data  = "notBreaching"
  alarm_actions       = []  # Add SNS topic ARN for notifications

  tags = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "sync_service_high_errors" {
  alarm_name          = "${var.project_name}-sync-service-high-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "SyncServiceErrors"
  namespace           = "KeepNotionSync"
  period              = "300"
  statistic           = "Sum"
  threshold           = "10"
  alarm_description   = "Sync Service error rate is too high"
  treat_missing_data  = "notBreaching"
  alarm_actions       = []  # Add SNS topic ARN for notifications

  tags = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "sync_job_failure_rate" {
  alarm_name          = "${var.project_name}-sync-job-failure-rate"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "SyncJobsFailed"
  namespace           = "KeepNotionSync"
  period              = "3600"
  statistic           = "Sum"
  threshold           = "5"
  alarm_description   = "Too many sync jobs are failing"
  treat_missing_data  = "notBreaching"
  alarm_actions       = []  # Add SNS topic ARN for notifications

  tags = local.common_tags
}

# CloudWatch Dashboard
resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = "${var.project_name}-dashboard"

  dashboard_body = jsonencode({
    widgets = [
      {
        type = "metric"
        properties = {
          metrics = [
            ["KeepNotionSync", "SyncJobsCompleted", { stat = "Sum", label = "Completed" }],
            [".", "SyncJobsFailed", { stat = "Sum", label = "Failed" }]
          ]
          period = 300
          stat   = "Sum"
          region = var.aws_region
          title  = "Sync Jobs"
          yAxis = {
            left = {
              min = 0
            }
          }
        }
      },
      {
        type = "metric"
        properties = {
          metrics = [
            ["KeepNotionSync", "APIGatewayErrors", { stat = "Sum" }],
            [".", "SyncServiceErrors", { stat = "Sum" }],
            [".", "KeepExtractorErrors", { stat = "Sum" }],
            [".", "NotionWriterErrors", { stat = "Sum" }]
          ]
          period = 300
          stat   = "Sum"
          region = var.aws_region
          title  = "Application Errors by Service"
          yAxis = {
            left = {
              min = 0
            }
          }
        }
      },
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/RDS", "CPUUtilization", { stat = "Average", dimensions = { DBInstanceIdentifier = module.rds.db_instance_identifier } }],
            [".", "DatabaseConnections", { stat = "Average", dimensions = { DBInstanceIdentifier = module.rds.db_instance_identifier } }]
          ]
          period = 300
          stat   = "Average"
          region = var.aws_region
          title  = "RDS Metrics"
          yAxis = {
            left = {
              min = 0
            }
          }
        }
      },
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/S3", "NumberOfObjects", { stat = "Average", dimensions = { BucketName = module.s3.s3_bucket_id, StorageType = "AllStorageTypes" } }],
            [".", "BucketSizeBytes", { stat = "Average", dimensions = { BucketName = module.s3.s3_bucket_id, StorageType = "StandardStorage" } }]
          ]
          period = 86400
          stat   = "Average"
          region = var.aws_region
          title  = "S3 Storage Metrics"
        }
      },
      {
        type = "log"
        properties = {
          query   = "SOURCE '${aws_cloudwatch_log_group.sync_service.name}' | fields @timestamp, @message | filter @message like /ERROR/ | sort @timestamp desc | limit 20"
          region  = var.aws_region
          title   = "Recent Errors"
        }
      }
    ]
  })
}

# SNS Topic for Alarms (Optional - uncomment to enable)
# resource "aws_sns_topic" "alarms" {
#   name = "${var.project_name}-alarms"
#   
#   tags = local.common_tags
# }
#
# resource "aws_sns_topic_subscription" "alarms_email" {
#   topic_arn = aws_sns_topic.alarms.arn
#   protocol  = "email"
#   endpoint  = "your-email@example.com"
# }

# Outputs
output "cloudwatch_log_groups" {
  description = "CloudWatch log group names"
  value = {
    api_gateway     = aws_cloudwatch_log_group.api_gateway.name
    admin_interface = aws_cloudwatch_log_group.admin_interface.name
    sync_service    = aws_cloudwatch_log_group.sync_service.name
    keep_extractor  = aws_cloudwatch_log_group.keep_extractor.name
    notion_writer   = aws_cloudwatch_log_group.notion_writer.name
  }
}

output "cloudwatch_dashboard_url" {
  description = "CloudWatch dashboard URL"
  value       = "https://console.aws.amazon.com/cloudwatch/home?region=${var.aws_region}#dashboards:name=${aws_cloudwatch_dashboard.main.dashboard_name}"
}
