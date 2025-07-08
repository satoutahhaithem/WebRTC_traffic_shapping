#!/bin/bash
#
# Start Stable Sender
#
# This script starts both the stable traffic control and the video sender.
#
# Usage: sudo ./start_stable_sender.sh RECEIVER_IP [VIDEO_PATH]
#
# Author: Roo AI Assistant
# Date: May 2025

# --- Configuration ---
RECEIVER_IP="$1"
VIDEO_PATH="${2:-../video/zidane.mp4}" # Default video path if not provided

# Define color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# --- Validation ---
if [[ $EUID -ne 0 ]]; then
    echo -e "${RED}This script requires root privileges. Please run with sudo.${NC}"
    exit 1
fi

if [ -z "$RECEIVER_IP" ]; then
    echo -e "${RED}Error: Receiver IP address is required.${NC}"
    echo -e "Usage: sudo $0 RECEIVER_IP [VIDEO_PATH]"
    exit 1
fi

# --- Cleanup Function ---
cleanup() {
    echo -e "\n${YELLOW}Cleaning up...${NC}"
    # Kill the stable traffic control script
    if [[ ! -z "$TC_PID" ]]; then
        kill $TC_PID 2>/dev/null
    fi
    # Kill the sender script
    if [[ ! -z "$SENDER_PID" ]]; then
        kill $SENDER_PID 2>/dev/null
    fi
    # Reset TC rules just in case
    INTERFACE=$(ip route | grep default | head -n 1 | awk '{print $5}')
    if [[ ! -z "$INTERFACE" ]]; then
        tc qdisc del dev $INTERFACE root 2>/dev/null
    fi
    echo -e "${GREEN}Cleanup complete.${NC}"
    exit 0
}

trap cleanup INT

# --- Main Execution ---

# 1. Start the stable traffic control in the background
echo -e "${BLUE}Starting stable traffic control...${NC}"
./set_stable_tc.sh &
TC_PID=$!
sleep 2 # Give it a moment to apply rules

if ! ps -p $TC_PID > /dev/null; then
    echo -e "${RED}Error: Failed to start set_stable_tc.sh${NC}"
    exit 1
fi
echo -e "${GREEN}Traffic control is active.${NC}"

# 2. Start the video sender in the foreground
echo -e "\n${BLUE}Starting video sender...${NC}"
python3 direct_sender.py --ip "$RECEIVER_IP" --video "$VIDEO_PATH"
SENDER_PID=$!

# The script will wait here until the sender is stopped (e.g., with Ctrl+C).
# The trap will then handle the cleanup.
wait $SENDER_PID