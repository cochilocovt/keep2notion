#!/bin/bash
# Install AWS Load Balancer Controller on EKS
# Usage: ./install-aws-load-balancer-controller.sh [CLUSTER_NAME] [AWS_REGION]

set -e

# Configuration
CLUSTER_NAME=${1:-keep-notion-sync}
AWS_REGION=${2:-us-east-1}
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Installing AWS Load Balancer Controller${NC}"
echo -e "${GREEN}========================================${NC}"
echo "Cluster: $CLUSTER_NAME"
echo "Region: $AWS_REGION"
echo "Account: $AWS_ACCOUNT_ID"
echo ""

# Update kubeconfig
echo -e "${YELLOW}Updating kubeconfig...${NC}"
aws eks update-kubeconfig --name $CLUSTER_NAME --region $AWS_REGION

# Add Helm repo
echo -e "${YELLOW}Adding EKS Helm repository...${NC}"
helm repo add eks https://aws.github.io/eks-charts
helm repo update

# Install AWS Load Balancer Controller
echo -e "${YELLOW}Installing AWS Load Balancer Controller...${NC}"
helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set clusterName=$CLUSTER_NAME \
  --set serviceAccount.create=true \
  --set serviceAccount.name=aws-load-balancer-controller \
  --set region=$AWS_REGION \
  --set vpcId=$(aws eks describe-cluster --name $CLUSTER_NAME --region $AWS_REGION --query "cluster.resourcesVpcConfig.vpcId" --output text)

# Wait for deployment
echo -e "${YELLOW}Waiting for controller to be ready...${NC}"
kubectl wait --for=condition=available --timeout=300s deployment/aws-load-balancer-controller -n kube-system

# Verify installation
echo -e "${YELLOW}Verifying installation...${NC}"
kubectl get deployment -n kube-system aws-load-balancer-controller

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}AWS Load Balancer Controller installed!${NC}"
echo -e "${GREEN}========================================${NC}"
