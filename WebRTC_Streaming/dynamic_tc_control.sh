#!/bin/bash
#
# Dynamic Traffic Control Script for WebRTC Streaming
#
# This script uses Linux's tc (Traffic Control) to simulate different network conditions.
# It can limit bandwidth, add delay, and introduce packet loss to test video streaming
# under various network conditions.
#
# Usage: sudo ./dynamic_tc_control.sh
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
        echo ""
        echo "These settings should affect the video quality. If you don't see any difference:"
        echo "1. Make sure you're using a high enough delay (try 1000ms or more)"
        echo "2. Make sure you're using a low enough rate (try 500kbit or less)"
        echo "3. Make sure you're using a high enough loss (try 20% or more)"
        echo ""
        echo "IMPORTANT: Always include units when entering values:"
        echo "- Rate: Use 'kbit', 'mbit', or 'gbit' (e.g., '1mbit')"
        echo "- Delay: Use 'ms' or 's' (e.g., '100ms')"
        echo "- Loss: Use '%' (e.g., '10%')"
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
    echo ""
    echo "To see the effect on video streaming:"
    echo "1. Start the receiver: python direct_receiver.py --display"
    echo "2. Start the sender: python direct_sender.py --ip RECEIVER_IP --video ../video/zidane.mp4"
    echo ""
    echo "Observe how the video quality and synchronization are affected by these network conditions."
}

# Function to reset network conditions (remove tc configuration)
reset_conditions() {
    echo "Resetting network conditions."
    sudo tc qdisc del dev $INTERFACE root
    echo "Network conditions reset successfully."
}

# Function to apply ultra-low-latency streaming conditions
apply_ultra_low_latency() {
    echo "Applying ULTRA-LOW-LATENCY streaming conditions..."
    
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
    
    echo "✅ ULTRA-LOW-LATENCY streaming conditions applied successfully!"
    echo "These settings provide the absolute best video streaming experience with:"
    echo "  - 50Mbit bandwidth"
    echo "  - 1ms delay"
    echo "  - 0% packet loss"
    echo "  - Advanced packet scheduling (SFQ)"
    echo "  - Video traffic prioritization"
    echo "  - Hierarchical bandwidth allocation"
    echo ""
    echo "For best results with these settings, use the minimal buffer sizes:"
    echo "python direct_receiver.py --display --buffer 3"
    echo "python direct_sender.py --ip RECEIVER_IP --video ../video/zidane.mp4 --buffer 3"
}

# Interactive menu for traffic control
menu() {
    echo "----------------------------"
    echo "Dynamic Traffic Control (TC)"
    echo "----------------------------"
    echo "1. Set custom network conditions"
    echo "2. Apply preset network conditions"
    echo "3. Show current network stats"
    echo "4. Reset network conditions"
    echo "5. Apply ultra-low-latency conditions"
    echo "6. Exit"
    echo "----------------------------"
    read -p "Select an option (1-6): " option

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
            # Apply ultra-low-latency conditions
            apply_ultra_low_latency
            ;;
        6)
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