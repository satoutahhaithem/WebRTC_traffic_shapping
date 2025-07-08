#!/usr/bin/env python3
"""
Traffic Control Performance Comparison

This script compares the controlled network conditions (set by auto_tc_control.sh)
with the actual performance measured at the receiver. It generates graphs showing
the relationship between what was commanded and what was actually applied.

Usage:
    python tc_performance_comparison.py [--sender-ip SENDER_IP] [--receiver-ip RECEIVER_IP]
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
DEFAULT_INTERVAL = 10.0  # seconds (changed from 1.0 to 10.0 as requested)
DEFAULT_DURATION = 120  # seconds (2 minutes)
DEFAULT_OUTPUT_DIR = "./tc_performance_graphs"

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

# Function to get current network conditions using tc
def get_network_conditions():
    try:
        # Get the default interface
        result = subprocess.run(["ip", "route", "get", "8.8.8.8"], 
                               capture_output=True, text=True, check=True)
        interface = result.stdout.split()[4]
        
        # Get current tc settings
        result = subprocess.run(["tc", "qdisc", "show", "dev", interface], 
                               capture_output=True, text=True, check=True)
        
        # Parse the output to extract metrics
        conditions = {
            "rate": "0",
            "delay": "0ms",
            "loss": "0%"
        }
        
        # Extract rate
        rate_match = result.stdout.find("rate ")
        if rate_match != -1:
            rate_end = result.stdout.find(" ", rate_match + 5)
            conditions["rate"] = result.stdout[rate_match + 5:rate_end]
        
        # Extract delay
        delay_match = result.stdout.find("delay ")
        if delay_match != -1:
            delay_end = result.stdout.find(" ", delay_match + 6)
            conditions["delay"] = result.stdout[delay_match + 6:delay_end]
        
        # Extract loss
        loss_match = result.stdout.find("loss ")
        if loss_match != -1:
            loss_end = result.stdout.find(" ", loss_match + 5)
            conditions["loss"] = result.stdout[loss_match + 5:loss_end]
        
        return conditions
    except Exception as e:
        print(f"{Colors.YELLOW}Error getting network conditions: {e}{Colors.ENDC}")
        return {"rate": "0", "delay": "0ms", "loss": "0%"}

# Function to convert rate string to Mbps
def convert_rate_to_mbps(rate_str):
    if "Kbit" in rate_str or "kbit" in rate_str:
        return float(rate_str.replace("Kbit", "").replace("kbit", "")) / 1000
    elif "Mbit" in rate_str or "mbit" in rate_str:
        return float(rate_str.replace("Mbit", "").replace("mbit", ""))
    elif "Gbit" in rate_str or "gbit" in rate_str:
        return float(rate_str.replace("Gbit", "").replace("gbit", "")) * 1000
    else:
        return 0

# Function to convert delay string to ms
def convert_delay_to_ms(delay_str):
    if "us" in delay_str:
        return float(delay_str.replace("us", "")) / 1000
    elif "ms" in delay_str:
        return float(delay_str.replace("ms", ""))
    elif "s" in delay_str:
        return float(delay_str.replace("s", "")) * 1000
    else:
        return 0

# Function to convert loss string to percentage
def convert_loss_to_percent(loss_str):
    return float(loss_str.replace("%", ""))

# Function to collect metrics
def collect_metrics(sender_ip, sender_port, receiver_ip, receiver_port, interval, duration):
    global running, data
    
    start_time = time.time()
    count = 0
    
    print(f"{Colors.GREEN}Starting metrics collection for {duration} seconds...{Colors.ENDC}")
    print(f"{Colors.CYAN}Press Ctrl+C at any time to stop collection and generate graphs immediately{Colors.ENDC}")
    
    try:
        while running and (duration <= 0 or time.time() - start_time < duration):
            # Get current timestamp
            current_time = time.time() - start_time
            data["timestamps"].append(current_time)
            
            # Get commanded network conditions (what was set by tc)
            network_conditions = get_network_conditions()
            
            # Convert to numeric values
            rate_mbps = convert_rate_to_mbps(network_conditions["rate"])
            delay_ms = convert_delay_to_ms(network_conditions["delay"])
            loss_percent = convert_loss_to_percent(network_conditions["loss"])
            
            # Store commanded values
            data["commanded"]["rate"].append(rate_mbps)
            data["commanded"]["delay"].append(delay_ms)
            data["commanded"]["loss"].append(loss_percent)
            
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
                
                print(f"{Colors.CYAN}Commanded Network Conditions:{Colors.ENDC}")
                print(f"  Rate: {network_conditions['rate']} ({rate_mbps:.2f} Mbps)")
                print(f"  Delay: {network_conditions['delay']} ({delay_ms:.2f} ms)")
                print(f"  Loss: {network_conditions['loss']} ({loss_percent:.2f}%)")
                
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
    parser = argparse.ArgumentParser(description="Traffic Control Performance Comparison")
    parser.add_argument("--sender-ip", default=DEFAULT_SENDER_IP, help="Sender IP address")
    parser.add_argument("--receiver-ip", default=DEFAULT_RECEIVER_IP, help="Receiver IP address")
    parser.add_argument("--sender-port", type=int, default=DEFAULT_SENDER_PORT, help="Sender metrics port")
    parser.add_argument("--receiver-port", type=int, default=DEFAULT_RECEIVER_PORT, help="Receiver metrics port")
    parser.add_argument("--interval", type=float, default=DEFAULT_INTERVAL, help="Metrics collection interval in seconds")
    parser.add_argument("--duration", type=int, default=DEFAULT_DURATION, help="Total duration in seconds (0 for unlimited)")
    parser.add_argument("--output", default=DEFAULT_OUTPUT_DIR, help="Output directory for graphs")
    args = parser.parse_args()
    
    print(f"{Colors.HEADER}Traffic Control Performance Comparison{Colors.ENDC}")
    print(f"{Colors.HEADER}======================================{Colors.ENDC}")
    print(f"Sender: {args.sender_ip}:{args.sender_port}")
    print(f"Receiver: {args.receiver_ip}:{args.receiver_port}")
    print(f"Interval: {args.interval} seconds")
    print(f"Duration: {args.duration} seconds (0 = unlimited)")
    print(f"Output Directory: {args.output}")
    print(f"{Colors.HEADER}======================================{Colors.ENDC}")
    
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
    
    # Check if we can access the tc command
    print(f"\n{Colors.CYAN}Checking traffic control access...{Colors.ENDC}")
    
    network_conditions = get_network_conditions()
    if network_conditions["rate"] != "0" or network_conditions["delay"] != "0ms" or network_conditions["loss"] != "0%":
        print(f"{Colors.GREEN}Successfully detected traffic control settings{Colors.ENDC}")
        print(f"  Rate: {network_conditions['rate']}")
        print(f"  Delay: {network_conditions['delay']}")
        print(f"  Loss: {network_conditions['loss']}")
    else:
        print(f"{Colors.YELLOW}Warning: No traffic control settings detected{Colors.ENDC}")
        print(f"{Colors.YELLOW}Make sure auto_tc_control.sh is running{Colors.ENDC}")
    
    # Start metrics collection
    print(f"\n{Colors.CYAN}Starting metrics collection...{Colors.ENDC}")
    
    # Start collection in the main thread
    collect_metrics(args.sender_ip, args.sender_port, args.receiver_ip, args.receiver_port, args.interval, args.duration)
    
    # Generate graphs
    if len(data["timestamps"]) > 0:
        output_file = generate_graphs(args.output)
        print(f"\n{Colors.GREEN}Analysis complete!{Colors.ENDC}")
        print(f"{Colors.GREEN}Graphs have been saved in the '{args.output}' directory{Colors.ENDC}")
    else:
        print(f"\n{Colors.RED}No data collected. Cannot generate graphs.{Colors.ENDC}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Program interrupted by user{Colors.ENDC}")
    except Exception as e:
        print(f"\n{Colors.RED}Error: {e}{Colors.ENDC}")