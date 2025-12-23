#!/bin/bash
# Complete VM setup script for Google Cloud

set -e

echo "=========================================="
echo "Product Recommendation API - VM Setup"
echo "=========================================="

# Update system
echo "Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install Python
echo "Installing Python 3.11"
sudo apt install -y python3-pip python3-venv git

# Navigate to app directory
cd ~/app

# Create virtual environment
echo "Creating virtual environment"
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
echo "Installing Python packages"
pip install -r api/requirements.txt

# Set environment variables
echo "Setting environment variables..."
export QDRANT_URL="https://your-qdrant-url"
export QDRANT_API_KEY="your-api-key"
export GCS_BUCKET_NAME="your-bucket-name"

# Download cache files
echo "Downloading cache files from GCS..."
python scripts/download_cache.py

# Verify cache
ls -lh cache/

echo ""
echo "Setup complete!"
echo ""
echo "To start the API:"
echo "  cd ~/app"
echo "  source venv/bin/activate"
echo "  uvicorn api.main:app --host 0.0.0.0 --port 8080"
echo ""