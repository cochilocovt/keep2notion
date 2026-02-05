# AWS Staging Environment Deployment Guide

This guide provides step-by-step instructions for deploying the Keep-Notion-Sync application to an AWS staging environment.

## Overview

The staging environment mirrors production but uses:
- Smaller instance sizes
- Reduced replica counts
- Shorter log retention
- Test credentials

## Prerequisites

- AWS account with appropriate permissions
- AWS CLI configured
- Terraform installed
- kubectl installed
- Docker installed
- Helm installed

## Deployment Checklist

- [ ] AWS infrastructure provisioned
- [ ] Docker images built and pushed to ECR
- [ ] Database migrations completed
- [ ] Secrets configured in AWS Secrets Manager
- [ ] Kubernetes manifests deployed
- [ ] DNS configured
- [ ] SSL certificates validated
- [ ] Health checks passing
- [ ] Monitoring configured

## Step-by-Step Deployment

### 1. Prepare Staging Configuration

Create `deployment/terraform/terraform.staging.tfvars`:

```hcl
# AWS Configuration
aws_region   = "us-east-1"
project_name = "keep-notion-sync-staging"
environment  = "staging"

# VPC Configuration
vpc_cidr = "10.1.0.0/16"

# RDS Configuration
db_instance_class           = "db.t3.small"  # Smaller for staging
db_allocated_storage        = 50
db_max_allocated_storage    = 100
db_name                     = "keep_notion_sync_staging"
db_username                 = "dbadmin"
db_password                 = "CHANGE_ME_STAGING_PASSWORD"
db_backup_retention_period  = 3  # Shorter retention for staging

# EKS Configuration
eks_cluster_version    = "1.27"
eks_node_instance_types = ["t3.medium"]
eks_node_desired_size  = 2  # Fewer nodes for staging
eks_node_min_size      = 1
eks_node_max_size      = 4

# S3 Configuration
s3_bucket_name               = "keep-notion-sync-staging-images"
s3_lifecycle_expiration_days = 3  # Shorter retention for staging

# Tags
tags = {
  Project     = "keep-notion-sync"
  Environment = "staging"
  ManagedBy   = "terraform"
}
```

### 2. Deploy Infrastructure

```bash
cd deployment/scripts

# Initialize Terraform
./setup-aws-infrastructure.sh init

# Review plan
terraform plan -var-file=terraform.staging.tfvars

# Apply infrastructure
./setup-aws-infrastructure.sh apply
```

Expected resources created:
- VPC with subnets
- EKS cluster with 2 nodes
- RDS PostgreSQL (db.t3.small)
- S3 bucket
- ECR repositories
- Secrets Manager secrets
- CloudWatch log groups
- IAM roles and policies

### 3. Configure kubectl

```bash
# Update kubeconfig
aws eks update-kubeconfig \
  --name keep-notion-sync-staging \
  --region us-east-1

# Verify connection
kubectl cluster-info
kubectl get nodes
```

### 4. Install AWS Load Balancer Controller

```bash
cd deployment/scripts
./install-aws-load-balancer-controller.sh keep-notion-sync-staging us-east-1
```

Verify installation:
```bash
kubectl get deployment -n kube-system aws-load-balancer-controller
```

### 5. Build and Push Docker Images

```bash
cd deployment/scripts

# Build and push all images
./build-and-push-images.sh us-east-1 YOUR_AWS_ACCOUNT_ID

# Verify images in ECR
aws ecr list-images --repository-name keep-notion-sync-staging/api-gateway
aws ecr list-images --repository-name keep-notion-sync-staging/sync-service
aws ecr list-images --repository-name keep-notion-sync-staging/keep-extractor
aws ecr list-images --repository-name keep-notion-sync-staging/notion-writer
aws ecr list-images --repository-name keep-notion-sync-staging/admin-interface
```

### 6. Configure Secrets

#### Get RDS Endpoint

```bash
RDS_ENDPOINT=$(terraform output -raw rds_endpoint)
echo "RDS Endpoint: $RDS_ENDPOINT"
```

#### Create Kubernetes Secrets

```bash
# Database credentials
kubectl create secret generic db-credentials \
  --from-literal=username=dbadmin \
  --from-literal=password=YOUR_STAGING_DB_PASSWORD \
  -n keep-notion-sync

# Encryption key
kubectl create secret generic encryption-key \
  --from-literal=key=$(openssl rand -base64 32) \
  -n keep-notion-sync

# Django secret key
kubectl create secret generic django-secret \
  --from-literal=secret-key=$(openssl rand -base64 50) \
  -n keep-notion-sync
```

#### Configure AWS Secrets Manager

