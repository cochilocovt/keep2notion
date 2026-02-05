#!/bin/bash
# Build and Push Docker Images to ECR
# Usage: ./build-and-push-images.sh [AWS_REGION] [AWS_ACCOUNT_ID]

set -e

# Configuration
AWS_REGION=${1:-us-east-1}
AWS_ACCOUNT_ID=${2:-$(aws sts get-caller-identity --query Account --output text)}
PROJECT_NAME="keep-notion-sync"
VERSION=${VERSION:-latest}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Building and Pushing Docker Images${NC}"
echo -e "${GREEN}========================================${NC}"
echo "AWS Region: $AWS_REGION"
echo "AWS Account: $AWS_ACCOUNT_ID"
echo "Version: $VERSION"
echo ""

# Authenticate with ECR
echo -e "${YELLOW}Authenticating with ECR...${NC}"
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Services to build
SERVICES=("api-gateway" "admin-interface" "sync-service" "keep-extractor" "notion-writer")

# Build and push each service
for SERVICE in "${SERVICES[@]}"; do
    echo -e "${YELLOW}Building $SERVICE...${NC}"
    
    # Determine service directory
    if [ "$SERVICE" == "api-gateway" ]; then
        SERVICE_DIR="services/api_gateway"
    elif [ "$SERVICE" == "admin-interface" ]; then
        SERVICE_DIR="services/admin_interface"
    elif [ "$SERVICE" == "sync-service" ]; then
        SERVICE_DIR="services/sync_service"
    elif [ "$SERVICE" == "keep-extractor" ]; then
        SERVICE_DIR="services/keep_extractor"
    elif [ "$SERVICE" == "notion-writer" ]; then
        SERVICE_DIR="services/notion_writer"
    fi
    
    # ECR repository URL
    ECR_REPO="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$PROJECT_NAME/$SERVICE"
    
    # Build Docker image
    echo "Building Docker image for $SERVICE..."
    docker build -t $SERVICE:$VERSION -f $SERVICE_DIR/Dockerfile .
    
    # Tag image for ECR
    docker tag $SERVICE:$VERSION $ECR_REPO:$VERSION
    docker tag $SERVICE:$VERSION $ECR_REPO:latest
    
    # Push to ECR
    echo "Pushing $SERVICE to ECR..."
    docker push $ECR_REPO:$VERSION
    docker push $ECR_REPO:latest
    
    echo -e "${GREEN}✓ $SERVICE pushed successfully${NC}"
    echo ""
done

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}All images built and pushed successfully!${NC}"
echo -e "${GREEN}========================================${NC}"
