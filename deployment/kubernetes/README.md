# Kubernetes Deployment for Keep-Notion-Sync

This directory contains Kubernetes manifests for deploying the Keep-Notion-Sync application to AWS EKS.

## Architecture

The application consists of 5 microservices:
- **API Gateway** (FastAPI) - External REST API on port 8000
- **Admin Interface** (Django) - Web admin UI on port 8080
- **Sync Service** - Orchestration service on port 8003
- **Keep Extractor** - Google Keep integration on port 8001
- **Notion Writer** - Notion integration on port 8002

All services communicate internally via ClusterIP services and are exposed externally via an Application Load Balancer (ALB) through the Ingress resource.

## Prerequisites

1. **AWS EKS Cluster** - A running EKS cluster (v1.27+)
2. **kubectl** - Configured to access your EKS cluster
3. **AWS CLI** - Configured with appropriate credentials
4. **AWS Load Balancer Controller** - Installed in the cluster for ALB ingress
5. **Metrics Server** - Installed for HPA (Horizontal Pod Autoscaler)
6. **AWS RDS PostgreSQL** - Database instance (see terraform/rds.tf)
7. **AWS S3 Bucket** - For image storage (see terraform/s3.tf)
8. **AWS Secrets Manager** - For storing credentials (see terraform/secrets.tf)
9. **ECR Repositories** - For Docker images (see deployment/scripts/push-images.sh)

## Configuration

Before deploying, update the following files with your AWS-specific values:

### 1. ConfigMap (`configmap.yaml`)
```yaml
DB_HOST: "your-rds-endpoint.rds.amazonaws.com"
S3_BUCKET_NAME: "your-s3-bucket-name"
AWS_REGION: "your-aws-region"
```

### 2. Secrets (`secrets.yaml`)
Create secrets using AWS Secrets Manager or kubectl:

```bash
# Database credentials
kubectl create secret generic db-credentials \
  --from-literal=username=your_db_user \
  --from-literal=password=your_db_password \
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

### 3. Service Account (`service-account.yaml`)
Update the IAM role ARN:
```yaml
eks.amazonaws.com/role-arn: arn:aws:iam::YOUR_ACCOUNT_ID:role/KeepNotionSyncRole
```

### 4. Ingress (`ingress.yaml`)
Update the following:
- Certificate ARN for HTTPS
- Security group ID
- Domain names (api.keep-notion-sync.example.com, admin.keep-notion-sync.example.com)

### 5. Deployment Images
Update image URLs in all deployment files:
```yaml
image: YOUR_ACCOUNT_ID.dkr.ecr.YOUR_REGION.amazonaws.com/SERVICE_NAME:latest
```

## Deployment Steps

### Step 1: Create Namespace
```bash
kubectl apply -f namespace.yaml
```

### Step 2: Create Service Account and RBAC
```bash
kubectl apply -f service-account.yaml
```

### Step 3: Create ConfigMap and Secrets
```bash
kubectl apply -f configmap.yaml
kubectl apply -f secrets.yaml  # Or create manually as shown above
```

### Step 4: Deploy Services
```bash
# Deploy all services
kubectl apply -f keep-extractor-deployment.yaml
kubectl apply -f notion-writer-deployment.yaml
kubectl apply -f sync-service-deployment.yaml
kubectl apply -f api-gateway-deployment.yaml
kubectl apply -f admin-interface-deployment.yaml
```

### Step 5: Configure Autoscaling
```bash
kubectl apply -f hpa.yaml
```

### Step 6: Apply Network Policies (Optional but Recommended)
```bash
kubectl apply -f network-policy.yaml
```

### Step 7: Create Ingress
```bash
kubectl apply -f ingress.yaml
```

## Verification

### Check Pod Status
```bash
kubectl get pods -n keep-notion-sync
```

All pods should be in `Running` state with `READY 1/1`.

### Check Services
```bash
kubectl get svc -n keep-notion-sync
```

### Check Ingress
```bash
kubectl get ingress -n keep-notion-sync
kubectl describe ingress keep-notion-sync-ingress -n keep-notion-sync
```

The ALB DNS name will be shown in the output. It may take 2-3 minutes for the ALB to be provisioned.

### Check Logs
```bash
# API Gateway logs
kubectl logs -f deployment/api-gateway -n keep-notion-sync

# Sync Service logs
kubectl logs -f deployment/sync-service -n keep-notion-sync

# Keep Extractor logs
kubectl logs -f deployment/keep-extractor -n keep-notion-sync

# Notion Writer logs
kubectl logs -f deployment/notion-writer -n keep-notion-sync

