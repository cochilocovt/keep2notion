# Keep-Notion-Sync Deployment Guide

This directory contains all the necessary configuration and scripts to deploy the Keep-Notion-Sync application to AWS using EKS (Elastic Kubernetes Service).

## Directory Structure

```
deployment/
├── kubernetes/          # Kubernetes manifests for EKS
│   ├── namespace.yaml
│   ├── configmap.yaml
│   ├── secrets.yaml
│   ├── service-account.yaml
│   ├── *-deployment.yaml
│   ├── ingress.yaml
│   ├── hpa.yaml
│   ├── network-policy.yaml
│   └── README.md
├── terraform/           # Terraform infrastructure as code
│   ├── main.tf
│   ├── variables.tf
│   ├── vpc.tf
│   ├── rds.tf
│   ├── s3.tf
│   ├── secrets.tf
│   ├── cloudwatch.tf
│   ├── eks.tf
│   ├── ecr.tf
│   └── policies/
└── scripts/             # Deployment automation scripts
    ├── setup-aws-infrastructure.sh
    ├── build-and-push-images.sh
    ├── run-migrations.sh
    ├── deploy-to-eks.sh
    └── install-aws-load-balancer-controller.sh
```

## Prerequisites

### Required Tools

1. **AWS CLI** (v2.x+)
   ```bash
   aws --version
   ```

2. **Terraform** (v1.5.0+)
   ```bash
   terraform --version
   ```

3. **kubectl** (v1.27+)
   ```bash
   kubectl version --client
   ```

4. **Docker** (v20.x+)
   ```bash
   docker --version
   ```

5. **Helm** (v3.x+)
   ```bash
   helm version
   ```

### AWS Account Setup

1. **AWS Account** with appropriate permissions
2. **IAM User** with programmatic access
3. **AWS CLI configured** with credentials:
   ```bash
   aws configure
   ```

### Required AWS Permissions

Your IAM user/role needs permissions for:
- VPC, Subnets, Security Groups
- EKS Cluster and Node Groups
- RDS PostgreSQL
- S3 Buckets
- ECR Repositories
- Secrets Manager
- CloudWatch Logs and Metrics
- IAM Roles and Policies
- KMS Keys

## Deployment Steps

### Step 1: Setup AWS Infrastructure with Terraform

1. Navigate to the terraform directory:
   ```bash
   cd deployment/terraform
   ```

2. Create `terraform.tfvars` file:
   ```hcl
   aws_region  = "us-east-1"
   project_name = "keep-notion-sync"
   environment = "production"
   
   # Database Configuration
   db_username = "dbadmin"
   db_password = "YOUR_SECURE_PASSWORD_HERE"
   
   # EKS Configuration
   eks_cluster_version = "1.27"
   eks_node_desired_size = 3
   
   # S3 Configuration
   s3_bucket_name = "keep-notion-sync-images"
   ```

3. Initialize Terraform:
   ```bash
   cd deployment/scripts
   ./setup-aws-infrastructure.sh init
   ```

4. Review the infrastructure plan:
   ```bash
   ./setup-aws-infrastructure.sh plan
   ```

5. Apply the infrastructure:
   ```bash
   ./setup-aws-infrastructure.sh apply
   ```

   This will create:
   - VPC with public, private, and database subnets
   - EKS cluster with managed node group
   - RDS PostgreSQL database
   - S3 bucket for image storage
   - ECR repositories for Docker images
   - Secrets Manager secrets
   - CloudWatch log groups and dashboard
   - IAM roles and policies

6. Save the Terraform outputs:
   ```bash
   ./setup-aws-infrastructure.sh output > terraform-outputs.txt
   ```

### Step 2: Update Kubernetes Manifests

Update the following files with actual values from Terraform outputs:

1. **configmap.yaml**:
   - `DB_HOST`: RDS endpoint from Terraform output
   - `S3_BUCKET_NAME`: S3 bucket name from Terraform output

