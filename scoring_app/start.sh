#!/bin/bash

# Production startup script for Flask application

set -e

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Set default values
export FLASK_APP=${FLASK_APP:-app.py}
export FLASK_ENV=${FLASK_ENV:-production}
export HOST=${HOST:-0.0.0.0}
export PORT=${PORT:-5000}

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "Error: Virtual environment not found. Please run deploy.sh first."
    exit 1
fi

# Create necessary directories
mkdir -p uploads
mkdir -p data

# Start the application
echo "Starting Flask application..."
echo "Host: $HOST"
echo "Port: $PORT"
echo "Environment: $FLASK_ENV"
echo ""

# Use gunicorn if available, otherwise use Flask's built-in server
if command -v gunicorn &> /dev/null; then
    echo "Starting with Gunicorn..."
    gunicorn -w 4 -b $HOST:$PORT --timeout 120 --access-logfile - --error-logfile - app:app
else
    echo "Gunicorn not found. Installing..."
    pip install gunicorn
    echo "Starting with Gunicorn..."
    gunicorn -w 4 -b $HOST:$PORT --timeout 120 --access-logfile - --error-logfile - app:app
fi
