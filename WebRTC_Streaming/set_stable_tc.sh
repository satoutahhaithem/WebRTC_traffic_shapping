#!/bin/bash
#
# Set Stable Traffic Control for WebRTC Streaming
#
# This script applies a stable, ultra-low-latency network configuration
# to provide the best possible streaming performance.
#
# Usage: sudo ./set_stable_tc.sh
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

# --- Configuration ---
INTERFACE="" # Will be auto-detected

# --- Functions ---

# Function to detect the default network interface
detect_interface() {
    DEFAULT_ROUTE=$(ip route | grep default | head -n 1)
    if [[ -n "$DEFAULT_ROUTE" ]]; then
        INTERFACE=$(echo "$DEFAULT_ROUTE" | awk '{print $5}')
        echo -e "${GREEN}Detected default interface: $INTERFACE${NC}"
    else
        echo -e "${RED}Could not detect default network interface. Exiting.${NC}"
        exit 1
    fi
}

# Function to apply ultra-low-latency conditions
apply_ultra_conditions() {
    echo -e "\n${BLUE}======================================================${NC}"
    echo -e "${BLUE}APPLYING STABLE ULTRA-LOW-LATENCY CONDITIONS${NC}"
    echo -e "${BLUE}======================================================${NC}"

    # First, reset any existing traffic control settings to avoid conflicts
    sudo tc qdisc del dev $INTERFACE root 2>/dev/null
    echo "Cleared existing TC rules."

    # Create a hierarchical token bucket (HTB) qdisc as the root
    sudo tc qdisc add dev $INTERFACE root handle 1: htb default 10
    echo "Added HTB qdisc."

    # Add a class with high bandwidth
    sudo tc class add dev $INTERFACE parent 1: classid 1:10 htb rate 100mbit ceil 100mbit burst 25k
    echo "Added HTB class with 100mbit rate."

    # Add minimal network emulation parameters for low latency
    sudo tc qdisc add dev $INTERFACE parent 1:10 handle 10: netem delay 1ms
    echo "Added netem with 1ms delay."

    # Add SFQ (Stochastic Fairness Queueing) for better packet scheduling
    sudo tc qdisc add dev $INTERFACE parent 10: handle 100: sfq perturb 10
    echo "Added SFQ for fairness."

    echo -e "${GREEN}ULTRA-LOW-LATENCY conditions applied successfully!${NC}"
    echo -e "${YELLOW}These settings will remain active until you stop the script (Ctrl+C) or reboot.${NC}"
    echo -e "${BLUE}======================================================${NC}"
}

# Function to reset network conditions
reset_conditions() {
    echo -e "\n${BLUE}======================================================${NC}"
    echo -e "${BLUE}RESETTING NETWORK CONDITIONS${NC}"
    echo -e "${BLUE}======================================================${NC}"
    sudo tc qdisc del dev $INTERFACE root 2>/dev/null
    echo -e "${GREEN}Network conditions reset successfully.${NC}"
    echo -e "${BLUE}======================================================${NC}"
}

# --- Main Script ---

# Check if running as root
if [[ $EUID -ne 0 ]]; then
    echo -e "${RED}This script requires root privileges to modify network settings.${NC}"
    echo -e "${RED}Please run with sudo: sudo $0${NC}"
    exit 1
fi

# Check if tc is installed
if ! command -v tc &> /dev/null; then
    echo -e "${RED}Error: tc (traffic control) is not installed.${NC}"
    echo -e "${RED}Please install it with: sudo apt install iproute2${NC}"
    exit 1
fi

# Trap Ctrl+C to reset conditions before exiting
trap 'echo -e "\n${YELLOW}Stopping...${NC}"; reset_conditions; exit 0' INT

# Detect the network interface
detect_interface

# Apply the stable conditions
apply_ultra_conditions

# Keep the script running to hold the settings
echo -e "${CYAN}Network shaping is active. Press Ctrl+C to stop and reset.${NC}"
while true; do
    sleep 60
done