```bash
# Google OAuth credentials (use test credentials for staging)
aws secretsmanager put-secret-value \
  --secret-id keep-notion-sync-staging/google-oauth \
  --secret-string '{
    "client_id": "STAGING_GOOGLE_CLIENT_ID",
    "client_secret": "STAGING_GOOGLE_CLIENT_SECRET",
    "redirect_uri": "https://admin-staging.keep-notion-sync.example.com/oauth/callback"
  }'

# Notion API token (use test workspace for staging)
aws secretsmanager put-secret-value \
  --secret-id keep-notion-sync-staging/notion-api \
  --secret-string '{
    "api_token": "STAGING_NOTION_API_TOKEN",
    "database_id": "STAGING_NOTION_DATABASE_ID"
  }'
```

### 7. Update Kubernetes Manifests for Staging

Create staging-specific ConfigMap:

```yaml
# deployment/kubernetes/staging/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: keep-notion-sync-config
  namespace: keep-notion-sync
data:
  DB_HOST: "YOUR_RDS_ENDPOINT"
  DB_PORT: "5432"
  DB_NAME: "keep_notion_sync_staging"
  
  KEEP_EXTRACTOR_URL: "http://keep-extractor-service:8001"
  NOTION_WRITER_URL: "http://notion-writer-service:8002"
  SYNC_SERVICE_URL: "http://sync-service:8003"
  API_GATEWAY_URL: "http://api-gateway-service:8000"
  
  AWS_REGION: "us-east-1"
  S3_BUCKET_NAME: "keep-notion-sync-staging-images-ACCOUNT_ID"
  
  LOG_LEVEL: "DEBUG"  # More verbose for staging
  ENVIRONMENT: "staging"
  
  NOTION_RATE_LIMIT_REQUESTS: "3"
  NOTION_RATE_LIMIT_PERIOD: "1"
  MAX_RETRIES: "3"
  RETRY_BACKOFF_FACTOR: "2"
```

Update deployment replicas for staging:

```yaml
# Reduce replicas for staging
spec:
  replicas: 1  # Instead of 2-3 in production
```

### 8. Run Database Migrations

```bash
cd deployment/scripts

# Run migrations
./run-migrations.sh \
  YOUR_RDS_ENDPOINT \
  keep_notion_sync_staging \
  dbadmin \
  YOUR_STAGING_DB_PASSWORD
```

Verify migrations:
```bash
# Connect to database
psql -h YOUR_RDS_ENDPOINT \
     -U dbadmin \
     -d keep_notion_sync_staging

# Check tables
\dt

# Exit
\q
```

### 9. Deploy to Kubernetes

```bash
cd deployment/scripts

# Deploy all services
./deploy-to-eks.sh keep-notion-sync-staging us-east-1
```

Monitor deployment:
```bash
# Watch pods starting
kubectl get pods -n keep-notion-sync --watch

# Check deployment status
kubectl get deployments -n keep-notion-sync

# Check services
kubectl get svc -n keep-notion-sync
```

### 10. Configure DNS

Get ALB DNS name:
```bash
ALB_DNS=$(kubectl get ingress keep-notion-sync-ingress -n keep-notion-sync \
  -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')

echo "ALB DNS: $ALB_DNS"
```

Create DNS records:
- `api-staging.keep-notion-sync.example.com` → ALB DNS
- `admin-staging.keep-notion-sync.example.com` → ALB DNS

### 11. Request SSL Certificate

```bash
# Request certificate for staging domains
aws acm request-certificate \
  --domain-name "*.staging.keep-notion-sync.example.com" \
  --subject-alternative-names "staging.keep-notion-sync.example.com" \
  --validation-method DNS \
  --region us-east-1

# Get certificate ARN
CERT_ARN=$(aws acm list-certificates --region us-east-1 \
  --query "CertificateSummaryList[?DomainName=='*.staging.keep-notion-sync.example.com'].CertificateArn" \
  --output text)

echo "Certificate ARN: $CERT_ARN"
```

Add DNS validation records, then update ingress:
```bash
kubectl patch ingress keep-notion-sync-ingress -n keep-notion-sync \
  --type='json' \
  -p='[{"op": "replace", "path": "/metadata/annotations/alb.ingress.kubernetes.io~1certificate-arn", "value":"'$CERT_ARN'"}]'
```

### 12. Verify Deployment

#### Check Pod Health

```bash
# All pods should be Running
kubectl get pods -n keep-notion-sync

# Check pod logs
kubectl logs -f deployment/api-gateway -n keep-notion-sync
kubectl logs -f deployment/sync-service -n keep-notion-sync
```

#### Test Health Endpoints

```bash
# API Gateway health
curl https://api-staging.keep-notion-sync.example.com/api/v1/health

# Expected response:
# {
#   "status": "healthy",
#   "services": {
#     "sync_service": "up",
#     "database": "up"
#   }
# }
```

#### Test Admin Interface