2. **service-account.yaml**:
   - `eks.amazonaws.com/role-arn`: Service account role ARN from Terraform output

3. **ingress.yaml**:
   - `alb.ingress.kubernetes.io/certificate-arn`: ACM certificate ARN
   - `alb.ingress.kubernetes.io/security-groups`: Security group ID
   - Update domain names

4. **All deployment files**:
   - Update image URLs with your AWS account ID and region

### Step 3: Create Kubernetes Secrets

Create secrets manually (recommended for production):

```bash
# Database credentials
kubectl create secret generic db-credentials \
  --from-literal=username=dbadmin \
  --from-literal=password=YOUR_DB_PASSWORD \
  -n keep-notion-sync

# Encryption key (32 bytes for AES-256)
kubectl create secret generic encryption-key \
  --from-literal=key=$(openssl rand -base64 32) \
  -n keep-notion-sync

# Django secret key
kubectl create secret generic django-secret \
  --from-literal=secret-key=$(openssl rand -base64 50) \
  -n keep-notion-sync
```

### Step 4: Build and Push Docker Images

1. Make the script executable:
   ```bash
   chmod +x deployment/scripts/build-and-push-images.sh
   ```

2. Build and push all images:
   ```bash
   cd deployment/scripts
   ./build-and-push-images.sh us-east-1 YOUR_AWS_ACCOUNT_ID
   ```

   This will:
   - Authenticate with ECR
   - Build Docker images for all services
   - Tag images with version and latest
   - Push images to ECR repositories

### Step 5: Run Database Migrations

1. Get RDS endpoint from Terraform outputs or AWS Console

2. Run migrations:
   ```bash
   ./run-migrations.sh \
     YOUR_RDS_ENDPOINT \
     keep_notion_sync \
     dbadmin \
     YOUR_DB_PASSWORD
   ```

### Step 6: Install AWS Load Balancer Controller

1. Make the script executable:
   ```bash
   chmod +x deployment/scripts/install-aws-load-balancer-controller.sh
   ```

2. Install the controller:
   ```bash
   ./install-aws-load-balancer-controller.sh keep-notion-sync us-east-1
   ```

### Step 7: Deploy to EKS

1. Make the script executable:
   ```bash
   chmod +x deployment/scripts/deploy-to-eks.sh
   ```

2. Deploy all services:
   ```bash
   ./deploy-to-eks.sh keep-notion-sync us-east-1
   ```

   This will:
   - Create namespace
   - Deploy all microservices
   - Configure autoscaling
   - Create ingress with ALB
   - Apply network policies

3. Wait for ALB to be provisioned (2-3 minutes):
   ```bash
   kubectl get ingress -n keep-notion-sync --watch
   ```

### Step 8: Configure DNS

1. Get the ALB DNS name:
   ```bash
   kubectl get ingress keep-notion-sync-ingress -n keep-notion-sync \
     -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
   ```

2. Create CNAME records in your DNS provider:
   - `api.keep-notion-sync.example.com` → ALB DNS name
   - `admin.keep-notion-sync.example.com` → ALB DNS name

### Step 9: Configure Application Secrets

Update AWS Secrets Manager with actual credentials:

```bash
# Google OAuth credentials
aws secretsmanager put-secret-value \
  --secret-id keep-notion-sync/google-oauth \
  --secret-string '{
    "client_id": "YOUR_GOOGLE_CLIENT_ID",
    "client_secret": "YOUR_GOOGLE_CLIENT_SECRET",
    "redirect_uri": "YOUR_REDIRECT_URI"
  }'

# Notion API token
aws secretsmanager put-secret-value \
  --secret-id keep-notion-sync/notion-api \
  --secret-string '{
    "api_token": "YOUR_NOTION_API_TOKEN",
    "database_id": "YOUR_NOTION_DATABASE_ID"
  }'
```

### Step 10: Verify Deployment

