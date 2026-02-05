#!/bin/bash

# Setup script for Google Keep to Notion Sync

set -e

echo "Setting up Google Keep to Notion Sync..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "Creating .env file from .env.example..."
    cp .env.example .env
    echo "Please edit .env file with your configuration before running the services."
fi

# Create Python virtual environment for local development
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install shared dependencies
echo "Installing shared dependencies..."
pip install -r shared/requirements.txt

# Install database dependencies
echo "Installing database dependencies..."
pip install -r database/requirements.txt

echo ""
echo "Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your configuration"
echo "2. Run 'docker-compose up' to start all services"
echo "3. Access the admin interface at http://localhost:8000"
echo ""
echo "For local development:"
echo "1. Activate virtual environment: source venv/bin/activate"
echo "2. Run individual services from their directories"
echo ""
