#!/usr/bin/env python3
"""
Traffic Control All-in-One Script

This script combines traffic control (like auto_tc_control.sh) and performance
measurement (like tc_performance_comparison.py) in a single file. It applies
network conditions and measures their impact, all from the receiver PC.

Usage:
    sudo python tc_all_in_one.py [--sender-ip SENDER_IP] [--receiver-ip RECEIVER_IP]
                                [--interval INTERVAL] [--duration DURATION]
                                [--output OUTPUT_DIR]

Author: Roo AI Assistant
Date: May 2025
"""

import argparse
import time
import json
import os
import subprocess
import requests
import numpy as np
import threading
from datetime import datetime

# Import matplotlib with error handling
try:
    import matplotlib.pyplot as plt
except ImportError:
    print("Error: matplotlib is not installed. Please install it with:")
    print("pip install matplotlib")
    exit(1)

# Default settings
DEFAULT_SENDER_IP = "localhost"
DEFAULT_RECEIVER_IP = "192.168.2.169"
DEFAULT_SENDER_PORT = 8000
DEFAULT_RECEIVER_PORT = 8001
DEFAULT_INTERVAL = 10.0  # seconds
DEFAULT_DURATION = 120  # seconds (2 minutes)
DEFAULT_OUTPUT_DIR = "./tc_performance_graphs"
DEFAULT_CYCLE_DURATION = 20  # seconds per network condition

# Global variables
running = True
data = {
    "timestamps": [],
    "commanded": {
        "rate": [],      # Mbps
        "delay": [],     # ms
        "loss": []       # %
    },
    "measured": {
        "bandwidth": [],  # MB/s (will convert to Mbps)
        "latency": [],    # ms
        "loss_rate": []   # %
    }
}
current_condition = {
    "name": "NONE",
    "rate": 0,
    "delay": 0,
    "loss": 0
}

# ANSI color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

# Define the network condition presets
NETWORK_PRESETS = [
    {"name": "VERY POOR", "rate": 1, "delay": 300, "loss": 5},
    {"name": "POOR", "rate": 2, "delay": 150, "loss": 3},
    {"name": "FAIR", "rate": 4, "delay": 80, "loss": 1},
    {"name": "GOOD", "rate": 6, "delay": 40, "loss": 0.5},
    {"name": "EXCELLENT", "rate": 10, "delay": 20, "loss": 0},
    {"name": "ULTRA", "rate": 50, "delay": 1, "loss": 0}
]

# Function to detect the default network interface
def detect_interface():
    try:
        # Try to get the default interface used for internet access
        result = subprocess.run(["ip", "route", "get", "8.8.8.8"], 
                               capture_output=True, text=True, check=True)
        interface = result.stdout.split()[4]
        print(f"{Colors.GREEN}Detected default interface: {interface}{Colors.ENDC}")
        return interface
    except Exception as e:
        print(f"{Colors.YELLOW}Could not detect default interface automatically: {e}{Colors.ENDC}")
        print("Available interfaces:")
        try:
            result = subprocess.run(["ip", "-o", "link", "show"], 
                                   capture_output=True, text=True, check=True)
            for line in result.stdout.splitlines():
                if "lo:" not in line:  # Skip loopback
                    interface_name = line.split(": ")[1]
                    print(f"  {interface_name}")
        except Exception:
            print(f"{Colors.RED}Could not list interfaces{Colors.ENDC}")
        
        # Ask user to select an interface
        interface = input("Enter interface name: ")
        
        if not interface:
            print(f"{Colors.RED}No interface selected. Exiting.{Colors.ENDC}")
            exit(1)
        
        print(f"{Colors.GREEN}Using interface: {interface}{Colors.ENDC}")
        return interface

