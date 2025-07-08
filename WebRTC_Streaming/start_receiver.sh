#!/bin/bash
#
# Receiver Script for Video Streaming with Traffic Control
#
# This script starts the receiver components for video streaming with traffic control.
# It starts the video receiver, settings receiver, and performance measurement.
#
# Usage: ./start_receiver.sh SENDER_IP
#
# Author: Roo AI Assistant
# Date: May 2025

# Check if sender IP is provided
if [ -z "$1" ]; then
    echo -e "\033[0;31mError: Sender IP address is required.\033[0m"
    echo -e "Usage: $0 SENDER_IP"
    exit 1
fi

SENDER_IP="$1"

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

# Check for matplotlib
if ! module_exists matplotlib; then
    echo -e "${YELLOW}Matplotlib module not found.${NC}"
    echo -e "${YELLOW}Please install it using one of these methods:${NC}"
    echo -e "${YELLOW}1. System package: sudo apt install python3-matplotlib${NC}"
    echo -e "${YELLOW}2. In a virtual environment: python3 -m pip install matplotlib${NC}"
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
    
    # Kill receiver
    kill_process "direct_receiver.py"
    
    # Kill settings receiver
    kill_process "tc_settings_receiver.py"
    
    # Kill performance measurement
    kill_process "tc_performance_sync.py"
    
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
kill_process "direct_receiver.py"
kill_process "tc_settings_receiver.py"
kill_process "tc_performance_sync.py"

# Get current directory
CURRENT_DIR=$(pwd)

# Check for a terminal emulator
TERMINAL_CMD=$(check_terminal_emulator)

# Launch additional terminal windows if a terminal emulator is available
if [ -n "$TERMINAL_CMD" ]; then
    echo -e "${GREEN}Launching monitoring terminals...${NC}"
    
    # Launch terminal for receiver metrics API monitoring
    $TERMINAL_CMD -- bash -c "cd \"$CURRENT_DIR\" && echo 'Waiting for metrics API to start...' && sleep 5 && watch -n 1 'curl -s http://localhost:8001/metrics | python3 -m json.tool'; exec bash" &
    echo -e "${GREEN}Launched receiver metrics monitoring terminal.${NC}"
    
    # Launch terminal for log monitoring
    $TERMINAL_CMD -- bash -c "cd \"$CURRENT_DIR\" && echo 'Waiting for logs to be created...' && sleep 5 && tail -f logs/receiver.log; exec bash" &
    echo -e "${GREEN}Launched log monitoring terminal.${NC}"
    
    # Give time for terminals to launch
    sleep 1
else
    echo -e "${YELLOW}No supported terminal emulator found. Will not launch additional monitoring windows.${NC}"
    echo -e "${YELLOW}You can manually run these commands in separate terminals:${NC}"
    echo -e "${YELLOW}  watch -n 1 'curl -s http://localhost:8001/metrics | python3 -m json.tool'${NC}"
    echo -e "${YELLOW}  tail -f logs/receiver.log${NC}"
fi

# Create a directory for logs
mkdir -p logs

# Start the receiver
echo -e "\n${BLUE}======================================================${NC}"
echo -e "${BLUE}STARTING VIDEO RECEIVER${NC}"
echo -e "${BLUE}======================================================${NC}"

# Start the receiver in the background
$PYTHON_CMD direct_receiver.py --display --metrics-port 8001 > logs/receiver.log 2>&1 &
RECEIVER_PID=$!

# Wait a moment for receiver to start
sleep 2

# Check if receiver is running
if ! ps -p $RECEIVER_PID > /dev/null; then
    echo -e "${RED}Error: Receiver failed to start.${NC}"
    echo -e "${RED}Check logs/receiver.log for details.${NC}"
    cleanup
    exit 1
fi

echo -e "${GREEN}Receiver started successfully.${NC}"

# Start the settings receiver
echo -e "\n${BLUE}======================================================${NC}"
echo -e "${BLUE}STARTING SETTINGS RECEIVER${NC}"
echo -e "${BLUE}======================================================${NC}"

# Start the settings receiver in the background
$PYTHON_CMD tc_settings_receiver.py > logs/settings_receiver.log 2>&1 &
SETTINGS_PID=$!

# Wait a moment for settings receiver to start
sleep 2

# Check if settings receiver is running
if ! ps -p $SETTINGS_PID > /dev/null; then
    echo -e "${RED}Error: Settings receiver failed to start.${NC}"
    echo -e "${RED}Check logs/settings_receiver.log for details.${NC}"
    cleanup
    exit 1
fi

echo -e "${GREEN}Settings receiver started successfully.${NC}"

# Start the performance measurement
echo -e "\n${BLUE}======================================================${NC}"
echo -e "${BLUE}STARTING PERFORMANCE MEASUREMENT${NC}"
echo -e "${BLUE}======================================================${NC}"
echo -e "Sender IP: ${CYAN}$SENDER_IP${NC}"
echo -e "${BLUE}======================================================${NC}"

# Check if sudo is available
if command_exists sudo; then
    # Start the performance measurement with sudo
    sudo $PYTHON_CMD tc_performance_sync.py --sender-ip "$SENDER_IP" --receiver-ip localhost &
    PERF_PID=$!
else
    echo -e "${YELLOW}Warning: sudo not available. Trying to run without sudo.${NC}"
    # Start the performance measurement without sudo
    $PYTHON_CMD tc_performance_sync.py --sender-ip "$SENDER_IP" --receiver-ip localhost &
    PERF_PID=$!
fi

# Wait a moment for performance measurement to start
sleep 2

# Check if performance measurement is running
if ! ps -p $PERF_PID > /dev/null; then
    echo -e "${RED}Error: Performance measurement failed to start.${NC}"
    cleanup
    exit 1
fi

echo -e "${GREEN}Performance measurement started successfully.${NC}"

# Print status
echo -e "\n${GREEN}All receiver components are running.${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop all components.${NC}"

# Wait for user to press Ctrl+C
while true; do
    sleep 1
done