#!/bin/bash
set -e

echo "Installing dependencies"
pip install --upgrade pip
pip install -r api/requirements.txt

echo "Downloading cache files"
python scripts/download_cache.py

echo "Build complete!"