# Function to apply network conditions
def apply_conditions(interface, preset):
    global current_condition
    
    name = preset["name"]
    rate = preset["rate"]
    delay = preset["delay"]
    loss = preset["loss"]
    
    print(f"\n{Colors.BLUE}======================================================{Colors.ENDC}")
    print(f"{Colors.BLUE}APPLYING NETWORK CONDITIONS: {Colors.CYAN}{name}{Colors.ENDC}")
    print(f"{Colors.BLUE}======================================================{Colors.ENDC}")
    print(f"Rate: {Colors.CYAN}{rate} Mbps{Colors.ENDC}")
    print(f"Delay: {Colors.CYAN}{delay} ms{Colors.ENDC}")
    print(f"Loss: {Colors.CYAN}{loss}%{Colors.ENDC}")
    
    try:
        # Check if netem is already configured
        result = subprocess.run(["tc", "qdisc", "show", "dev", interface], 
                               capture_output=True, text=True, check=True)
        
        if "netem" in result.stdout:
            # Change existing netem configuration
            subprocess.run(["tc", "qdisc", "change", "dev", interface, "root", "netem", 
                           "rate", f"{rate}mbit", "delay", f"{delay}ms", "loss", f"{loss}%"], 
                          check=True)
        else:
            # Add new netem configuration
            subprocess.run(["tc", "qdisc", "add", "dev", interface, "root", "netem", 
                           "rate", f"{rate}mbit", "delay", f"{delay}ms", "loss", f"{loss}%"], 
                          check=True)
        
        # Update current condition
        current_condition = {
            "name": name,
            "rate": rate,
            "delay": delay,
            "loss": loss
        }
        
        print(f"{Colors.GREEN}Network conditions applied successfully.{Colors.ENDC}")
    except Exception as e:
        print(f"{Colors.RED}Error applying network conditions: {e}{Colors.ENDC}")

# Function to apply ultra-low-latency conditions
def apply_ultra_conditions(interface):
    global current_condition
    
    print(f"\n{Colors.BLUE}======================================================{Colors.ENDC}")
    print(f"{Colors.BLUE}APPLYING NETWORK CONDITIONS: {Colors.CYAN}ULTRA-LOW-LATENCY{Colors.ENDC}")
    print(f"{Colors.BLUE}======================================================{Colors.ENDC}")
    
    try:
        # Reset any existing traffic control settings
        subprocess.run(["tc", "qdisc", "del", "dev", interface, "root"], 
                      stderr=subprocess.DEVNULL, check=False)
        
        # Create a hierarchical token bucket (HTB) qdisc as the root
        subprocess.run(["tc", "qdisc", "add", "dev", interface, "root", "handle", "1:", "htb", "default", "10"], 
                      check=True)
        
        # Add a class with high bandwidth (50mbit)
        subprocess.run(["tc", "class", "add", "dev", interface, "parent", "1:", "classid", "1:10", "htb", 
                       "rate", "50mbit", "ceil", "50mbit", "burst", "15k"], 
                      check=True)
        
        # Add minimal network emulation parameters
        subprocess.run(["tc", "qdisc", "add", "dev", interface, "parent", "1:10", "handle", "10:", "netem",
                       "delay", "1ms", "0.5ms", "distribution", "normal",
                       "loss", "0%", "corrupt", "0%", "reorder", "0%", "duplicate", "0%"], 
                      check=True)
        
        # Add SFQ (Stochastic Fairness Queueing) for better packet scheduling
        subprocess.run(["tc", "qdisc", "add", "dev", interface, "parent", "10:", "handle", "100:", "sfq", "perturb", "10"], 
                      check=True)
        
        # Add filter to prioritize video traffic (common video streaming ports)
        subprocess.run(["tc", "filter", "add", "dev", interface, "parent", "1:", "protocol", "ip", "prio", "1", "u32",
                       "match", "ip", "dport", "9999", "0xffff", "flowid", "1:10"], 
                      check=True)
        
        # Update current condition
        current_condition = {
            "name": "ULTRA",
            "rate": 50,
            "delay": 1,
            "loss": 0
        }
        
        print(f"{Colors.GREEN}ULTRA-LOW-LATENCY conditions applied successfully!{Colors.ENDC}")
    except Exception as e:
        print(f"{Colors.RED}Error applying ULTRA conditions: {e}{Colors.ENDC}")

# Function to reset network conditions
def reset_conditions(interface):
    global current_condition
    
    print(f"\n{Colors.BLUE}======================================================{Colors.ENDC}")
    print(f"{Colors.BLUE}RESETTING NETWORK CONDITIONS{Colors.ENDC}")
    print(f"{Colors.BLUE}======================================================{Colors.ENDC}")
    
    try:
        subprocess.run(["tc", "qdisc", "del", "dev", interface, "root"], 
                      stderr=subprocess.DEVNULL, check=False)
        
        # Update current condition
        current_condition = {
            "name": "NONE",
            "rate": 0,
            "delay": 0,
            "loss": 0
        }
        
        print(f"{Colors.GREEN}Network conditions reset successfully.{Colors.ENDC}")
    except Exception as e:
        print(f"{Colors.RED}Error resetting network conditions: {e}{Colors.ENDC}")

