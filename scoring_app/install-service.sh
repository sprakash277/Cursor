#!/bin/bash

# Script to install systemd service for the Flask application

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Get current user
CURRENT_USER=$(whoami)
APP_DIR="$HOME/scoring_app"
SERVICE_FILE="scoring-app.service"

echo -e "${YELLOW}Installing systemd service...${NC}"

# Check if service file exists
if [ ! -f "$SERVICE_FILE" ]; then
    echo -e "${RED}Error: $SERVICE_FILE not found${NC}"
    exit 1
fi

# Create logs directory
mkdir -p "$APP_DIR/logs"

# Create temporary service file with user-specific paths
TEMP_SERVICE="/tmp/scoring-app-${CURRENT_USER}.service"
sed "s|%i|$CURRENT_USER|g; s|%h|$HOME|g" "$SERVICE_FILE" > "$TEMP_SERVICE"

# Copy service file to systemd directory
echo -e "${YELLOW}Copying service file to /etc/systemd/system/...${NC}"
sudo cp "$TEMP_SERVICE" "/etc/systemd/system/scoring-app.service"

# Reload systemd
echo -e "${YELLOW}Reloading systemd...${NC}"
sudo systemctl daemon-reload

# Enable service
echo -e "${YELLOW}Enabling service...${NC}"
sudo systemctl enable scoring-app.service

echo -e "${GREEN}Service installed successfully!${NC}"
echo ""
echo "To start the service:"
echo "  sudo systemctl start scoring-app"
echo ""
echo "To stop the service:"
echo "  sudo systemctl stop scoring-app"
echo ""
echo "To check status:"
echo "  sudo systemctl status scoring-app"
echo ""
echo "To view logs:"
echo "  sudo journalctl -u scoring-app -f"
