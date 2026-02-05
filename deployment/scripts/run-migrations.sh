#!/bin/bash
# Run Database Migrations
# Usage: ./run-migrations.sh [DB_HOST] [DB_NAME] [DB_USER] [DB_PASSWORD]

set -e

# Configuration
DB_HOST=${1:-localhost}
DB_NAME=${2:-keep_notion_sync}
DB_USER=${3:-postgres}
DB_PASSWORD=${4}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Running Database Migrations${NC}"
echo -e "${GREEN}========================================${NC}"
echo "Database Host: $DB_HOST"
echo "Database Name: $DB_NAME"
echo "Database User: $DB_USER"
echo ""

# Check if password is provided
if [ -z "$DB_PASSWORD" ]; then
    echo -e "${RED}Error: DB_PASSWORD is required${NC}"
    echo "Usage: ./run-migrations.sh [DB_HOST] [DB_NAME] [DB_USER] [DB_PASSWORD]"
    exit 1
fi

# Set environment variables for Alembic
export DB_HOST=$DB_HOST
export DB_NAME=$DB_NAME
export DB_USER=$DB_USER
export DB_PASSWORD=$DB_PASSWORD
export DB_PORT=${DB_PORT:-5432}

# Navigate to database directory
cd ../../database

# Check current migration status
echo -e "${YELLOW}Checking current migration status...${NC}"
alembic current

# Run migrations
echo -e "${YELLOW}Running migrations...${NC}"
alembic upgrade head

# Verify migration status
echo -e "${YELLOW}Verifying migration status...${NC}"
alembic current

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Migrations completed successfully!${NC}"
echo -e "${GREEN}========================================${NC}"
