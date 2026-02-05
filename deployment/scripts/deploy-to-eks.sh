#!/bin/bash
# Deploy Keep-Notion-Sync to EKS
# Usage: ./deploy-to-eks.sh [CLUSTER_NAME] [AWS_REGION]

set -e

# Configuration
CLUSTER_NAME=${1:-keep-notion-sync}
AWS_REGION=${2:-us-east-1}
NAMESPACE="keep-notion-sync"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deploying to EKS${NC}"
echo -e "${GREEN}========================================${NC}"
echo "Cluster: $CLUSTER_NAME"
echo "Region: $AWS_REGION"
echo "Namespace: $NAMESPACE"
echo ""

# Update kubeconfig
echo -e "${YELLOW}Updating kubeconfig...${NC}"
aws eks update-kubeconfig --name $CLUSTER_NAME --region $AWS_REGION

# Verify connection
echo -e "${YELLOW}Verifying cluster connection...${NC}"
kubectl cluster-info
echo ""

# Create namespace
echo -e "${YELLOW}Creating namespace...${NC}"
kubectl apply -f ../kubernetes/namespace.yaml

# Create service account and RBAC
echo -e "${YELLOW}Creating service account and RBAC...${NC}"
kubectl apply -f ../kubernetes/service-account.yaml

# Create ConfigMap
echo -e "${YELLOW}Creating ConfigMap...${NC}"
kubectl apply -f ../kubernetes/configmap.yaml

# Create secrets (if not using AWS Secrets Manager)
echo -e "${YELLOW}Note: Secrets should be created manually or via AWS Secrets Manager${NC}"
echo "Skipping secrets.yaml - ensure secrets are created before proceeding"
echo ""

# Deploy services
echo -e "${YELLOW}Deploying services...${NC}"
kubectl apply -f ../kubernetes/keep-extractor-deployment.yaml
kubectl apply -f ../kubernetes/notion-writer-deployment.yaml
kubectl apply -f ../kubernetes/sync-service-deployment.yaml
kubectl apply -f ../kubernetes/api-gateway-deployment.yaml
kubectl apply -f ../kubernetes/admin-interface-deployment.yaml

# Wait for deployments to be ready
echo -e "${YELLOW}Waiting for deployments to be ready...${NC}"
kubectl wait --for=condition=available --timeout=300s deployment/keep-extractor -n $NAMESPACE
kubectl wait --for=condition=available --timeout=300s deployment/notion-writer -n $NAMESPACE
kubectl wait --for=condition=available --timeout=300s deployment/sync-service -n $NAMESPACE
kubectl wait --for=condition=available --timeout=300s deployment/api-gateway -n $NAMESPACE
kubectl wait --for=condition=available --timeout=300s deployment/admin-interface -n $NAMESPACE

# Apply HPA
echo -e "${YELLOW}Configuring autoscaling...${NC}"
kubectl apply -f ../kubernetes/hpa.yaml

# Apply network policies (optional)
echo -e "${YELLOW}Applying network policies...${NC}"
kubectl apply -f ../kubernetes/network-policy.yaml

# Create ingress
echo -e "${YELLOW}Creating ingress...${NC}"
kubectl apply -f ../kubernetes/ingress.yaml

# Display deployment status
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment Status${NC}"
echo -e "${GREEN}========================================${NC}"
kubectl get pods -n $NAMESPACE
echo ""
kubectl get svc -n $NAMESPACE
echo ""
kubectl get ingress -n $NAMESPACE

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment completed successfully!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "To view logs:"
echo "  kubectl logs -f deployment/api-gateway -n $NAMESPACE"
echo ""
echo "To get ingress URL:"
echo "  kubectl get ingress keep-notion-sync-ingress -n $NAMESPACE -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'"
