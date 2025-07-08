#!/bin/bash
#
# Traffic Control Script for Video Streaming
#
# This script uses Linux's tc (Traffic Control) to simulate different network conditions.
# It can limit bandwidth, add delay, and introduce packet loss to test video streaming
# under various network conditions.
#
# Usage: sudo ./webrtc_tc_control.sh
#
# Author: Roo AI Assistant
# Date: May 2025

# Set the network interface (change this to match your system)
INTERFACE="wlp0s20f3"  # network interface (e.g., eth0, wlan0, etc.)

# Function to show the current network performance stats
show_stats() {
    echo "Monitoring network statistics for $INTERFACE"
    echo "----------------------------------------------"
    # Show the interface statistics: packets, bytes, and errors
    netstat -i | grep $INTERFACE
    
    # Show tc qdisc statistics (e.g., packet loss, delay, etc.)
    echo "Current TC settings:"
    tc -s qdisc show dev $INTERFACE
    
    # Check if netem is configured and show details
    if tc qdisc show dev $INTERFACE | grep -q "netem"; then
        echo ""
        echo "Network emulation is ACTIVE with the following parameters:"
        tc qdisc show dev $INTERFACE | grep -i "rate\|delay\|loss" | sed 's/^/    /'
    else
        echo ""
        echo "Network emulation is NOT ACTIVE. Use option 1 to set network conditions."
    fi
}

# Function to apply network conditions
apply_conditions() {
    local rate="$1"     # Bandwidth rate (e.g., "1mbit")
    local delay="$2"    # Latency delay (e.g., "100ms")
    local loss="$3"     # Packet loss (e.g., "10%")

    echo "Applying network conditions: Rate=$rate, Delay=$delay, Loss=$loss"

    # First, ensure the qdisc is added to the interface if it doesn't exist yet
    if ! tc qdisc show dev $INTERFACE | grep -q "netem"; then
        # Add the root qdisc for network emulation if not already added
        sudo tc qdisc add dev $INTERFACE root netem
    fi

    # Apply the new network conditions using tc
    sudo tc qdisc change dev $INTERFACE root netem rate $rate delay $delay loss $loss
    
    echo "Network conditions applied successfully."
}

# Function to reset network conditions (remove tc configuration)
reset_conditions() {
    echo "Resetting network conditions."
    sudo tc qdisc del dev $INTERFACE root
    echo "Network conditions reset successfully."
}

# Interactive menu for traffic control
menu() {
    echo "----------------------------"
    echo "Traffic Control (TC) Menu"
    echo "----------------------------"
    echo "1. Set custom network conditions"
    echo "2. Apply preset network conditions"
    echo "3. Show current network stats"
    echo "4. Reset network conditions"
    echo "5. Exit"
    echo "----------------------------"
    read -p "Select an option (1-5): " option

    case $option in
        1)
            # Set custom network conditions
            read -p "Enter the rate (e.g., '1mbit'): " rate
            read -p "Enter the delay (e.g., '100ms'): " delay
            read -p "Enter the loss (e.g., '10%'): " loss
            apply_conditions "$rate" "$delay" "$loss"
            ;;
        2)
            # Apply preset network conditions
            echo "Select a preset network condition:"
            echo "1. Excellent (10mbit, 20ms, 0%)"
            echo "2. Good (6mbit, 40ms, 0.5%)"
            echo "3. Fair (4mbit, 80ms, 1%)"
            echo "4. Poor (2mbit, 150ms, 3%)"
            echo "5. Very Poor (1mbit, 300ms, 5%)"
            read -p "Select a preset (1-5): " preset
            
            case $preset in
                1) apply_conditions "10mbit" "20ms" "0%" ;;
                2) apply_conditions "6mbit" "40ms" "0.5%" ;;
                3) apply_conditions "4mbit" "80ms" "1%" ;;
                4) apply_conditions "2mbit" "150ms" "3%" ;;
                5) apply_conditions "1mbit" "300ms" "5%" ;;
                *) echo "Invalid preset selection." ;;
            esac
            ;;
        3)
            # Show current stats
            show_stats
            ;;
        4)
            # Reset network conditions
            reset_conditions
            ;;
        5)
            echo "Exiting the script."
            exit 0
            ;;
        *)
            echo "Invalid option. Please select again."
            ;;
    esac
}

# Check if running as root (needed for tc commands)
if [ "$EUID" -ne 0 ]; then
    echo "This script requires root privileges to modify network settings."
    echo "Please run with sudo: sudo $0"
    exit 1
fi

# Check if tc is installed
if ! command -v tc &> /dev/null; then
    echo "Error: tc (traffic control) is not installed."
    echo "Please install it with: sudo apt install iproute2"
    exit 1
fi

# Detect network interface if not set
if [ "$INTERFACE" = "wlp0s20f3" ]; then
    # Try to detect the default interface
    DEFAULT_INTERFACE=$(ip route | grep default | awk '{print $5}' | head -n 1)
    if [ -n "$DEFAULT_INTERFACE" ]; then
        echo "Detected default interface: $DEFAULT_INTERFACE"
        echo "Do you want to use this interface? (y/n)"
        read -p "> " use_default
        if [ "$use_default" = "y" ] || [ "$use_default" = "Y" ]; then
            INTERFACE=$DEFAULT_INTERFACE
        else
            echo "Available interfaces:"
            ip -o link show | awk -F': ' '{print $2}'
            read -p "Enter the interface name to use: " INTERFACE
        fi
    fi
fi

echo "Using network interface: $INTERFACE"
echo ""

# Main loop for traffic control
while true; do
    menu
    echo ""
done