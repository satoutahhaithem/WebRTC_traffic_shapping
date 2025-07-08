#!/bin/bash
#
# Manual Traffic Control Script for WebRTC Streaming
#
# This script provides a menu to manually apply specific network conditions,
# allowing for controlled Quality of Service (QoS) testing.
#
# Usage: sudo ./manual_tc_control.sh
#
# Author: Roo AI Assistant
# Date: May 2025

# Define color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

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

# Function to apply network conditions
apply_conditions() {
    local preset="$1"
    local rate="$2"
    lgive me ocal delay="$3"
    local loss="$4"
    
    echo -e "\n${BLUE}======================================================${NC}"
    echo -e "${BLUE}APPLYING NETWORK CONDITIONS: ${CYAN}$preset${NC}"
    echo -e "${BLUE}======================================================${NC}"
    echo -e "Rate: ${CYAN}$rate${NC}, Delay: ${CYAN}$delay${NC}, Loss: ${CYAN}$loss${NC}"
    
    # Reset first to ensure a clean state
    sudo tc qdisc del dev $INTERFACE root 2>/dev/null
    
    # Add new netem configuration
    sudo tc qdisc add dev $INTERFACE root netem rate $rate delay $delay loss $loss
    
    echo -e "${GREEN}Network conditions applied successfully.${NC}"
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

# Function to display the menu
show_menu() {
    echo -e "\n${PURPLE}--- QoS Measurement Menu ---${NC}"
    echo "Select a network condition to test:"
    echo -e "  1) ${CYAN}Excellent${NC} (10mbit, 20ms delay, 0% loss)"
    echo -e "  2) ${CYAN}Good${NC}      (6mbit, 40ms delay, 0.5% loss)"
    echo -e "  3) ${CYAN}Fair${NC}      (4mbit, 80ms delay, 1% loss)"
    echo -e "  4) ${CYAN}Poor${NC}      (2mbit, 150ms delay, 3% loss)"
    echo -e "  5) ${CYAN}Very Poor${NC} (1mbit, 300ms delay, 5% loss)"
    echo -e "  6) ${GREEN}Stable / Ultra${NC} (Same as the stable script)"
    echo -e "  7) ${YELLOW}Reset${NC}     (Remove all network shaping)"
    echo -e "  8) ${RED}Exit${NC}"
    echo -e "${PURPLE}--------------------------${NC}"
}

# --- Main Script ---

# Check if running as root
if [[ $EUID -ne 0 ]]; then
    echo -e "${RED}This script requires root privileges. Please run with sudo.${NC}"
    exit 1
fi

detect_interface
reset_conditions # Start with a clean slate

while true; do
    show_menu
    read -p "Enter your choice [1-8]: " choice

    case $choice in
        1) apply_conditions "Excellent" "10mbit" "20ms" "0%" ;;
        2) apply_conditions "Good" "6mbit" "40ms" "0.5%" ;;
        3) apply_conditions "Fair" "4mbit" "80ms" "1%" ;;
        4) apply_conditions "Poor" "2mbit" "150ms" "3%" ;;
        5) apply_conditions "Very Poor" "1mbit" "300ms" "5%" ;;
        6) . ./set_stable_tc.sh ;; # Source the stable script
        7) reset_conditions ;;
        8) echo -e "${YELLOW}Exiting.${NC}"; reset_conditions; break ;;
        *) echo -e "${RED}Invalid choice. Please try again.${NC}" ;;
    esac

    echo -e "\n${YELLOW}The selected network condition is now active.${NC}"
    echo -e "${YELLOW}You can now run the sender/receiver scripts to measure QoS.${NC}"
    read -p "Press [Enter] to return to the menu..."
done