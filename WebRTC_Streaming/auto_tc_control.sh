#!/bin/bash
#
# Automatic Traffic Control Script for WebRTC Streaming
#
# This script automatically changes network conditions at regular intervals,
# cycling through different presets from poor to excellent.
#
# Usage: sudo ./auto_tc_control.sh
#
# Author: Roo AI Assistant
# Date: May 2025

# Set the network interface (change this to match your system)
INTERFACE=""  # Will be auto-detected

# Set the interval between condition changes (in seconds)
CHANGE_INTERVAL=20

# Define color codes for better readability
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
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

# Function to apply network conditions
apply_conditions() {
    local preset="$1"
    local rate="$2"
    local delay="$3"
    local loss="$4"
    
    echo -e "\n${BLUE}======================================================${NC}"
    echo -e "${BLUE}APPLYING NETWORK CONDITIONS: ${CYAN}$preset${NC}"
    echo -e "${BLUE}======================================================${NC}"
    echo -e "Rate: ${CYAN}$rate${NC}"
    echo -e "Delay: ${CYAN}$delay${NC}"
    echo -e "Loss: ${CYAN}$loss${NC}"
    
    # Check if netem is already configured
    if tc qdisc show dev $INTERFACE | grep -q "netem"; then
        # Change existing netem configuration
        sudo tc qdisc change dev $INTERFACE root netem rate $rate delay $delay loss $loss
    else
        # Add new netem configuration
        sudo tc qdisc add dev $INTERFACE root netem rate $rate delay $delay loss $loss
    fi
    
    echo -e "${GREEN}Network conditions applied successfully.${NC}"
    echo -e "${YELLOW}These conditions will be active for $CHANGE_INTERVAL seconds.${NC}"
    echo -e "${BLUE}======================================================${NC}"
}

# Function to apply ultra-low-latency conditions
apply_ultra_conditions() {
    echo -e "\n${BLUE}======================================================${NC}"
    echo -e "${BLUE}APPLYING NETWORK CONDITIONS: ${CYAN}ULTRA-LOW-LATENCY${NC}"
    echo -e "${BLUE}======================================================${NC}"
    
    # Reset any existing traffic control settings
    sudo tc qdisc del dev $INTERFACE root 2>/dev/null
    
    # Create a hierarchical token bucket (HTB) qdisc as the root
    sudo tc qdisc add dev $INTERFACE root handle 1: htb default 10
    
    # Add a class with high bandwidth (50mbit)
    sudo tc class add dev $INTERFACE parent 1: classid 1:10 htb rate 50mbit ceil 50mbit burst 15k
    
    # Add minimal network emulation parameters
    sudo tc qdisc add dev $INTERFACE parent 1:10 handle 10: netem \
        delay 1ms 0.5ms distribution normal \
        loss 0% \
        corrupt 0% \
        reorder 0% \
        duplicate 0%
    
    # Add SFQ (Stochastic Fairness Queueing) for better packet scheduling
    sudo tc qdisc add dev $INTERFACE parent 10: handle 100: sfq perturb 10
    
    # Add filter to prioritize video traffic (common video streaming ports)
    sudo tc filter add dev $INTERFACE parent 1: protocol ip prio 1 u32 \
        match ip dport 9999 0xffff flowid 1:10
    
    echo -e "${GREEN}ULTRA-LOW-LATENCY conditions applied successfully!${NC}"
    echo -e "${YELLOW}These conditions will be active for $CHANGE_INTERVAL seconds.${NC}"
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

# Function to show current network conditions
show_conditions() {
    echo -e "\n${BLUE}======================================================${NC}"
    echo -e "${BLUE}CURRENT NETWORK CONDITIONS${NC}"
    echo -e "${BLUE}======================================================${NC}"
    
    # Show the interface statistics
    echo -e "${CYAN}Interface Statistics:${NC}"
    netstat -i | grep $INTERFACE
    
    # Show tc qdisc statistics
    echo -e "\n${CYAN}Traffic Control Settings:${NC}"
    tc -s qdisc show dev $INTERFACE
    
    # Check if netem is configured and show details
    if tc qdisc show dev $INTERFACE | grep -q "netem"; then
        echo -e "\n${GREEN}Network emulation is ACTIVE with the following parameters:${NC}"
        tc qdisc show dev $INTERFACE | grep -i "rate\|delay\|loss" | sed "s/^/    /"
    else
        echo -e "\n${YELLOW}Network emulation is NOT ACTIVE.${NC}"
    fi
    
    echo -e "${BLUE}======================================================${NC}"
}

# Function to run the automatic cycle
run_auto_cycle() {
    # Define the presets in order from worst to best
    local presets=(
        "VERY POOR:1mbit:300ms:5%"
        "POOR:2mbit:150ms:3%"
        "FAIR:4mbit:80ms:1%"
        "GOOD:6mbit:40ms:0.5%"
        "EXCELLENT:10mbit:20ms:0%"
        "ULTRA:ultra:ultra:ultra"  # Special case for ultra conditions
    )
    
    echo -e "\n${BLUE}======================================================${NC}"
    echo -e "${BLUE}STARTING AUTOMATIC TRAFFIC CONTROL CYCLE${NC}"
    echo -e "${BLUE}======================================================${NC}"
    echo -e "This script will automatically cycle through different network conditions."
    echo -e "Each condition will be active for ${YELLOW}$CHANGE_INTERVAL seconds${NC}."
    echo -e "Press ${RED}Ctrl+C${NC} at any time to stop and reset conditions."
    echo -e "${BLUE}======================================================${NC}"
    
    # Trap Ctrl+C to reset conditions before exiting
    trap 'echo -e "\n${YELLOW}Stopping automatic cycle...${NC}"; reset_conditions; exit 0' INT
    
    # Start with a clean slate
    reset_conditions
    
    # Run the cycle until interrupted
    while true; do
        for preset_info in "${presets[@]}"; do
            # Parse preset info
            IFS=':' read -r preset_name rate delay loss <<< "$preset_info"
            
            # Apply the conditions
            if [[ "$preset_name" == "ULTRA" ]]; then
                apply_ultra_conditions
            else
                apply_conditions "$preset_name" "$rate" "$delay" "$loss"
            fi
            
            # Show current conditions
            show_conditions
            
            # Wait for the specified interval
            echo -e "\n${YELLOW}Waiting for $CHANGE_INTERVAL seconds...${NC}"
            sleep $CHANGE_INTERVAL
        done
        
        echo -e "\n${GREEN}Completed one full cycle. Starting again...${NC}"
    done
}

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

# Detect network interface
detect_interface

# Start the automatic cycle
run_auto_cycle