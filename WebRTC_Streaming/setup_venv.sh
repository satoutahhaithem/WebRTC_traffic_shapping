#!/bin/bash
#
# Setup Script for Video Streaming with Traffic Control
#
# This script creates a virtual environment and installs the required dependencies.
#
# Usage: ./setup_venv.sh
#
# Author: Roo AI Assistant
# Date: May 2025

# Define color codes for better readability
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Function to check if a command exists
command_exists() {
    command -v "$1" &> /dev/null
}

# Check if python3 is installed
if ! command_exists python3; then
    echo -e "${RED}Error: python3 is not installed.${NC}"
    echo -e "${RED}Please install it with: sudo apt install python3${NC}"
    exit 1
fi

# Check if python3-venv is installed
if ! python3 -m venv --help &> /dev/null; then
    echo -e "${YELLOW}python3-venv is not installed. Attempting to install...${NC}"
    sudo apt install python3-venv
    
    # Check if installation was successful
    if ! python3 -m venv --help &> /dev/null; then
        echo -e "${RED}Error: Failed to install python3-venv. Please install it manually:${NC}"
        echo -e "${RED}sudo apt install python3-venv${NC}"
        exit 1
    fi
    echo -e "${GREEN}python3-venv installed successfully.${NC}"
fi

# Create a virtual environment
echo -e "${BLUE}Creating virtual environment...${NC}"
python3 -m venv venv

# Activate the virtual environment
echo -e "${BLUE}Activating virtual environment...${NC}"
source venv/bin/activate

# Install dependencies
echo -e "${BLUE}Installing dependencies...${NC}"
pip install -r requirements.txt

# Check if installation was successful
if [ $? -eq 0 ]; then
    echo -e "${GREEN}Dependencies installed successfully.${NC}"
    echo -e "${GREEN}Virtual environment setup complete.${NC}"
    echo -e "${YELLOW}To activate the virtual environment, run:${NC}"
    echo -e "${YELLOW}source venv/bin/activate${NC}"
else
    echo -e "${RED}Error: Failed to install dependencies.${NC}"
    exit 1
fi