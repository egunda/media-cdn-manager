#!/bin/bash

# VIV Media CDN Manager - IAM Permission Automation
# This script grants the necessary IAM roles to your service account.

# Use colors for better readability
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}==================================================${NC}"
echo -e "${BLUE}       GCP IAM Permission Automation Script       ${NC}"
echo -e "${BLUE}==================================================${NC}"

# 1. Detect Service Account
if [ -f "credentials/key.json" ]; then
    SA_EMAIL=$(grep -o '"client_email": "[^"]*' credentials/key.json | cut -d'"' -f4)
    PROJECT_ID=$(grep -o '"project_id": "[^"]*' credentials/key.json | cut -d'"' -f4)
    echo -e "${GREEN}Detected Service Account:${NC} $SA_EMAIL"
    echo -e "${GREEN}Detected Project ID:${NC} $PROJECT_ID"
else
    echo -e "${YELLOW}No credentials/key.json found.${NC}"
    read -p "Enter Service Account Email: " SA_EMAIL
    read -p "Enter Project ID: " PROJECT_ID
fi

if [ -z "$SA_EMAIL" ] || [ -z "$PROJECT_ID" ]; then
    echo -e "${RED}Error: Service Account Email and Project ID are required.${NC}"
    exit 1
fi

# List of required roles
ROLES=(
    "roles/certificatemanager.editor"
    "roles/networkservices.edgeCacheAdmin"
    "roles/networkservices.edgeCacheUser"
    "roles/networkservices.edgeCacheViewer"
    "roles/networkservices.edgeNetworkViewer"
    "roles/secretmanager.admin"
    "roles/secretmanager.secretAccessor"
    "roles/storage.admin"
    "roles/viewer"
)

echo -e "\n${BLUE}Granting internal roles to $SA_EMAIL...${NC}"

for ROLE in "${ROLES[@]}"; do
    echo -ne "Granting $ROLE... "
    gcloud projects add-iam-policy-binding "$PROJECT_ID" \
        --member="serviceAccount:$SA_EMAIL" \
        --role="$ROLE" \
        --quiet > /dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}DONE${NC}"
    else
        echo -e "${RED}FAILED${NC}"
    fi
done

echo -e "\n${BLUE}==================================================${NC}"
echo -e "${GREEN}        IAM Automation Completed Successfully!     ${NC}"
echo -e "${BLUE}==================================================${NC}"
echo -e "Your service account now has all necessary permissions"
echo -e "to manage Media CDN, Certificates, and Secrets."