```bash
# Should redirect to login
curl -I https://admin-staging.keep-notion-sync.example.com/admin/
```

#### Test Sync Flow

```bash
# Start a sync job
curl -X POST https://api-staging.keep-notion-sync.example.com/api/v1/sync/start \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test-user",
    "full_sync": false
  }'

# Check job status
curl https://api-staging.keep-notion-sync.example.com/api/v1/sync/jobs/JOB_ID
```

### 13. Configure Monitoring

#### CloudWatch Dashboard

Access the dashboard:
```bash
terraform output cloudwatch_dashboard_url
```

#### Set Up Alarms

```bash
# Create SNS topic for staging alerts
aws sns create-topic --name keep-notion-sync-staging-alerts

# Subscribe to alerts
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:ACCOUNT_ID:keep-notion-sync-staging-alerts \
  --protocol email \
  --notification-endpoint your-email@example.com
```

### 14. Load Testing (Optional)

Create test data:
```bash
# Create test sync jobs
for i in {1..10}; do
  curl -X POST https://api-staging.keep-notion-sync.example.com/api/v1/sync/start \
    -H "Content-Type: application/json" \
    -d "{\"user_id\": \"test-user-$i\", \"full_sync\": false}"
done
```

Monitor performance:
```bash
# Watch HPA scaling
kubectl get hpa -n keep-notion-sync --watch

# Check resource usage
kubectl top pods -n keep-notion-sync
kubectl top nodes
```

## Verification Checklist

### Infrastructure
- [ ] VPC and subnets created
- [ ] EKS cluster running with 2 nodes
- [ ] RDS database accessible
- [ ] S3 bucket created with lifecycle rules
- [ ] ECR repositories contain images
- [ ] Secrets Manager secrets configured

### Kubernetes
- [ ] All pods in Running state
- [ ] All deployments available
- [ ] Services created and accessible
- [ ] Ingress created with ALB
- [ ] HPA configured
- [ ] Network policies applied

### Application
- [ ] Health endpoints responding
- [ ] Database migrations completed
- [ ] Can create sync jobs
- [ ] Can query sync status
- [ ] Admin interface accessible
- [ ] Logs flowing to CloudWatch

### Security
- [ ] HTTPS working with valid certificate
- [ ] HTTP redirects to HTTPS
- [ ] Security headers present
- [ ] Secrets encrypted
- [ ] Network policies enforced
- [ ] IAM roles configured with least privilege

### Monitoring
- [ ] CloudWatch logs receiving data
- [ ] CloudWatch metrics being published
- [ ] Dashboard showing data
- [ ] Alarms configured
- [ ] SNS notifications working

## Troubleshooting

### Pods Not Starting

```bash
# Describe pod
kubectl describe pod POD_NAME -n keep-notion-sync

# Check events
kubectl get events -n keep-notion-sync --sort-by='.lastTimestamp'

# Check logs
kubectl logs POD_NAME -n keep-notion-sync
```

### Database Connection Failures

```bash
# Test connectivity from pod
kubectl exec -it deployment/api-gateway -n keep-notion-sync -- sh
nc -zv $DB_HOST 5432

# Check security groups
aws ec2 describe-security-groups --group-ids SG_ID
```

### ALB Not Created

```bash
# Check ALB controller logs
kubectl logs -n kube-system deployment/aws-load-balancer-controller

# Check ingress status
kubectl describe ingress keep-notion-sync-ingress -n keep-notion-sync
```

### Certificate Issues

```bash
# Check certificate status
aws acm describe-certificate --certificate-arn $CERT_ARN

# Verify DNS validation
dig CNAME_RECORD
```

## Staging vs Production Differences

| Aspect | Staging | Production |
|--------|---------|------------|
| Instance Size | t3.small/medium | t3.large/xlarge |
| Node Count | 1-4 | 2-10 |
| Replicas | 1 | 2-3 |
| Log Retention | 7 days | 30 days |
| Backup Retention | 3 days | 7 days |
| S3 Lifecycle | 3 days | 7 days |
| Log Level | DEBUG | INFO |
| Monitoring | Basic | Comprehensive |

## Cleanup Staging Environment

When done testing:

```bash
# Delete Kubernetes resources
kubectl delete namespace keep-notion-sync

# Destroy infrastructure
cd deployment/scripts
./setup-aws-infrastructure.sh destroy
```

## Next Steps

After successful staging deployment:
1. Run integration tests
2. Perform load testing
3. Verify all features work
4. Document any issues
5. Prepare for production deployment

## Additional Resources

- [Deployment README](./README.md)
- [HTTPS Configuration](./security/HTTPS_CONFIGURATION.md)
- [Secure Logging](./security/SECURE_LOGGING.md)
- [Image Cleanup](./security/IMAGE_CLEANUP.md)
