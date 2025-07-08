#!/bin/bash
#
# Sender Script for Video Streaming with Traffic Control
#
# This script starts the sender components for video streaming with traffic control.
# It starts the traffic control script and the video sender.
#
# Usage: sudo ./start_sender.sh RECEIVER_IP [VIDEO_PATH]
#
# Author: Roo AI Assistant
# Date: May 2025

# Check if receiver IP is provided
if [ -z "$1" ]; then
    echo -e "\033[0;31mError: Receiver IP address is required.\033[0m"
    echo -e "Usage: sudo $0 RECEIVER_IP [VIDEO_PATH]"
    exit 1
fi

RECEIVER_IP="$1"
VIDEO_PATH="../video/zidane.mp4"  # Default video path

# Check if video path is provided
if [ ! -z "$2" ]; then
    VIDEO_PATH="$2"
fi

# Check if running as root
if [[ $EUID -ne 0 ]]; then
    echo -e "\033[0;31mThis script requires root privileges to modify network settings.\033[0m"
    echo -e "\033[0;31mPlease run with sudo: sudo $0 $RECEIVER_IP $VIDEO_PATH\033[0m"
    exit 1
fi

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

# Check if required commands exist
if ! command_exists tc; then
    echo -e "${RED}Error: tc (traffic control) is not installed.${NC}"
    echo -e "${RED}Please install it with: sudo apt install iproute2${NC}"
    exit 1
fi

if ! command_exists curl; then
    echo -e "${RED}Error: curl is not installed.${NC}"
    echo -e "${RED}Please install it with: sudo apt install curl${NC}"
    exit 1
fi

# Check if a local virtual environment exists
if [ -d "./venv" ] && [ -f "./venv/bin/python" ]; then
    echo -e "${GREEN}Using local virtual environment: ./venv${NC}"
    PYTHON_CMD="./venv/bin/python"
elif [ -n "$VIRTUAL_ENV" ]; then
    echo -e "${GREEN}Running in virtual environment: $VIRTUAL_ENV${NC}"
    PYTHON_CMD="$VIRTUAL_ENV/bin/python"
else
    # Check for python - try both python and python3
    PYTHON_CMD=""
    if command_exists python3; then
        PYTHON_CMD="python3"
    elif command_exists python; then
        PYTHON_CMD="python"
    else
        echo -e "${RED}Error: Neither python nor python3 is installed.${NC}"
        echo -e "${RED}Please install it with: sudo apt install python3${NC}"
        exit 1
    fi
fi

echo -e "${GREEN}Using Python command: $PYTHON_CMD${NC}"

# Check for required Python modules
echo -e "${BLUE}Checking for required Python modules...${NC}"

# Function to check if a Python module is installed
module_exists() {
    $PYTHON_CMD -c "import $1" 2>/dev/null
    return $?
}

# Check for OpenCV
if ! module_exists cv2; then
    echo -e "${YELLOW}OpenCV (cv2) module not found.${NC}"
    echo -e "${YELLOW}Please install it using one of these methods:${NC}"
    echo -e "${YELLOW}1. System package: sudo apt install python3-opencv${NC}"
    echo -e "${YELLOW}2. In a virtual environment: python3 -m pip install opencv-python${NC}"
    exit 1
fi

# Check for NumPy
if ! module_exists numpy; then
    echo -e "${YELLOW}NumPy module not found.${NC}"
    echo -e "${YELLOW}Please install it using one of these methods:${NC}"
    echo -e "${YELLOW}1. System package: sudo apt install python3-numpy${NC}"
    echo -e "${YELLOW}2. In a virtual environment: python3 -m pip install numpy${NC}"
    exit 1
fi

# Check for requests
if ! module_exists requests; then
    echo -e "${YELLOW}Requests module not found.${NC}"
    echo -e "${YELLOW}Please install it using one of these methods:${NC}"
    echo -e "${YELLOW}1. System package: sudo apt install python3-requests${NC}"
    echo -e "${YELLOW}2. In a virtual environment: python3 -m pip install requests${NC}"
    exit 1
fi

echo -e "${GREEN}All required Python modules are installed.${NC}"

# Function to check if a process is running
is_running() {
    pgrep -f "$1" > /dev/null
}

# Function to kill a process
kill_process() {
    pkill -f "$1" 2> /dev/null
}

# Function to clean up on exit
cleanup() {
    echo -e "\n${YELLOW}Cleaning up...${NC}"
    
    # Kill traffic control script
    kill_process "auto_tc_control_sync.sh"
    
    # Kill sender
    kill_process "direct_sender.py"
    
    # Reset traffic control
    tc qdisc del dev $(ip route | grep default | head -n 1 | awk '{print $5}') root 2> /dev/null
    
    echo -e "${GREEN}Cleanup complete.${NC}"
    exit 0
}

