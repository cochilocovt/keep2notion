#!/bin/bash
# Setup AWS Infrastructure using Terraform
# Usage: ./setup-aws-infrastructure.sh [init|plan|apply|destroy]

set -e

# Configuration
ACTION=${1:-plan}
TERRAFORM_DIR="../terraform"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}AWS Infrastructure Setup${NC}"
echo -e "${GREEN}========================================${NC}"
echo "Action: $ACTION"
echo ""

# Navigate to Terraform directory
cd $TERRAFORM_DIR

# Check if terraform.tfvars exists
if [ ! -f "terraform.tfvars" ]; then
    echo -e "${YELLOW}Warning: terraform.tfvars not found${NC}"
    echo "Creating terraform.tfvars from example..."
    cat > terraform.tfvars <<EOF
# AWS Configuration
aws_region = "us-east-1"
project_name = "keep-notion-sync"
environment = "production"

# Database Configuration
db_username = "dbadmin"
db_password = "CHANGE_ME_SECURE_PASSWORD"

# Tags
tags = {
  Project   = "keep-notion-sync"
  ManagedBy = "terraform"
}
EOF
    echo -e "${RED}Please update terraform.tfvars with your configuration before proceeding${NC}"
    exit 1
fi

case $ACTION in
    init)
        echo -e "${YELLOW}Initializing Terraform...${NC}"
        terraform init
        ;;
    
    plan)
        echo -e "${YELLOW}Planning infrastructure changes...${NC}"
        terraform plan
        ;;
    
    apply)
        echo -e "${YELLOW}Applying infrastructure changes...${NC}"
        terraform apply
        
        if [ $? -eq 0 ]; then
            echo ""
            echo -e "${GREEN}========================================${NC}"
            echo -e "${GREEN}Infrastructure created successfully!${NC}"
            echo -e "${GREEN}========================================${NC}"
            echo ""
            echo "Next steps:"
            echo "1. Update Kubernetes manifests with actual resource values"
            echo "2. Build and push Docker images: ./build-and-push-images.sh"
            echo "3. Run database migrations: ./run-migrations.sh"
            echo "4. Deploy to EKS: ./deploy-to-eks.sh"
            echo "5. Configure DNS for ingress endpoints"
        fi
        ;;
    
    destroy)
        echo -e "${RED}WARNING: This will destroy all infrastructure!${NC}"
        read -p "Are you sure? (yes/no): " confirm
        if [ "$confirm" == "yes" ]; then
            echo -e "${YELLOW}Destroying infrastructure...${NC}"
            terraform destroy
        else
            echo "Destroy cancelled"
        fi
        ;;
    
    output)
        echo -e "${YELLOW}Displaying Terraform outputs...${NC}"
        terraform output
        ;;
    
    *)
        echo -e "${RED}Invalid action: $ACTION${NC}"
        echo "Usage: ./setup-aws-infrastructure.sh [init|plan|apply|destroy|output]"
        exit 1
        ;;
esac
