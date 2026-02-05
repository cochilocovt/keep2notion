# AWS Secrets Manager Configuration for Keep-Notion-Sync

# Random password generation for encryption key
resource "random_password" "encryption_key" {
  length  = 32
  special = true
}

# Database Credentials Secret
resource "aws_secretsmanager_secret" "db_credentials" {
  name        = "${var.project_name}/db-credentials"
  description = "Database credentials for Keep-Notion-Sync"
  
  recovery_window_in_days = 7

  tags = local.common_tags
}

resource "aws_secretsmanager_secret_version" "db_credentials" {
  secret_id = aws_secretsmanager_secret.db_credentials.id
  
  secret_string = jsonencode({
    username = var.db_username
    password = var.db_password
    host     = module.rds.db_instance_address
    port     = module.rds.db_instance_port
    dbname   = var.db_name
    engine   = "postgres"
  })
}

# Encryption Key Secret (for credential encryption in application)
resource "aws_secretsmanager_secret" "encryption_key" {
  name        = "${var.project_name}/encryption-key"
  description = "AES-256 encryption key for credential encryption"
  
  recovery_window_in_days = 7

  tags = local.common_tags
}

resource "aws_secretsmanager_secret_version" "encryption_key" {
  secret_id = aws_secretsmanager_secret.encryption_key.id
  
  secret_string = jsonencode({
    key = random_password.encryption_key.result
  })
}

# Django Secret Key
resource "random_password" "django_secret" {
  length  = 50
  special = true
}

resource "aws_secretsmanager_secret" "django_secret" {
  name        = "${var.project_name}/django-secret"
  description = "Django secret key for Admin Interface"
  
  recovery_window_in_days = 7

  tags = local.common_tags
}

resource "aws_secretsmanager_secret_version" "django_secret" {
  secret_id = aws_secretsmanager_secret.django_secret.id
  
  secret_string = jsonencode({
    secret_key = random_password.django_secret.result
  })
}

# Placeholder for Google OAuth Credentials (to be populated manually)
resource "aws_secretsmanager_secret" "google_oauth" {
  name        = "${var.project_name}/google-oauth"
  description = "Google OAuth credentials for Keep API access"
  
  recovery_window_in_days = 7

  tags = local.common_tags
}

resource "aws_secretsmanager_secret_version" "google_oauth" {
  secret_id = aws_secretsmanager_secret.google_oauth.id
  
  secret_string = jsonencode({
    client_id     = "REPLACE_WITH_ACTUAL_CLIENT_ID"
    client_secret = "REPLACE_WITH_ACTUAL_CLIENT_SECRET"
    redirect_uri  = "REPLACE_WITH_ACTUAL_REDIRECT_URI"
  })
  
  lifecycle {
    ignore_changes = [secret_string]  # Prevent Terraform from overwriting manual updates
  }
}

# Placeholder for Notion API Token (to be populated manually)
resource "aws_secretsmanager_secret" "notion_api" {
  name        = "${var.project_name}/notion-api"
  description = "Notion API token for database access"
  
  recovery_window_in_days = 7

  tags = local.common_tags
}

resource "aws_secretsmanager_secret_version" "notion_api" {
  secret_id = aws_secretsmanager_secret.notion_api.id
  
  secret_string = jsonencode({
    api_token   = "REPLACE_WITH_ACTUAL_API_TOKEN"
    database_id = "REPLACE_WITH_ACTUAL_DATABASE_ID"
  })
  
  lifecycle {
    ignore_changes = [secret_string]  # Prevent Terraform from overwriting manual updates
  }
}

# IAM Policy for Secrets Manager Access
resource "aws_iam_policy" "secrets_access" {
  name        = "${var.project_name}-secrets-access"
  description = "Policy for Keep-Notion-Sync services to access Secrets Manager"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Resource = [
          aws_secretsmanager_secret.db_credentials.arn,
          aws_secretsmanager_secret.encryption_key.arn,
          aws_secretsmanager_secret.django_secret.arn,
          aws_secretsmanager_secret.google_oauth.arn,
          aws_secretsmanager_secret.notion_api.arn
        ]
      }
    ]
  })

  tags = local.common_tags
}

# CloudWatch Alarms for Secrets Manager
resource "aws_cloudwatch_log_metric_filter" "secrets_access" {
  name           = "${var.project_name}-secrets-access-filter"
  log_group_name = "/aws/secretsmanager/${var.project_name}"
  pattern        = "[time, request_id, event_type = GetSecretValue, ...]"

  metric_transformation {
    name      = "SecretsAccessCount"
    namespace = "KeepNotionSync"
    value     = "1"
  }
}

# Outputs
output "secrets_db_credentials_arn" {
  description = "ARN of database credentials secret"
  value       = aws_secretsmanager_secret.db_credentials.arn
  sensitive   = true
}

output "secrets_encryption_key_arn" {
  description = "ARN of encryption key secret"
  value       = aws_secretsmanager_secret.encryption_key.arn
  sensitive   = true
}

output "secrets_django_secret_arn" {
  description = "ARN of Django secret key"
  value       = aws_secretsmanager_secret.django_secret.arn
  sensitive   = true
}

output "secrets_google_oauth_arn" {
  description = "ARN of Google OAuth credentials secret"
  value       = aws_secretsmanager_secret.google_oauth.arn
  sensitive   = true
}

output "secrets_notion_api_arn" {
  description = "ARN of Notion API token secret"
  value       = aws_secretsmanager_secret.notion_api.arn
  sensitive   = true
}

output "secrets_access_policy_arn" {
  description = "IAM policy ARN for Secrets Manager access"
  value       = aws_iam_policy.secrets_access.arn
}