1. Check pod status:
   ```bash
   kubectl get pods -n keep-notion-sync
   ```

2. Check service status:
   ```bash
   kubectl get svc -n keep-notion-sync
   ```

3. Test API Gateway health:
   ```bash
   curl https://api.keep-notion-sync.example.com/api/v1/health
   ```

4. Access Admin Interface:
   ```bash
   open https://admin.keep-notion-sync.example.com/admin/
   ```

## Monitoring and Maintenance

### View Logs

```bash
# API Gateway logs
kubectl logs -f deployment/api-gateway -n keep-notion-sync

# Sync Service logs
kubectl logs -f deployment/sync-service -n keep-notion-sync

# All pods
kubectl logs -f -l app=api-gateway -n keep-notion-sync
```

### CloudWatch Dashboard

Access the CloudWatch dashboard:
```bash
# Get dashboard URL from Terraform outputs
terraform output cloudwatch_dashboard_url
```

### Scaling

```bash
# Manual scaling
kubectl scale deployment api-gateway --replicas=5 -n keep-notion-sync

# Check HPA status
kubectl get hpa -n keep-notion-sync
```

### Updates

```bash
# Update image version
kubectl set image deployment/api-gateway \
  api-gateway=ACCOUNT_ID.dkr.ecr.REGION.amazonaws.com/keep-notion-sync/api-gateway:v1.1.0 \
  -n keep-notion-sync

# Check rollout status
kubectl rollout status deployment/api-gateway -n keep-notion-sync

# Rollback if needed
kubectl rollout undo deployment/api-gateway -n keep-notion-sync
```

## Troubleshooting

### Pods Not Starting

```bash
# Describe pod
kubectl describe pod POD_NAME -n keep-notion-sync

# Check events
kubectl get events -n keep-notion-sync --sort-by='.lastTimestamp'
```

### Database Connection Issues

```bash
# Test from pod
kubectl exec -it deployment/api-gateway -n keep-notion-sync -- sh
nc -zv $DB_HOST 5432
```

### Ingress Not Working

```bash
# Check ALB controller logs
kubectl logs -n kube-system deployment/aws-load-balancer-controller

# Check ingress details
kubectl describe ingress keep-notion-sync-ingress -n keep-notion-sync
```

### High Error Rate

```bash
# Check CloudWatch alarms
aws cloudwatch describe-alarms --alarm-names keep-notion-sync-*

# View recent errors
aws logs tail /aws/eks/keep-notion-sync/sync-service --follow
```

## Cost Optimization

1. **Right-size resources**: Adjust CPU/memory requests based on actual usage
2. **Use Spot instances**: For non-critical workloads
3. **Enable S3 lifecycle**: Automatically delete old images
4. **Optimize RDS**: Use appropriate instance size
5. **Review CloudWatch retention**: Adjust log retention periods

## Security Best Practices

1. **Rotate secrets regularly**: Update credentials in Secrets Manager
2. **Enable MFA**: For AWS account access
3. **Use least privilege**: IAM roles with minimal permissions
4. **Enable audit logging**: CloudTrail for all API calls
5. **Regular updates**: Keep EKS, images, and dependencies updated
6. **Network policies**: Restrict pod-to-pod communication
7. **Security scanning**: Enable ECR image scanning

## Cleanup

To destroy all infrastructure:

```bash
# Delete Kubernetes resources
kubectl delete namespace keep-notion-sync

# Destroy Terraform infrastructure
cd deployment/scripts
./setup-aws-infrastructure.sh destroy
```

**Warning**: This will permanently delete all data including the database!

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review CloudWatch logs and metrics
3. Check Kubernetes events and pod logs
4. Review the design document in `.kiro/specs/google-keep-notion-sync/design.md`

## Additional Resources

- [AWS EKS Documentation](https://docs.aws.amazon.com/eks/)
- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [AWS Load Balancer Controller](https://kubernetes-sigs.github.io/aws-load-balancer-controller/)