# Admin Interface logs
kubectl logs -f deployment/admin-interface -n keep-notion-sync
```

### Test Health Endpoints
```bash
# Get the ALB DNS name
ALB_DNS=$(kubectl get ingress keep-notion-sync-ingress -n keep-notion-sync -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')

# Test API Gateway health
curl http://$ALB_DNS/api/v1/health

# Test Admin Interface (should redirect to login)
curl -I http://$ALB_DNS/admin/
```

## Scaling

### Manual Scaling
```bash
# Scale API Gateway to 5 replicas
kubectl scale deployment api-gateway --replicas=5 -n keep-notion-sync

# Scale Sync Service to 4 replicas
kubectl scale deployment sync-service --replicas=4 -n keep-notion-sync
```

### Autoscaling
HPA is configured for all services. Check HPA status:
```bash
kubectl get hpa -n keep-notion-sync
```

## Monitoring

### View HPA Metrics
```bash
kubectl get hpa -n keep-notion-sync --watch
```

### View Resource Usage
```bash
kubectl top pods -n keep-notion-sync
kubectl top nodes
```

### CloudWatch Logs
Logs are automatically sent to CloudWatch. View them in the AWS Console:
1. Go to CloudWatch > Log groups
2. Find log groups: `/aws/eks/keep-notion-sync/*`

## Troubleshooting

### Pods Not Starting
```bash
# Describe pod to see events
kubectl describe pod POD_NAME -n keep-notion-sync

# Check logs
kubectl logs POD_NAME -n keep-notion-sync

# Check previous logs if pod restarted
kubectl logs POD_NAME -n keep-notion-sync --previous
```

### Database Connection Issues
```bash
# Test database connectivity from a pod
kubectl exec -it deployment/api-gateway -n keep-notion-sync -- sh
# Inside the pod:
nc -zv $DB_HOST $DB_PORT
```

### Service Communication Issues
```bash
# Test internal service connectivity
kubectl exec -it deployment/api-gateway -n keep-notion-sync -- sh
# Inside the pod:
curl http://sync-service:8003/health
```

### Ingress Not Working
```bash
# Check ALB controller logs
kubectl logs -n kube-system deployment/aws-load-balancer-controller

# Check ingress events
kubectl describe ingress keep-notion-sync-ingress -n keep-notion-sync

# Verify security groups allow traffic
# Verify target groups are healthy in AWS Console
```

## Updating Deployments

### Update Image Version
```bash
# Update image tag
kubectl set image deployment/api-gateway \
  api-gateway=YOUR_ACCOUNT_ID.dkr.ecr.YOUR_REGION.amazonaws.com/api-gateway:v1.1.0 \
  -n keep-notion-sync

# Check rollout status
kubectl rollout status deployment/api-gateway -n keep-notion-sync

# Rollback if needed
kubectl rollout undo deployment/api-gateway -n keep-notion-sync
```

### Update ConfigMap
```bash
# Edit configmap
kubectl edit configmap keep-notion-sync-config -n keep-notion-sync

# Restart deployments to pick up changes
kubectl rollout restart deployment/api-gateway -n keep-notion-sync
kubectl rollout restart deployment/sync-service -n keep-notion-sync
# ... repeat for other services
```

## Cleanup

To remove all resources:
```bash
kubectl delete namespace keep-notion-sync
```

This will delete all resources in the namespace including deployments, services, configmaps, and secrets.

## Security Considerations

1. **Secrets Management**: Use AWS Secrets Manager with External Secrets Operator for production
2. **Network Policies**: Enable network policies to restrict pod-to-pod communication
3. **RBAC**: Service accounts have minimal required permissions
4. **IRSA**: Use IAM Roles for Service Accounts instead of AWS credentials
5. **TLS**: All external traffic uses HTTPS via ACM certificates
6. **Security Groups**: Restrict ALB security groups to necessary ports and IPs

## Cost Optimization

1. **Right-size Resources**: Adjust CPU/memory requests and limits based on actual usage
2. **HPA**: Autoscaling reduces costs during low traffic periods
3. **Spot Instances**: Consider using spot instances for non-critical workloads
4. **S3 Lifecycle**: Configure S3 lifecycle rules to delete old images
5. **RDS**: Use appropriate instance size and enable automated backups

## Additional Resources

- [AWS EKS Documentation](https://docs.aws.amazon.com/eks/)
- [AWS Load Balancer Controller](https://kubernetes-sigs.github.io/aws-load-balancer-controller/)
- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Horizontal Pod Autoscaler](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/)
