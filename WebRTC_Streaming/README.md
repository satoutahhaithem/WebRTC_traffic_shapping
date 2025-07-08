# Video Streaming with Traffic Control

## Quick Start - Just Run These Scripts!

We've created simple scripts that start everything for you:

### First, install required dependencies:

#### Option 1: Using apt (System-wide installation)

```bash
# On both sender and receiver PCs:
sudo apt install python3-opencv python3-numpy python3-requests

# On receiver PC only (for graphs):
sudo apt install python3-matplotlib
```

#### Option 2: Using pip in a virtual environment (Recommended)

We've created a setup script that handles everything for you:

```bash
# Run the setup script
./setup_venv.sh

# Activate the virtual environment
source venv/bin/activate
```

Or manually:

```bash
# Create a virtual environment
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

After installing dependencies, make sure to activate the virtual environment before running the scripts:

```bash
source venv/bin/activate
```

### Then run the scripts:

#### On the sender PC:
```bash
# Note: sudo doesn't preserve the virtual environment by default
sudo -E env "PATH=$PATH" ./start_sender.sh RECEIVER_IP
```
Replace RECEIVER_IP with the receiver's IP address.

#### On the receiver PC:
```bash
./start_receiver.sh SENDER_IP
```
Replace SENDER_IP with the sender's IP address.

> **Important Note about sudo**: When using `sudo`, the virtual environment is not preserved by default. The `sudo -E env "PATH=$PATH"` command preserves the environment variables, including the virtual environment.

The scripts will:
1. Check for required dependencies
2. Start all necessary components
3. Apply traffic control on the sender
4. Send settings to the receiver in real-time
5. Measure performance and generate graphs
6. Clean up everything when you press Ctrl+C

## How to Run a Stable, High-Performance Stream

If your goal is not to test different network conditions but to have the most stable, high-quality stream possible, you should use the `start_stable_sender.sh` script. This script applies an optimized, low-latency network configuration and starts the sender.

### On the Sender PC:
```bash
# This single command applies stable network settings and starts the sender.
sudo -E env "PATH=$PATH" ./start_stable_sender.sh RECEIVER_IP
```
Replace `RECEIVER_IP` with the receiver's IP address.

### On the Receiver PC:
The receiver setup is the same as the quick start.
```bash
./start_receiver.sh SENDER_IP
```
Replace `SENDER_IP` with the sender's IP address.

This setup is ideal for demonstrations or when you simply want the best possible video quality without manually managing network conditions.

## Manual Setup Options

If you prefer to run the commands manually:

### Option 1: Real-time Synchronization (Recommended)

1. **On the receiver PC**:
   ```bash
   # Terminal 1: Start the receiver
   python direct_receiver.py --display --metrics-port 8001
   
   # Terminal 2: Start the settings receiver
   python tc_settings_receiver.py
   
   # Terminal 3: Start performance measurement
   sudo python tc_performance_sync.py --sender-ip SENDER_IP --receiver-ip localhost
   ```

2. **On the sender PC**:
   ```bash
   # Terminal 1: Start traffic control with synchronization
   sudo ./auto_tc_control_sync.sh RECEIVER_IP
   
   # Terminal 2: Start the sender
   python direct_sender.py --ip RECEIVER_IP --video ../video/zidane.mp4 --metrics-port 8000
   ```

### Option 2: All-in-One on Receiver (Simplest)

```bash
# On receiver PC:
python direct_receiver.py --display --metrics-port 8001
sudo python tc_all_in_one.py --sender-ip SENDER_IP --receiver-ip localhost

# On sender PC:
python direct_sender.py --ip RECEIVER_IP --video ../video/zidane.mp4 --metrics-port 8000
```

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running the System

### On Receiver PC:
```bash
python direct_receiver.py --display --metrics-port 8001
```

### On Sender PC:
Run these in separate terminals:

```bash
# Terminal 1: Start traffic control
sudo ./auto_tc_control.sh

# Terminal 2: Start the sender
python direct_sender.py --ip RECEIVER_IP --video ../video/zidane.mp4 --metrics-port 8000
```
Replace RECEIVER_IP with the receiver's IP address.

## Performance Measurement Solutions

This system offers two different solutions for measuring and visualizing the performance of traffic control:

## IMPORTANT: Choose ONE of the following solutions - do NOT use both at the same time!

### Solution 1: Traffic Shaping on Sender, Measurement on Receiver (Hardcoded Cycle)

This approach keeps traffic control and performance measurement separate, but uses hardcoded knowledge of the traffic control cycle:

1. **On the Sender PC**: Run auto_tc_control.sh to apply traffic control
2. **On the Receiver PC**: Run tc_performance_manual.py to measure and plot

```bash
# On the sender PC
sudo ./auto_tc_control.sh