# Function to run the traffic control cycle in a separate thread
def run_tc_cycle(interface):
    global running
    
    print(f"\n{Colors.BLUE}======================================================{Colors.ENDC}")
    print(f"{Colors.BLUE}STARTING TRAFFIC CONTROL CYCLE{Colors.ENDC}")
    print(f"{Colors.BLUE}======================================================{Colors.ENDC}")
    print(f"This script will automatically cycle through different network conditions.")
    print(f"Each condition will be active for {Colors.YELLOW}{DEFAULT_CYCLE_DURATION} seconds{Colors.ENDC}.")
    
    # Start with a clean slate
    reset_conditions(interface)
    
    # Run the cycle until interrupted
    while running:
        for preset in NETWORK_PRESETS:
            if not running:
                break
                
            # Apply the conditions
            if preset["name"] == "ULTRA":
                apply_ultra_conditions(interface)
            else:
                apply_conditions(interface, preset)
            
            # Wait for the specified interval
            print(f"\n{Colors.YELLOW}Waiting for {DEFAULT_CYCLE_DURATION} seconds...{Colors.ENDC}")
            
            # Wait in small increments to check if we should stop
            for _ in range(int(DEFAULT_CYCLE_DURATION / 0.5)):
                if not running:
                    break
                time.sleep(0.5)
        
        if running:
            print(f"\n{Colors.GREEN}Completed one full cycle. Starting again...{Colors.ENDC}")

# Function to get metrics from the sender
def get_sender_metrics(sender_ip, sender_port):
    try:
        response = requests.get(f"http://{sender_ip}:{sender_port}/metrics", timeout=1)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"{Colors.RED}Error getting sender metrics: HTTP {response.status_code}{Colors.ENDC}")
            return None
    except Exception as e:
        print(f"{Colors.RED}Error connecting to sender metrics API: {e}{Colors.ENDC}")
        return None

# Function to get metrics from the receiver
def get_receiver_metrics(receiver_ip, receiver_port):
    try:
        response = requests.get(f"http://{receiver_ip}:{receiver_port}/metrics", timeout=1)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"{Colors.RED}Error getting receiver metrics: HTTP {response.status_code}{Colors.ENDC}")
            return None
    except Exception as e:
        print(f"{Colors.RED}Error connecting to receiver metrics API: {e}{Colors.ENDC}")
        return None

# Function to collect metrics
def collect_metrics(sender_ip, sender_port, receiver_ip, receiver_port, interval, duration):
    global running, data, current_condition
    
    start_time = time.time()
    count = 0
    
    print(f"{Colors.GREEN}Starting metrics collection for {duration} seconds...{Colors.ENDC}")
    print(f"{Colors.CYAN}Press Ctrl+C at any time to stop collection and generate graphs immediately{Colors.ENDC}")
    
    try:
        while running and (duration <= 0 or time.time() - start_time < duration):
            # Get current timestamp
            current_time = time.time() - start_time
            data["timestamps"].append(current_time)
            
            # Store commanded values from current_condition
            data["commanded"]["rate"].append(current_condition["rate"])
            data["commanded"]["delay"].append(current_condition["delay"])
            data["commanded"]["loss"].append(current_condition["loss"])
            
            # Get sender metrics
            sender_metrics = get_sender_metrics(sender_ip, sender_port)
            
            # Get receiver metrics
            receiver_metrics = get_receiver_metrics(receiver_ip, receiver_port)
            
            # Calculate measured values
            if sender_metrics and receiver_metrics:
                # Convert bandwidth from MB/s to Mbps (1 MB/s = 8 Mbps)
                bandwidth_mbps = sender_metrics.get("bandwidth_usage", 0) * 8
                
                # Get latency from frame delivery time
                latency_ms = receiver_metrics.get("frame_delivery_time", 0)
                
                # Get loss rate from frame drop rate
                loss_rate = receiver_metrics.get("frame_drop_rate", 0)
                
                # Store measured values
                data["measured"]["bandwidth"].append(bandwidth_mbps)
                data["measured"]["latency"].append(latency_ms)
                data["measured"]["loss_rate"].append(loss_rate)
            else:
                # Use previous values or 0 if no previous values
                data["measured"]["bandwidth"].append(data["measured"]["bandwidth"][-1] if data["measured"]["bandwidth"] else 0)
                data["measured"]["latency"].append(data["measured"]["latency"][-1] if data["measured"]["latency"] else 0)
                data["measured"]["loss_rate"].append(data["measured"]["loss_rate"][-1] if data["measured"]["loss_rate"] else 0)
            
            # Print current metrics every 5 seconds
            if count % 5 == 0:
                print(f"\n{Colors.BLUE}======================================================{Colors.ENDC}")
                print(f"{Colors.BLUE}TC PERFORMANCE COMPARISON - {time.strftime('%H:%M:%S')}{Colors.ENDC}")
                print(f"{Colors.BLUE}======================================================{Colors.ENDC}")
                
                print(f"{Colors.CYAN}Commanded Network Conditions: {current_condition['name']}{Colors.ENDC}")
                print(f"  Rate: {current_condition['rate']} Mbps")
                print(f"  Delay: {current_condition['delay']} ms")
                print(f"  Loss: {current_condition['loss']}%")
                
                print(f"\n{Colors.CYAN}Measured Performance:{Colors.ENDC}")
                if sender_metrics and receiver_metrics:
                    print(f"  Bandwidth: {bandwidth_mbps:.2f} Mbps")
                    print(f"  Latency: {latency_ms:.2f} ms")
                    print(f"  Loss Rate: {loss_rate:.2f}%")
                else:
                    print(f"  {Colors.YELLOW}Could not get complete metrics{Colors.ENDC}")
            
            # Wait for the next interval
            time.sleep(interval)
            count += 1
    
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Metrics collection stopped by user{Colors.ENDC}")
    
    except Exception as e:
        print(f"\n{Colors.RED}Error collecting metrics: {e}{Colors.ENDC}")
    
    finally:
        print(f"\n{Colors.GREEN}Collected {len(data['timestamps'])} data points over {data['timestamps'][-1]:.1f} seconds{Colors.ENDC}")

