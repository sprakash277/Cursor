#!/bin/bash

# Deployment script for VM
# This script sets up the Flask application on a VM

set -e  # Exit on error

echo "=========================================="
echo "Deploying Contest Scoring System"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
   echo -e "${RED}Please do not run as root${NC}"
   exit 1
fi

# Update system packages
echo -e "${YELLOW}Updating system packages...${NC}"
sudo apt-get update -qq

# Install Python and pip if not already installed
if ! command -v python3 &> /dev/null; then
    echo -e "${YELLOW}Installing Python 3...${NC}"
    sudo apt-get install -y python3 python3-pip python3-venv
fi

# Install nginx (optional, for reverse proxy)
if ! command -v nginx &> /dev/null; then
    echo -e "${YELLOW}Installing nginx...${NC}"
    sudo apt-get install -y nginx
fi

# Create application directory
APP_DIR="$HOME/scoring_app"
echo -e "${YELLOW}Setting up application directory: $APP_DIR${NC}"
mkdir -p $APP_DIR
cd $APP_DIR

# Clone or update from GitHub
if [ -d ".git" ]; then
    echo -e "${YELLOW}Pulling latest changes from GitHub...${NC}"
    git pull origin main || git pull origin master
else
    echo -e "${RED}Not a git repository. Please clone from GitHub first:${NC}"
    echo "git clone <your-repo-url> $APP_DIR"
    exit 1
fi

# Create virtual environment
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
echo -e "${YELLOW}Installing Python dependencies...${NC}"
pip install -r requirements.txt

# Create necessary directories
echo -e "${YELLOW}Creating necessary directories...${NC}"
mkdir -p uploads
mkdir -p data

# Set up environment variables
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}Creating .env file...${NC}"
    cat > .env << EOF
# Flask Configuration
FLASK_APP=app.py
FLASK_ENV=production
SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_hex(32))')

# Server Configuration
HOST=0.0.0.0
PORT=5000

# File Paths (update these as needed)
EXCEL_FILE_PATH=$APP_DIR/data/sanskriti-3.xlsx
UPLOAD_FOLDER=$APP_DIR/uploads
DATA_FOLDER=$APP_DIR/data
EOF
    echo -e "${GREEN}.env file created. Please update EXCEL_FILE_PATH if needed.${NC}"
fi

# Create data directory structure
mkdir -p data
mkdir -p uploads

# Set permissions
chmod +x run.sh
chmod +x start.sh 2>/dev/null || true

echo -e "${GREEN}=========================================="
echo "Deployment completed successfully!"
echo "==========================================${NC}"
echo ""
echo "Next steps:"
echo "1. Update .env file with your configuration"
echo "2. Place your Excel file in the data/ directory"
echo "3. Run: ./start.sh (or use systemd service)"
echo "4. Access the app at http://your-vm-ip:5000"
echo ""