# On the receiver PC
sudo python tc_performance_manual.py --sender-ip SENDER_IP --receiver-ip localhost
```

This script has the auto_tc_control.sh cycle built-in, so it knows what the commanded values should be without having to detect them.

### Solution 2: Traffic Shaping and Measurement on Receiver

This approach combines traffic control and performance measurement in a single script that runs entirely on the receiver PC:

```bash
# On the receiver PC only
sudo python tc_all_in_one.py --sender-ip SENDER_IP --receiver-ip localhost
```

This script:
1. Applies traffic control directly on the receiver PC
2. Cycles through the same network conditions as auto_tc_control.sh
3. Measures the performance and plots the graphs
4. Resets the network conditions when done

### Solution 3: Real-time Synchronization Between Sender and Receiver

This approach uses real-time communication to send the traffic control settings from the sender to the receiver:

1. **On the Receiver PC**: Start the settings receiver server
   ```bash
   # Terminal 1: Start the settings receiver
   python tc_settings_receiver.py
   ```

2. **On the Sender PC**: Run the modified traffic control script that sends settings to the receiver
   ```bash
   # Terminal 1: Start traffic control with synchronization
   sudo ./auto_tc_control_sync.sh RECEIVER_IP
   ```
   Replace RECEIVER_IP with the actual IP address of the receiver.

3. **On the Receiver PC**: Run the performance measurement script
   ```bash
   # Terminal 2: Start performance measurement
   sudo python tc_performance_sync.py --sender-ip SENDER_IP --receiver-ip localhost
   ```
   Replace SENDER_IP with the actual IP address of the sender.

This solution:
1. Applies traffic control on the sender PC
2. Sends the current settings to the receiver PC in real-time
3. Measures the performance on the receiver PC
4. Plots graphs showing the actual commanded values from the sender

### Do NOT run traffic shaping on both PCs at the same time!

If you run auto_tc_control.sh on the sender PC AND tc_all_in_one.py on the receiver PC:
- Both PCs will be applying traffic control simultaneously
- This will create unpredictable network conditions
- The measurements will not match either set of commanded values
- The graphs will be meaningless

Choose either Solution 1, Solution 2, OR Solution 3, not multiple solutions at the same time.

### When to Do Traffic Shaping on the Receiver PC

You should use Solution 2 (tc_all_in_one.py) when:

1. **You want to control the network at the receiving end**:
   - This simulates bandwidth limitations, latency, and packet loss at the receiver
   - Useful when testing how a client handles poor network conditions

2. **You want a simpler setup with everything on one machine**:
   - No need to coordinate between two machines
   - Easier to start and stop the entire system

3. **You want to ensure perfect synchronization**:
   - The commanded values and measurements are taken on the same machine
   - This eliminates timing discrepancies between sender and receiver

4. **You want to plot graphs that accurately show both commanded and measured values**:
   - Since both traffic shaping and measurement happen on the same machine
   - The graphs will show perfect correlation between what was commanded and what was measured

### Comparing the Three Solutions

#### Solution 1: Traffic Shaping on Sender, Measurement on Receiver (Hardcoded Cycle)
- **Advantages**:
  - Simple setup with existing scripts
  - No additional server or communication needed
- **Disadvantages**:
  - Relies on hardcoded knowledge of the traffic control cycle
  - If you start the sender and receiver scripts at different times, the commanded values may be out of sync
  - If you modify the auto_tc_control.sh script, you must also update tc_performance_manual.py

#### Solution 2: Traffic Shaping and Measurement on Receiver
- **Advantages**:
  - Everything runs on one machine
  - Perfect synchronization between commanded and measured values
  - Simplest setup with just one script to run
- **Disadvantages**:
  - Traffic shaping happens on the receiver, not the sender
  - May not accurately represent real-world scenarios where network limitations are on the sender side

#### Solution 3: Real-time Synchronization Between Sender and Receiver
- **Advantages**:
  - Traffic shaping happens on the sender (more realistic)
  - Real-time communication of commanded values to the receiver
  - Accurate graphs even if you modify the traffic control settings or cycle
  - No need to keep hardcoded values in sync between scripts
- **Disadvantages**:
  - More complex setup with three scripts
  - Requires network communication between sender and receiver
  - Requires both machines to be accessible to each other

### When to Use Solution 3 (Real-time Synchronization)

Solution 3 is the best choice when:
1. You want the most accurate representation of commanded vs. measured values
2. You want to modify the traffic control cycle or settings without updating multiple scripts
3. You want to apply traffic control on the sender (more realistic) but measure on the receiver
4. You need to ensure the commanded values shown in graphs exactly match what was applied

### Step-by-Step Guide for Each Solution

#### Solution 1: Traffic Shaping on Sender, Measurement on Receiver (Hardcoded Cycle)

1. **Start the receiver**:
   ```bash
   # On the receiver PC
   python direct_receiver.py --display --metrics-port 8001
   ```

2. **Start traffic control on the sender**:
   ```bash
   # On the sender PC
   sudo ./auto_tc_control.sh
   ```

3. **Start the sender**:
   ```bash
   # On the sender PC
   python direct_sender.py --ip RECEIVER_IP --video ../video/zidane.mp4 --metrics-port 8000
   ```
   Replace RECEIVER_IP with the actual IP address of the receiver.

4. **Run the performance measurement script on the receiver**:
   ```bash
   # On the receiver PC
   sudo python tc_performance_manual.py --sender-ip SENDER_IP --receiver-ip localhost
   ```
   Replace SENDER_IP with the actual IP address of the sender.

#### Solution 2: Traffic Shaping and Measurement on Receiver

1. **Start the sender without traffic control**:
   ```bash
   # On the sender PC
   python direct_sender.py --ip RECEIVER_IP --video ../video/zidane.mp4 --metrics-port 8000
   ```

2. **Start the receiver**:
   ```bash
   # On the receiver PC
   python direct_receiver.py --display --metrics-port 8001
   ```

3. **Run the all-in-one script on the receiver**:
   ```bash
   # On the receiver PC
   sudo python tc_all_in_one.py --sender-ip SENDER_IP --receiver-ip localhost
   ```
   Replace SENDER_IP with the actual IP address of the sender.

#### Solution 3: Real-time Synchronization Between Sender and Receiver

1. **Start the receiver**:
   ```bash
   # On the receiver PC
   python direct_receiver.py --display --metrics-port 8001
   ```

2. **Start the settings receiver server on the receiver PC**:
   ```bash
   # On the receiver PC (Terminal 2)
   python tc_settings_receiver.py
   ```

3. **Start traffic control with synchronization on the sender PC**:
   ```bash
   # On the sender PC
   sudo ./auto_tc_control_sync.sh RECEIVER_IP
   ```
   Replace RECEIVER_IP with the actual IP address of the receiver.

4. **Start the sender**:
   ```bash
   # On the sender PC (Terminal 2)
   python direct_sender.py --ip RECEIVER_IP --video ../video/zidane.mp4 --metrics-port 8000
   ```
   Replace RECEIVER_IP with the actual IP address of the receiver.

5. **Run the synchronized performance measurement script on the receiver**:
   ```bash
   # On the receiver PC (Terminal 3)
   sudo python tc_performance_sync.py --sender-ip SENDER_IP --receiver-ip localhost
   ```
   Replace SENDER_IP with the actual IP address of the sender.

6. **Watch the results**:
   - The sender will apply traffic control settings and send them to the receiver
   - The receiver will collect performance metrics and display them in real-time
   - After 2 minutes (or when you press Ctrl+C), it will generate and display graphs
   - The graphs will show both commanded and measured values

## Troubleshooting

### Address already in use error

If you see this error when starting the receiver:
```
Error: [Errno 98] Address already in use
```

This means port 9999 (the default port) is already in use. You can:

1. **Find and kill the process using the port**:
   ```bash
   # Find the process using port 9999
   sudo lsof -i :9999
   
   # Kill the process (replace PID with the process ID from above)
   kill PID
   
   # Or force kill if needed
   kill -9 PID
   ```

2. **Use a different port**:
   ```bash
   # On the receiver
   python direct_receiver.py --display --metrics-port 8001 --port 9998
   
   # On the sender (use the same port)
   python direct_sender.py --ip RECEIVER_IP --video ../video/zidane.mp4 --metrics-port 8000 --port 9998
   ```

### Connection refused errors

If you see errors like:
```
Error connecting to sender metrics API: HTTPConnectionPool(host='192.168.2.120', port=8000): Max retries exceeded with url: /metrics (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x7afc20369eb0>: Failed to establish a new connection: [Errno 111] Connection refused'))
```

This means the script cannot connect to the metrics API. Check:

1. **Verify IP addresses are correct**:
   - Make sure you're using the correct IP address for the sender
   - On the sender, run `ip addr show` to confirm its IP address

2. **Ensure metrics ports are enabled**:
   - Confirm the sender is running with `--metrics-port 8000`
   - Confirm the receiver is running with `--metrics-port 8001`

3. **Check for firewall issues**:
   - Temporarily disable firewall to test: `sudo ufw disable` (Ubuntu)
   - Or add rules to allow the ports: `sudo ufw allow 8000/tcp` and `sudo ufw allow 8001/tcp`

4. **Run on the same machine for testing**:
   - For testing, you can run both sender and receiver on the same machine
   - Use `--sender-ip localhost` and `--receiver-ip localhost`

### No traffic control settings detected

If you see:
```
Warning: No traffic control settings detected
Make sure auto_tc_control.sh is running
```

This means the script cannot detect any traffic control settings. Check:

1. **Verify traffic control is running**:
   - Make sure you've started `auto_tc_control.sh` on the sender
   - Run it with sudo: `sudo ./auto_tc_control.sh`

2. **Check if traffic control is working**:
   - On the sender, run: `sudo tc qdisc show`
   - You should see output containing rate, delay, and loss settings

3. **Run traffic control manually**:
   - If auto_tc_control.sh isn't working, try manual settings:
   ```bash
   # Replace eth0 with your network interface
   sudo tc qdisc add dev eth0 root netem rate 5mbit delay 100ms loss 1%
   ```

4. **Find your network interface**:
   - Run: `ip route get 8.8.8.8`
   - Look for "dev XXX" in the output to identify your interface

### Reset Traffic Control

After stopping everything, reset traffic control:
```bash
sudo tc qdisc del dev INTERFACE root
```
Replace INTERFACE with your network interface (e.g., eth0, wlan0).