# Function to check if a terminal emulator is available
check_terminal_emulator() {
    if command_exists gnome-terminal; then
        echo "gnome-terminal"
    elif command_exists xterm; then
        echo "xterm"
    elif command_exists konsole; then
        echo "konsole"
    elif command_exists terminator; then
        echo "terminator"
    else
        echo ""
    fi
}

# Trap Ctrl+C to clean up
trap cleanup INT

# Kill any existing processes
echo -e "${BLUE}Stopping any existing processes...${NC}"
kill_process "auto_tc_control_sync.sh"
kill_process "direct_sender.py"

# Reset traffic control
echo -e "${BLUE}Resetting traffic control...${NC}"
tc qdisc del dev $(ip route | grep default | head -n 1 | awk '{print $5}') root 2> /dev/null

# Get current directory
CURRENT_DIR=$(pwd)

# Check for a terminal emulator
TERMINAL_CMD=$(check_terminal_emulator)

# Launch additional terminal windows if a terminal emulator is available
if [ -n "$TERMINAL_CMD" ]; then
    echo -e "${GREEN}Launching monitoring terminals...${NC}"
    
    # Launch terminal for traffic control monitoring
    if [ -f "./monitor_tc.sh" ]; then
        $TERMINAL_CMD -- bash -c "cd \"$CURRENT_DIR\" && ./monitor_tc.sh; exec bash" &
        echo -e "${GREEN}Launched traffic control monitoring terminal.${NC}"
    else
        echo -e "${YELLOW}Warning: monitor_tc.sh not found. Skipping monitoring terminal.${NC}"
    fi
    
    # Launch terminal for metrics API monitoring
    $TERMINAL_CMD -- bash -c "cd \"$CURRENT_DIR\" && echo 'Waiting for metrics API to start...' && sleep 5 && watch -n 1 'curl -s http://localhost:8000/metrics | python3 -m json.tool'; exec bash" &
    echo -e "${GREEN}Launched metrics API monitoring terminal.${NC}"
    
    # Give time for terminals to launch
    sleep 1
else
    echo -e "${YELLOW}No supported terminal emulator found. Will not launch additional monitoring windows.${NC}"
    echo -e "${YELLOW}You can manually run these commands in separate terminals:${NC}"
    echo -e "${YELLOW}  ./monitor_tc.sh${NC}"
    echo -e "${YELLOW}  watch -n 1 'curl -s http://localhost:8000/metrics | python3 -m json.tool'${NC}"
fi

# Start traffic control with synchronization
echo -e "\n${BLUE}======================================================${NC}"
echo -e "${BLUE}STARTING TRAFFIC CONTROL WITH SYNCHRONIZATION${NC}"
echo -e "${BLUE}======================================================${NC}"
echo -e "Receiver IP: ${CYAN}$RECEIVER_IP${NC}"
echo -e "${BLUE}======================================================${NC}"

# Start traffic control in the background
./auto_tc_control_sync.sh "$RECEIVER_IP" &
TC_PID=$!

# Wait a moment for traffic control to start
sleep 2

# Check if traffic control is running
if ! ps -p $TC_PID > /dev/null; then
    echo -e "${RED}Error: Traffic control failed to start.${NC}"
    cleanup
    exit 1
fi

echo -e "${GREEN}Traffic control started successfully.${NC}"

# Start the sender
echo -e "\n${BLUE}======================================================${NC}"
echo -e "${BLUE}STARTING VIDEO SENDER${NC}"
echo -e "${BLUE}======================================================${NC}"
echo -e "Receiver IP: ${CYAN}$RECEIVER_IP${NC}"
echo -e "Video Path: ${CYAN}$VIDEO_PATH${NC}"
echo -e "${BLUE}======================================================${NC}"

# Check if video file exists
if [ ! -f "$VIDEO_PATH" ]; then
    echo -e "${RED}Error: Video file not found: $VIDEO_PATH${NC}"
    echo -e "${RED}Please provide a valid video path.${NC}"
    cleanup
    exit 1
fi

# Start the sender in the background
$PYTHON_CMD direct_sender.py --ip "$RECEIVER_IP" --video "$VIDEO_PATH" --metrics-port 8000 &
SENDER_PID=$!

# Wait a moment for sender to start
sleep 2

# Check if sender is running
if ! ps -p $SENDER_PID > /dev/null; then
    echo -e "${RED}Error: Sender failed to start.${NC}"
    cleanup
    exit 1
fi

echo -e "${GREEN}Sender started successfully.${NC}"

# Print status
echo -e "\n${GREEN}All sender components are running.${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop all components.${NC}"

# Wait for user to press Ctrl+C
while true; do
    sleep 1
done