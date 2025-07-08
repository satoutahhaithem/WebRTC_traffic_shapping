#!/bin/bash
#
# Traffic Control Monitoring Script
#
# This script continuously monitors and displays the current traffic control settings
# with timestamps to show when they change.
#
# Usage: ./monitor_tc.sh [interval]
#   interval: Optional monitoring interval in seconds (default: 1)
#

# Set default monitoring interval
INTERVAL=${1:-1}

# Define color codes for better readability
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Function to detect the default network interface
detect_interface() {
    # Try to get the default interface used for internet access
    DEFAULT_ROUTE=$(ip route | grep default | head -n 1)
    if [[ -n "$DEFAULT_ROUTE" ]]; then
        INTERFACE=$(echo "$DEFAULT_ROUTE" | awk '{print $5}')
        echo -e "${GREEN}Detected default interface: $INTERFACE${NC}"
        return 0
    fi
    
    # If no default route, list available interfaces
    echo -e "${YELLOW}Could not detect default interface automatically.${NC}"
    echo "Available interfaces:"
    ip -o link show | grep -v "lo:" | awk -F': ' '{print "  " $2}'
    
    # Ask user to select an interface
    read -p "Enter interface name: " INTERFACE
    
    if [[ -z "$INTERFACE" ]]; then
        echo -e "${RED}No interface selected. Exiting.${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}Using interface: $INTERFACE${NC}"
    return 0
}

# Function to determine the current network condition preset
determine_preset() {
    local tc_output="$1"
    
    if [[ "$tc_output" == *"rate 1Mbit"* && "$tc_output" == *"delay 300ms"* && "$tc_output" == *"loss 5%"* ]]; then
        echo "${RED}VERY POOR${NC}"
    elif [[ "$tc_output" == *"rate 2Mbit"* && "$tc_output" == *"delay 150ms"* && "$tc_output" == *"loss 3%"* ]]; then
        echo "${YELLOW}POOR${NC}"
    elif [[ "$tc_output" == *"rate 4Mbit"* && "$tc_output" == *"delay 80ms"* && "$tc_output" == *"loss 1%"* ]]; then
        echo "${YELLOW}FAIR${NC}"
    elif [[ "$tc_output" == *"rate 6Mbit"* && "$tc_output" == *"delay 40ms"* && "$tc_output" == *"loss 0.5%"* ]]; then
        echo "${GREEN}GOOD${NC}"
    elif [[ "$tc_output" == *"rate 10Mbit"* && "$tc_output" == *"delay 20ms"* && "$tc_output" == *"loss 0%"* ]]; then
        echo "${GREEN}EXCELLENT${NC}"
    elif [[ "$tc_output" == *"rate 50Mbit"* && "$tc_output" == *"delay 1ms"* ]]; then
        echo "${PURPLE}ULTRA${NC}"
    else
        echo "${BLUE}CUSTOM${NC}"
    fi
}

# Function to display current network conditions
show_conditions() {
    # Get current time
    local current_time=$(date "+%Y-%m-%d %H:%M:%S")
    
    # Get tc output
    local tc_output=$(tc qdisc show dev $INTERFACE)
    
    # Determine preset
    local preset=$(determine_preset "$tc_output")
    
    # Extract rate, delay, and loss if available
    local rate="N/A"
    local delay="N/A"
    local loss="N/A"
    
    if [[ "$tc_output" == *"rate"* ]]; then
        rate=$(echo "$tc_output" | grep -o "rate [^ ]*" | cut -d' ' -f2)
    fi
    
    if [[ "$tc_output" == *"delay"* ]]; then
        delay=$(echo "$tc_output" | grep -o "delay [^ ]*" | cut -d' ' -f2)
    fi
    
    if [[ "$tc_output" == *"loss"* ]]; then
        loss=$(echo "$tc_output" | grep -o "loss [^ ]*" | cut -d' ' -f2)
    fi
    
    # Display the information
    echo -e "${CYAN}[$current_time]${NC} Condition: $preset | Rate: ${YELLOW}$rate${NC} | Delay: ${YELLOW}$delay${NC} | Loss: ${YELLOW}$loss${NC}"
}

# Detect network interface
detect_interface

echo -e "\n${BLUE}======================================================${NC}"
echo -e "${BLUE}TRAFFIC CONTROL MONITOR${NC}"
echo -e "${BLUE}======================================================${NC}"
echo -e "Monitoring interface: ${CYAN}$INTERFACE${NC}"
echo -e "Update interval: ${CYAN}$INTERVAL seconds${NC}"
echo -e "Press ${RED}Ctrl+C${NC} to stop monitoring."
echo -e "${BLUE}======================================================${NC}"

# Store previous output to detect changes
previous_output=""

# Main monitoring loop
while true; do
    # Get current tc output
    current_output=$(tc qdisc show dev $INTERFACE)
    
    # Only show if there's a change or this is the first run
    if [[ "$current_output" != "$previous_output" || -z "$previous_output" ]]; then
        show_conditions
        previous_output="$current_output"
    fi
    
    # Wait for the specified interval
    sleep $INTERVAL
done