# Function to generate graphs
def generate_graphs(output_dir):
    global data
    
    print(f"{Colors.GREEN}Generating performance comparison graphs...{Colors.ENDC}")
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate timestamp for filenames
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Create a single figure with all three metrics
    plt.figure(figsize=(12, 10))
    
    # Plot all three metrics in one figure
    plt.subplot(3, 1, 1)
    plt.title("Bandwidth Comparison")
    plt.plot(data["timestamps"], data["commanded"]["rate"], 'b-', label="Commanded")
    plt.plot(data["timestamps"], data["measured"]["bandwidth"], 'r-', label="Measured")
    plt.ylabel("Mbps")
    plt.grid(True)
    plt.legend()
    
    plt.subplot(3, 1, 2)
    plt.title("Latency Comparison")
    plt.plot(data["timestamps"], data["commanded"]["delay"], 'b-', label="Commanded")
    plt.plot(data["timestamps"], data["measured"]["latency"], 'r-', label="Measured")
    plt.ylabel("ms")
    plt.grid(True)
    plt.legend()
    
    plt.subplot(3, 1, 3)
    plt.title("Packet Loss Comparison")
    plt.plot(data["timestamps"], data["commanded"]["loss"], 'b-', label="Commanded")
    plt.plot(data["timestamps"], data["measured"]["loss_rate"], 'r-', label="Measured")
    plt.xlabel("Time (seconds)")
    plt.ylabel("%")
    plt.grid(True)
    plt.legend()
    
    plt.tight_layout()
    
    # Save the figure
    output_file = os.path.join(output_dir, f"tc_performance_{timestamp}.png")
    plt.savefig(output_file, dpi=150)
    print(f"{Colors.GREEN}Saved performance graph to: {output_file}{Colors.ENDC}")
    
    # Save raw data as JSON for later analysis
    data_file = os.path.join(output_dir, f"tc_data_{timestamp}.json")
    with open(data_file, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"{Colors.GREEN}Saved raw data to: {data_file}{Colors.ENDC}")
    
    # Show the graph directly
    print(f"{Colors.GREEN}Displaying graph...{Colors.ENDC}")
    plt.show()
    
    return output_file

