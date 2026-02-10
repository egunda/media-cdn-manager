#!/bin/bash
# Move to the project root
cd "$(dirname "$0")"

# Terminate existing backend process if running
echo "Cleaning up existing processes on port 6001..."
lsof -ti:6001 | xargs kill -9 2>/dev/null

# Load environment variables if .env exists
if [ -f .env ]; then
    echo "Loading environment variables from .env..."
    export $(grep -v '^#' .env | xargs)
fi

# Start the native backend
echo "Starting Media CDN Deployer Backend at http://localhost:6001..."
echo "Using native implementation (no external dependencies required)."
python3 backend/main.py
