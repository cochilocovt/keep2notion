# Production Deployment Documentation

This document provides comprehensive guidance for deploying the Keep-Notion-Sync application to production on AWS.

## Table of Contents

1. [Pre-Deployment Checklist](#pre-deployment-checklist)
2. [Production Configuration](#production-configuration)
3. [Deployment Steps](#deployment-steps)
4. [Post-Deployment Verification](#post-deployment-verification)
5. [Monitoring and Alerting](#monitoring-and-alerting)
6. [Backup and Disaster Recovery](#backup-and-disaster-recovery)
7. [Scaling Guidelines](#scaling-guidelines)
8. [Troubleshooting](#troubleshooting)
9. [Rollback Procedures](#rollback-procedures)

## Pre-Deployment Checklist

### Infrastructure Readiness

- [ ] AWS account configured with appropriate permissions
- [ ] Production VPC and subnets planned
- [ ] Domain names registered and DNS configured
- [ ] SSL/TLS certificates obtained
- [ ] Budget and cost alerts configured
- [ ] Security groups and network policies reviewed
- [ ] IAM roles and policies configured with least privilege

### Application Readiness

- [ ] All code merged to main branch
- [ ] All tests passing (unit, integration, E2E)
- [ ] Load testing completed successfully
- [ ] Security audit completed
- [ ] Documentation updated
- [ ] Runbooks prepared
- [ ] On-call rotation established

### Data Readiness

- [ ] Database schema finalized
- [ ] Migration scripts tested
- [ ] Backup strategy defined
- [ ] Data retention policies configured
- [ ] Encryption keys generated and stored securely

### Team Readiness

- [ ] Deployment plan reviewed by team
- [ ] Rollback procedures documented and tested
- [ ] Monitoring dashboards configured
- [ ] Alert recipients configured
- [ ] Communication plan established
- [ ] Post-deployment tasks assigned

## Production Configuration

### Terraform Variables

Create `deployment/terraform/terraform.prod.tfvars`:

```hcl
# AWS Configuration
aws_region   = "us-east-1"
project_name = "keep-notion-sync"
environment  = "production"

# VPC Configuration
vpc_cidr = "10.0.0.0/16"
availability_zones = ["us-east-1a", "us-east-1b", "us-east-1c"]

# RDS Configuration
db_instance_class           = "db.r6g.large"  # Production-grade instance
db_allocated_storage        = 200
db_max_allocated_storage    = 1000
db_name                     = "keep_notion_sync"
db_username                 = "dbadmin"
db_password                 = "USE_SECRETS_MANAGER"  # Replace with actual secure password
db_backup_retention_period  = 7
db_backup_window            = "03:00-04:00"
db_maintenance_window       = "sun:04:00-sun:05:00"

# EKS Configuration
eks_cluster_version     = "1.27"
eks_node_instance_types = ["t3.large", "t3.xlarge"]
eks_node_desired_size   = 6
eks_node_min_size       = 3
eks_node_max_size       = 20

# S3 Configuration
s3_bucket_name               = "keep-notion-sync-images"
s3_lifecycle_expiration_days = 7

# Tags
tags = {
  Project     = "keep-notion-sync"
  Environment = "production"
  ManagedBy   = "terraform"
  CostCenter  = "engineering"
  Compliance  = "required"
}
```

### Kubernetes Production Configuration

Update replica counts in deployment files:

```yaml
# API Gateway
spec:
  replicas: 3

# Sync Service
spec:
  replicas: 3

# Keep Extractor
spec:
  replicas: 2

# Notion Writer
spec:
  replicas: 2

# Admin Interface
spec:
  replicas: 2
```

Update resource limits:

```yaml
resources:
  requests:
    memory: "512Mi"
    cpu: "500m"
  limits:
    memory: "2Gi"
    cpu: "2000m"
```

### Environment Variables

Production ConfigMap:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: keep-notion-sync-config
  namespace: keep-notion-sync
data:
  LOG_LEVEL: "INFO"  # Not DEBUG in production
  ENVIRONMENT: "production"
  
  # Rate limiting (more conservative)
  NOTION_RATE_LIMIT_REQUESTS: "3"
  NOTION_RATE_LIMIT_PERIOD: "1"
  
  # Retry configuration
  MAX_RETRIES: "5"
  RETRY_BACKOFF_FACTOR: "2"
  
  # Monitoring
  ENABLE_METRICS: "true"
  METRICS_PORT: "9090"
```

## Deployment Steps

### Phase 1: Infrastructure Deployment (Day 1)

#### 1.1 Deploy AWS Infrastructure

```bash
cd deployment/terraform

# Initialize Terraform
terraform init

# Review plan carefully
terraform plan -var-file=terraform.prod.tfvars -out=prod.tfplan

# Apply infrastructure (takes 20-30 minutes)
terraform apply prod.tfplan

# Save outputs
terraform output > ../prod-outputs.txt
```

#### 1.2 Verify Infrastructure

```bash
# Verify VPC
aws ec2 describe-vpcs --filters "Name=tag:Project,Values=keep-notion-sync"

# Verify EKS cluster
aws eks describe-cluster --name keep-notion-sync

# Verify RDS
aws rds describe-db-instances --db-instance-identifier keep-notion-sync-db

# Verify S3 bucket
aws s3 ls | grep keep-notion-sync
```

#### 1.3 Configure kubectl

```bash
aws eks update-kubeconfig --name keep-notion-sync --region us-east-1

# Verify connection
kubectl cluster-info
kubectl get nodes
```

### Phase 2: Pre-Deployment Setup (Day 1-2)

#### 2.1 Install AWS Load Balancer Controller

```bash
cd deployment/scripts
./install-aws-load-balancer-controller.sh keep-notion-sync us-east-1

# Verify installation
kubectl get deployment -n kube-system aws-load-balancer-controller
```

#### 2.2 Configure Secrets

```bash
# Generate encryption key
ENCRYPTION_KEY=$(openssl rand -base64 32)

# Create Kubernetes secrets
kubectl create secret generic db-credentials \
  --from-literal=username=dbadmin \
  --from-literal=password=YOUR_SECURE_PASSWORD \
  -n keep-notion-sync

kubectl create secret generic encryption-key \
  --from-literal=key=$ENCRYPTION_KEY \
  -n keep-notion-sync

kubectl create secret generic django-secret \
  --from-literal=secret-key=$(openssl rand -base64 50) \
  -n keep-notion-sync

# Configure AWS Secrets Manager
aws secretsmanager put-secret-value \
  --secret-id keep-notion-sync/google-oauth \
  --secret-string '{
    "client_id": "PRODUCTION_GOOGLE_CLIENT_ID",
    "client_secret": "PRODUCTION_GOOGLE_CLIENT_SECRET",
    "redirect_uri": "https://admin.keep-notion-sync.com/oauth/callback"
  }'

aws secretsmanager put-secret-value \
  --secret-id keep-notion-sync/notion-api \
  --secret-string '{
    "api_token": "PRODUCTION_NOTION_API_TOKEN",
    "database_id": "PRODUCTION_NOTION_DATABASE_ID"
  }'
```

#### 2.3 Configure SSL Certificates

```bash
# Request certificate
aws acm request-certificate \
  --domain-name "*.keep-notion-sync.com" \
  --subject-alternative-names "keep-notion-sync.com" \
  --validation-method DNS \
  --region us-east-1

# Get certificate ARN
CERT_ARN=$(aws acm list-certificates --region us-east-1 \
  --query "CertificateSummaryList[?DomainName=='*.keep-notion-sync.com'].CertificateArn" \
  --output text)

echo "Certificate ARN: $CERT_ARN"

# Add DNS validation records (from ACM console)
# Wait for validation (5-30 minutes)
```

#### 2.4 Build and Push Docker Images

```bash
cd deployment/scripts

# Build and push with production tag
VERSION=v1.0.0
./build-and-push-images.sh us-east-1 YOUR_AWS_ACCOUNT_ID

# Tag as production
for SERVICE in api-gateway admin-interface sync-service keep-extractor notion-writer; do
  docker tag $SERVICE:latest \
    YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/keep-notion-sync/$SERVICE:$VERSION
  
  docker push \
    YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/keep-notion-sync/$SERVICE:$VERSION
done
```

### Phase 3: Database Setup (Day 2)

#### 3.1 Run Database Migrations

```bash
cd deployment/scripts

# Get RDS endpoint
RDS_ENDPOINT=$(terraform output -raw rds_endpoint)

# Run migrations
./run-migrations.sh \
  $RDS_ENDPOINT \
  keep_notion_sync \
  dbadmin \
  YOUR_SECURE_PASSWORD

# Verify migrations
psql -h $RDS_ENDPOINT -U dbadmin -d keep_notion_sync -c "\dt"
```

#### 3.2 Create Initial Admin User

```bash
# Connect to database
psql -h $RDS_ENDPOINT -U dbadmin -d keep_notion_sync

# Create admin user (adjust as needed)
INSERT INTO auth_user (username, email, password, is_staff, is_superuser, is_active)
VALUES ('admin', 'admin@keep-notion-sync.com', 'HASHED_PASSWORD', true, true, true);

# Exit
\q
```

### Phase 4: Application Deployment (Day 2-3)

#### 4.1 Update Kubernetes Manifests

Update production values:
- Image tags to production version
- Replica counts
- Resource limits
- Certificate ARN in ingress
- RDS endpoint in ConfigMap

#### 4.2 Deploy Application

```bash
cd deployment/scripts

# Deploy all services
./deploy-to-eks.sh keep-notion-sync us-east-1

# Monitor deployment
kubectl get pods -n keep-notion-sync --watch
```

#### 4.3 Verify Deployment

```bash
# Check all pods are running
kubectl get pods -n keep-notion-sync

# Check services
kubectl get svc -n keep-notion-sync

# Check ingress
kubectl get ingress -n keep-notion-sync

# Get ALB DNS
ALB_DNS=$(kubectl get ingress keep-notion-sync-ingress -n keep-notion-sync \
  -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')

echo "ALB DNS: $ALB_DNS"
```

### Phase 5: DNS Configuration (Day 3)

#### 5.1 Create DNS Records

```bash
# Using Route 53
aws route53 change-resource-record-sets \
  --hosted-zone-id YOUR_ZONE_ID \
  --change-batch '{
    "Changes": [
      {
        "Action": "CREATE",
        "ResourceRecordSet": {
          "Name": "api.keep-notion-sync.com",
          "Type": "CNAME",
          "TTL": 300,
          "ResourceRecords": [{"Value": "'$ALB_DNS'"}]
        }
      },
      {
        "Action": "CREATE",
        "ResourceRecordSet": {
          "Name": "admin.keep-notion-sync.com",
          "Type": "CNAME",
          "TTL": 300,
          "ResourceRecords": [{"Value": "'$ALB_DNS'"}]
        }
      }
    ]
  }'
```

#### 5.2 Verify DNS Propagation

```bash
# Check DNS resolution
dig api.keep-notion-sync.com
dig admin.keep-notion-sync.com

# Test HTTPS
curl -I https://api.keep-notion-sync.com/api/v1/health
curl -I https://admin.keep-notion-sync.com/admin/
```

## Post-Deployment Verification

### Health Checks

```bash
# API Gateway health
curl https://api.keep-notion-sync.com/api/v1/health

# Expected response:
# {
#   "status": "healthy",
#   "services": {
#     "sync_service": "up",
#     "database": "up"
#   }
# }
```

### Functional Tests

```bash
# Run E2E tests against production
cd deployment/testing
pytest test_e2e.py -v --env=production
```

### Performance Tests

```bash
# Run load test
locust -f load_test.py \
  --host=https://api.keep-notion-sync.com \
  --users=100 \
  --spawn-rate=10 \
  --run-time=10m
```

### Security Verification

```bash
# SSL Labs test
# Visit: https://www.ssllabs.com/ssltest/analyze.html?d=api.keep-notion-sync.com

# Check security headers
curl -I https://api.keep-notion-sync.com/api/v1/health | grep -E "(Strict-Transport|X-Content|X-Frame)"

# Verify HTTPS redirect
curl -I http://api.keep-notion-sync.com/api/v1/health
```

## Monitoring and Alerting

### CloudWatch Dashboard

Access dashboard:
```bash
terraform output cloudwatch_dashboard_url
```

### Configure Alerts

```bash
# Create SNS topic for production alerts
aws sns create-topic --name keep-notion-sync-prod-alerts

# Subscribe team email
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:ACCOUNT_ID:keep-notion-sync-prod-alerts \
  --protocol email \
  --notification-endpoint team@keep-notion-sync.com

# Subscribe PagerDuty (if configured)
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:ACCOUNT_ID:keep-notion-sync-prod-alerts \
  --protocol https \
  --notification-endpoint https://events.pagerduty.com/integration/YOUR_KEY/enqueue
```

### Key Metrics to Monitor

1. **Application Metrics**:
   - Request rate
   - Error rate
   - Response time (p50, p95, p99)
   - Sync job success rate

2. **Infrastructure Metrics**:
   - CPU utilization
   - Memory utilization
   - Disk I/O
   - Network throughput

3. **Database Metrics**:
   - Connection count
   - Query performance
   - Replication lag (if applicable)
   - Storage usage

4. **Business Metrics**:
   - Active users
   - Sync jobs per hour
   - Notes synced per day
   - Error rate by type

## Backup and Disaster Recovery

### Database Backups

Automated backups are configured in Terraform:
- Daily automated backups
- 7-day retention
- Backup window: 03:00-04:00 UTC

Manual backup:
```bash
aws rds create-db-snapshot \
  --db-instance-identifier keep-notion-sync-db \
  --db-snapshot-identifier keep-notion-sync-manual-$(date +%Y%m%d-%H%M%S)
```

### Restore from Backup

```bash
# List available snapshots
aws rds describe-db-snapshots \
  --db-instance-identifier keep-notion-sync-db

# Restore from snapshot
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier keep-notion-sync-db-restored \
  --db-snapshot-identifier SNAPSHOT_ID
```

### Disaster Recovery Plan

**RTO (Recovery Time Objective)**: 4 hours
**RPO (Recovery Point Objective)**: 24 hours

#### DR Procedures

1. **Database Failure**:
   - Restore from latest automated backup
   - Update application configuration
   - Verify data integrity

2. **Region Failure**:
   - Deploy to secondary region using Terraform
   - Restore database from cross-region backup
   - Update DNS to point to new region

3. **Complete Infrastructure Loss**:
   - Deploy fresh infrastructure using Terraform
   - Restore database from backup
   - Redeploy application
   - Verify functionality

## Scaling Guidelines

### Horizontal Scaling

HPA is configured for automatic scaling based on CPU/memory:

```yaml
# Current HPA configuration
minReplicas: 2
maxReplicas: 10
targetCPUUtilizationPercentage: 70
targetMemoryUtilizationPercentage: 80
```

Manual scaling:
```bash
# Scale API Gateway
kubectl scale deployment api-gateway --replicas=5 -n keep-notion-sync

# Scale Sync Service
kubectl scale deployment sync-service --replicas=4 -n keep-notion-sync
```

### Vertical Scaling

Update resource limits in deployment manifests and apply:

```bash
kubectl apply -f deployment/kubernetes/api-gateway-deployment.yaml
kubectl rollout status deployment/api-gateway -n keep-notion-sync
```

### Database Scaling

```bash
# Modify instance class
aws rds modify-db-instance \
  --db-instance-identifier keep-notion-sync-db \
  --db-instance-class db.r6g.xlarge \
  --apply-immediately
```

## Troubleshooting

### Common Issues

#### Pods Not Starting

```bash
# Check pod status
kubectl describe pod POD_NAME -n keep-notion-sync

# Check logs
kubectl logs POD_NAME -n keep-notion-sync

# Check events
kubectl get events -n keep-notion-sync --sort-by='.lastTimestamp'
```

#### High Error Rate

```bash
# Check application logs
kubectl logs -f deployment/api-gateway -n keep-notion-sync | grep ERROR

# Check CloudWatch metrics
aws cloudwatch get-metric-statistics \
  --namespace KeepNotionSync \
  --metric-name APIGatewayErrors \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum
```

#### Database Connection Issues

```bash
# Test connectivity from pod
kubectl exec -it deployment/api-gateway -n keep-notion-sync -- sh
nc -zv $DB_HOST 5432

# Check RDS status
aws rds describe-db-instances \
  --db-instance-identifier keep-notion-sync-db \
  --query 'DBInstances[0].DBInstanceStatus'
```

## Rollback Procedures

### Application Rollback

```bash
# Rollback to previous version
kubectl rollout undo deployment/api-gateway -n keep-notion-sync

# Rollback to specific revision
kubectl rollout undo deployment/api-gateway --to-revision=2 -n keep-notion-sync

# Check rollout status
kubectl rollout status deployment/api-gateway -n keep-notion-sync
```

### Database Rollback

```bash
# Restore from backup before deployment
aws rds restore-db-instance-to-point-in-time \
  --source-db-instance-identifier keep-notion-sync-db \
  --target-db-instance-identifier keep-notion-sync-db-rollback \
  --restore-time 2024-01-15T10:00:00Z
```

### Infrastructure Rollback

```bash
# Revert Terraform changes
cd deployment/terraform
terraform apply -var-file=terraform.prod.tfvars.backup
```

## Maintenance Windows

### Planned Maintenance

Schedule: Sundays 04:00-05:00 UTC

Procedure:
1. Notify users 48 hours in advance
2. Enable maintenance mode
3. Perform updates
4. Run smoke tests
5. Disable maintenance mode
6. Monitor for issues

### Emergency Maintenance

For critical security patches or outages:
1. Notify on-call team
2. Assess impact
3. Execute fix
4. Verify resolution
5. Post-mortem within 24 hours

## Support and Escalation

### On-Call Rotation

- Primary: Check PagerDuty schedule
- Secondary: Check PagerDuty schedule
- Escalation: Engineering Manager

### Incident Response

1. **Severity 1** (Production down): Page on-call immediately
2. **Severity 2** (Degraded performance): Alert on-call, 15-min response
3. **Severity 3** (Minor issues): Create ticket, next business day

## Additional Resources

- [Staging Deployment Guide](./STAGING_DEPLOYMENT_GUIDE.md)
- [End-to-End Testing](./testing/END_TO_END_TESTS.md)
- [HTTPS Configuration](./security/HTTPS_CONFIGURATION.md)
- [Secure Logging](./security/SECURE_LOGGING.md)
- [Image Cleanup](./security/IMAGE_CLEANUP.md)
- [Kubernetes README](./kubernetes/README.md)
- [Terraform Documentation](./terraform/)