# Main function
def main():
    global running
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Traffic Control All-in-One Script")
    parser.add_argument("--sender-ip", default=DEFAULT_SENDER_IP, help="Sender IP address")
    parser.add_argument("--receiver-ip", default=DEFAULT_RECEIVER_IP, help="Receiver IP address")
    parser.add_argument("--sender-port", type=int, default=DEFAULT_SENDER_PORT, help="Sender metrics port")
    parser.add_argument("--receiver-port", type=int, default=DEFAULT_RECEIVER_PORT, help="Receiver metrics port")
    parser.add_argument("--interval", type=float, default=DEFAULT_INTERVAL, help="Metrics collection interval in seconds")
    parser.add_argument("--duration", type=int, default=DEFAULT_DURATION, help="Total duration in seconds (0 for unlimited)")
    parser.add_argument("--output", default=DEFAULT_OUTPUT_DIR, help="Output directory for graphs")
    args = parser.parse_args()
    
    print(f"{Colors.HEADER}Traffic Control All-in-One Script{Colors.ENDC}")
    print(f"{Colors.HEADER}======================================{Colors.ENDC}")
    print(f"Sender: {args.sender_ip}:{args.sender_port}")
    print(f"Receiver: {args.receiver_ip}:{args.receiver_port}")
    print(f"Interval: {args.interval} seconds")
    print(f"Duration: {args.duration} seconds (0 = unlimited)")
    print(f"Output Directory: {args.output}")
    print(f"{Colors.HEADER}======================================{Colors.ENDC}")
    
    # Check if running as root
    if os.geteuid() != 0:
        print(f"{Colors.RED}This script requires root privileges to modify network settings.{Colors.ENDC}")
        print(f"{Colors.RED}Please run with sudo: sudo {sys.argv[0]}{Colors.ENDC}")
        exit(1)
    
    # Check if tc is installed
    try:
        subprocess.run(["tc", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    except:
        print(f"{Colors.RED}Error: tc (traffic control) is not installed.{Colors.ENDC}")
        print(f"{Colors.RED}Please install it with: sudo apt install iproute2{Colors.ENDC}")
        exit(1)
    
    # Detect network interface
    interface = detect_interface()
    
    # Check if we can access the metrics APIs
    print(f"\n{Colors.CYAN}Checking metrics APIs...{Colors.ENDC}")
    
    sender_metrics = get_sender_metrics(args.sender_ip, args.sender_port)
    if sender_metrics:
        print(f"{Colors.GREEN}Successfully connected to sender metrics API{Colors.ENDC}")
    else:
        print(f"{Colors.YELLOW}Warning: Could not connect to sender metrics API{Colors.ENDC}")
        print(f"{Colors.YELLOW}Make sure the sender is running with --metrics-port {args.sender_port}{Colors.ENDC}")
    
    receiver_metrics = get_receiver_metrics(args.receiver_ip, args.receiver_port)
    if receiver_metrics:
        print(f"{Colors.GREEN}Successfully connected to receiver metrics API{Colors.ENDC}")
    else:
        print(f"{Colors.YELLOW}Warning: Could not connect to receiver metrics API{Colors.ENDC}")
        print(f"{Colors.YELLOW}Make sure the receiver is running with --metrics-port {args.receiver_port}{Colors.ENDC}")
    
    # Start traffic control thread
    tc_thread = threading.Thread(target=run_tc_cycle, args=(interface,))
    tc_thread.daemon = True
    tc_thread.start()
    
    # Trap Ctrl+C to reset conditions before exiting
    try:
        # Start metrics collection
        print(f"\n{Colors.CYAN}Starting metrics collection...{Colors.ENDC}")
        collect_metrics(args.sender_ip, args.sender_port, args.receiver_ip, args.receiver_port, args.interval, args.duration)
        
        # Generate graphs
        if len(data["timestamps"]) > 0:
            output_file = generate_graphs(args.output)
            print(f"\n{Colors.GREEN}Analysis complete!{Colors.ENDC}")
            print(f"{Colors.GREEN}Graphs have been saved in the '{args.output}' directory{Colors.ENDC}")
        else:
            print(f"\n{Colors.RED}No data collected. Cannot generate graphs.{Colors.ENDC}")
    
    finally:
        # Stop the traffic control thread
        running = False
        if tc_thread.is_alive():
            tc_thread.join(timeout=1.0)
        
        # Reset network conditions
        reset_conditions(interface)
        print(f"{Colors.GREEN}Network conditions have been reset.{Colors.ENDC}")

if __name__ == "__main__":
    try:
        import sys
        main()
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Program interrupted by user{Colors.ENDC}")
    except Exception as e:
        print(f"\n{Colors.RED}Error: {e}{Colors.ENDC}")