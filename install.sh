#!/bin/bash

# Media CDN Manager - Automated Installer for Debian/Ubuntu
# Website: https://github.com/egunda/media-cdn-manager

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}==================================================${NC}"
echo -e "${BLUE}          Media CDN Manager Installer             ${NC}"
echo -e "${BLUE}==================================================${NC}"

# Check for root
if [ "$EUID" -ne 0 ]; then
  echo -e "${RED}Please run as root${NC}"
  exit 1
fi

# Update system
echo -e "${GREEN}[1/5] Updating system packages...${NC}"
apt-get update && apt-get upgrade -y

# Install dependencies
echo -e "${GREEN}[2/5] Installing dependencies (Python, OpenSSL, Git)...${NC}"
apt-get install -y python3 python3-pip python3-venv openssl git curl

# Setup Directory
INSTALL_DIR="/opt/media-cdn-manager"
echo -e "${GREEN}[3/5] Setting up application in ${INSTALL_DIR}...${NC}"

if [ -d "$INSTALL_DIR" ]; then
    echo -e "${BLUE}Directory exists, updating source...${NC}"
    cd "$INSTALL_DIR"
    # git pull # Uncomment if you want to auto-update
else
    git clone https://github.com/egunda/media-cdn-manager "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# Setup Virtual Environment
echo -e "${GREEN}[4/5] Setting up Python virtual environment...${NC}"
python3 -m venv venv
# Note: Currently no external python dependencies are strictly required 
# as the project uses native libraries, but venv is good practice.
# ./venv/bin/pip install -r requirements.txt # Add if needed in future

# Create credentials directory if not exists
mkdir -p credentials

# Setup Systemd Service
echo -e "${GREEN}[5/5] Configuring systemd service...${NC}"
cat <<EOF > /etc/systemd/system/media-cdn-manager.service
[Unit]
Description=Media CDN Manager Dashboard
After=network.target

[Service]
User=root
WorkingDirectory=${INSTALL_DIR}
ExecStart=${INSTALL_DIR}/venv/bin/python3 ${INSTALL_DIR}/backend/main.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable media-cdn-manager.service

echo -e "${BLUE}==================================================${NC}"
echo -e "${GREEN}      Installation Complete Successfully!         ${NC}"
echo -e "${BLUE}==================================================${NC}"
echo -e ""
echo -e "Next Steps:"
echo -e "1. Place your GCP Service Account JSON key in:"
echo -e "   ${INSTALL_DIR}/credentials/key.json"
echo -e ""
echo -e "2. Start the service:"
echo -e "   systemctl start media-cdn-manager"
echo -e ""
echo -e "3. Access the dashboard at:"
echo -e "   http://$(hostname -I | awk '{print $1}'):8080"
echo -e ""
echo -e "${BLUE}==================================================${NC}"
