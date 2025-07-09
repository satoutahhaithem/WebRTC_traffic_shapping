#!/usr/bin/env python3
"""
Video Sender Script

This script captures video from a file and sends it to a receiver over a TCP socket.
It displays real-time traffic statistics in the terminal and shows the video locally.

Usage:
    python direct_sender.py --ip RECEIVER_IP --video VIDEO_PATH

Author: Roo AI Assistant
Date: May 2025
"""

import cv2
import socket
import pickle
import struct
import time
import argparse
import numpy as np
import threading
import http.server
import socketserver
import json
from collections import deque
from threading import Thread
from urllib.parse import urlparse, parse_qs

# Traffic statistics variables
bytes_sent = 0       # Total bytes sent
packets_sent = 0     # Total packets sent
frame_sizes = deque(maxlen=30)  # Last 30 frame sizes for averaging
frame_times = deque(maxlen=30)  # Last 30 frame processing times
start_time = time.time()        # When the script started

# Frame buffering for smoother transmission
frame_buffer = deque(maxlen=5)  # Buffer to store frames (minimal size for lowest latency)
buffer_lock = threading.Lock()   # Lock for thread-safe buffer access
send_thread = None               # Thread for sending frames
running = True                   # Flag to control threads

# API server for metrics
metrics_port = 8000  # Port for the metrics API server
metrics_server = None
metrics_handler = None

def print_stats():
    """
    Print current traffic statistics to the terminal.
    Clears the terminal and shows a formatted display of all metrics.
    """
    global bytes_sent, packets_sent, start_time, frame_sizes, frame_times, frame_buffer
    
    # Calculate elapsed time
    elapsed = time.time() - start_time
    
    # Calculate rates
    bytes_sent_rate = bytes_sent / elapsed if elapsed > 0 else 0
    packets_sent_rate = packets_sent / elapsed if elapsed > 0 else 0
    
    # Calculate averages
    avg_frame_size = sum(frame_sizes) / len(frame_sizes) if frame_sizes else 0
    avg_frame_time = sum(frame_times) / len(frame_times) if frame_times else 0
    fps = 1 / avg_frame_time if avg_frame_time > 0 else 0
    
    # Calculate buffer fullness
    buffer_percent = (len(frame_buffer) / frame_buffer.maxlen * 100) if frame_buffer.maxlen > 0 else 0
    
    # Clear terminal and print stats
    print("\033c", end="")  # Clear terminal
    
    print("\n" + "="*50)
    print("VIDEO SENDER - TRAFFIC MONITOR")
    print("="*50)
    print(f"Running time: {elapsed:.1f} seconds")
    print(f"Connected to: {receiver_ip}:{receiver_port}")
    print("\nTRAFFIC STATISTICS:")
    print(f"  Bytes sent:     {bytes_sent} bytes ({bytes_sent/1024/1024:.2f} MB)")
    print(f"  Packets sent:   {packets_sent}")
    print(f"  Send rate:      {bytes_sent_rate/1024/1024:.2f} MB/s")
    print(f"  Packet rate:    {packets_sent_rate:.1f} packets/s")
    print("\nVIDEO STATISTICS:")
    print(f"  Resolution:     {frame_width}x{frame_height}")
    print(f"  Avg frame size: {avg_frame_size/1024:.1f} KB")
    print(f"  Video FPS:      {video_fps:.1f}")
    print(f"  Target FPS:     {target_fps:.1f}")
    print(f"  Actual FPS:     {fps:.1f}")
    print(f"  Quality:        {jpeg_quality}%")
    print(f"  Buffer fullness: {len(frame_buffer)}/{frame_buffer.maxlen} ({buffer_percent:.1f}%)")
    print("="*50)

def send_frame(client_socket, frame, quality=90):
    """
    Compress and send a frame to the receiver
    
    Args:
        client_socket: Socket connected to the receiver
        frame: The video frame to send
        quality: JPEG compression quality (1-100)
        
    Returns:
        bool: True if successful, False otherwise
    """
    global bytes_sent, packets_sent, frame_sizes, frame_times
    
    # Record start time for performance measurement
    start_process = time.time()
    
    # Encode frame as JPEG (compress the image)
    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
    result, encoded_frame = cv2.imencode('.jpg', frame, encode_param)
    
    if not result:
        print("Error encoding frame")
        return False
    
    # Serialize frame for network transmission
    data = pickle.dumps(encoded_frame, protocol=4)
    
    # Get the size of the data
    size = len(data)
    frame_sizes.append(size)
    
    try:
        # Send the size of the data first (4 bytes)
        client_socket.sendall(struct.pack(">L", size))
        
        # Send the actual frame data
        client_socket.sendall(data)
        
        # Update traffic statistics
        bytes_sent += size + 4  # +4 for the size header
        packets_sent += 1
        
        # Calculate frame processing time
        frame_times.append(time.time() - start_process)
        
        return True
    
    except Exception as e:
        print(f"Error sending frame: {e}")
        return False

def send_frames_thread(client_socket, fps):
    """
    Thread function to continuously send frames from the buffer
    
    Args:
        client_socket: Socket connected to the receiver
        fps: Target frames per second
    """
    global frame_buffer, running
    
    # Calculate target frame time based on desired FPS
    target_frame_time = 1.0 / fps
    last_frame_time = time.time()
    
    while running:
        # Calculate time since last frame
        current_time = time.time()
        elapsed = current_time - last_frame_time
        
        # Only send a new frame if enough time has passed (control sending rate)
        if elapsed >= target_frame_time:
            # Get frame from buffer
            frame = None
            with buffer_lock:
                if frame_buffer:
                    frame = frame_buffer.popleft()
            
            if frame is not None:
                # Send the frame
                success = send_frame(client_socket, frame, jpeg_quality)
                
                if not success:
                    # Try to reconnect if sending fails
                    try:
                        client_socket.close()
                        new_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        new_socket.connect((receiver_ip, receiver_port))
                        client_socket = new_socket
                        
                        # Re-send video info
                        video_info = {
                            "width": frame_width,
                            "height": frame_height,
                            "fps": target_fps,
                            "quality": jpeg_quality
                        }
                        info_data = pickle.dumps(video_info, protocol=4)
                        client_socket.sendall(struct.pack(">L", len(info_data)))
                        client_socket.sendall(info_data)
                        
                        print("Reconnected to receiver")
                    except:
                        print("Failed to reconnect")
                        time.sleep(1.0)  # Wait before trying again
                
                # Update last frame time for consistent sending rate
                last_frame_time = current_time
            else:
                # No frames in buffer, wait a bit
                time.sleep(0.001)
        else:
            # Not time to send next frame yet, short sleep
            time.sleep(0.001)

# Custom HTTP request handler for metrics API
class MetricsHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        global bytes_sent, packets_sent, frame_sizes, frame_times, frame_buffer
        global frame_width, frame_height, video_fps, target_fps, jpeg_quality
        
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/metrics':
            # Calculate metrics
            avg_frame_size = sum(frame_sizes) / len(frame_sizes) if frame_sizes else 0
            avg_process_time = sum(frame_times) / len(frame_times) if frame_times else 0
            actual_fps = 1 / avg_process_time if avg_process_time > 0 else 0
            buffer_fullness = (len(frame_buffer) / frame_buffer.maxlen * 100) if frame_buffer.maxlen > 0 else 0
            
            # Create metrics JSON
            metrics = {
                "bandwidth_usage": bytes_sent / (1024 * 1024 * (time.time() - start_time)) if time.time() > start_time else 0,  # MB/s
                "frame_size": avg_frame_size / 1024,  # KB
                "process_time": avg_process_time * 1000,  # ms
                "actual_fps": actual_fps,
                "target_fps": target_fps,
                "buffer_fullness": buffer_fullness,  # %
                "resolution": f"{frame_width}x{frame_height}",
                "quality": jpeg_quality,
                "total_frames": len(frame_times)
            }
            
            # Send response
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')  # Allow cross-origin requests
            self.end_headers()
            self.wfile.write(json.dumps(metrics).encode())
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Not Found')
    
    def log_message(self, format, *args):
        # Suppress log messages to keep console clean
        return

# Function to start metrics API server
def start_metrics_server(port):
    global metrics_server, metrics_handler
    
    # Create server
    metrics_handler = MetricsHandler
    metrics_server = socketserver.ThreadingTCPServer(("", port), metrics_handler)
    
    # Start server in a separate thread
    server_thread = Thread(target=metrics_server.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    
    print(f"Metrics API server started on port {port}")
    print(f"Access metrics at: http://localhost:{port}/metrics")

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Video Sender")
    parser.add_argument("--ip", default="127.0.0.1", help="Receiver IP address")
    parser.add_argument("--port", type=int, default=9999, help="Receiver port")
    parser.add_argument("--video", default="../video/zidane.mp4", help="Video file path (default: ../video/zidane.mp4)")
    parser.add_argument("--quality", type=int, default=90, help="JPEG quality (1-100)")
    parser.add_argument("--scale", type=float, default=1.0, help="Resolution scale factor")
    parser.add_argument("--fps", type=float, default=0, help="Target FPS (0=use video's FPS)")
    parser.add_argument("--buffer", type=int, default=5, help="Frame buffer size")
    parser.add_argument("--display", action="store_true", help="Display video locally", default=True)
    parser.add_argument("--metrics-port", type=int, default=8000, help="Port for metrics API server")
    
    args = parser.parse_args()
    
    # Set variables from arguments
    receiver_ip = args.ip
    receiver_port = args.port
    video_path = args.video
    jpeg_quality = args.quality
    scale_factor = args.scale
    target_fps_arg = args.fps
    frame_buffer = deque(maxlen=args.buffer)
    display_video = args.display
    metrics_port = args.metrics_port
    
    # Print display status
    if display_video:
        print("Video display is ENABLED - you should see a window showing the video")
        # Create a window for the video
        cv2.namedWindow("Sender Video", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Sender Video", 640, 360)
    
    # Create TCP socket
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.settimeout(30)  # Set a 30-second timeout for socket operations
    
    try:
        # Connect to receiver with retry
        print(f"Connecting to {receiver_ip}:{receiver_port}...")
        max_retries = 3
        retry_count = 0
        connected = False
        
        while retry_count < max_retries and not connected:
            try:
                client_socket.connect((receiver_ip, receiver_port))
                connected = True
                print("Connected to receiver")
            except socket.error as e:
                retry_count += 1
                print(f"Connection failed (attempt {retry_count}/{max_retries}): {e}")
                if retry_count < max_retries:
                    print(f"Retrying in 2 seconds...")
                    time.sleep(2)
                    # Create a new socket for retry
                    client_socket.close()
                    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    client_socket.settimeout(30)
        
        if not connected:
            print(f"Failed to connect to receiver after {max_retries} attempts")
            print("Please make sure the receiver is running and the IP address is correct")
            print("Usage example: python direct_sender.py --ip RECEIVER_IP")
            exit()
        
        # Start metrics API server
        start_metrics_server(metrics_port)
        print(f"Metrics available at: http://{socket.gethostbyname(socket.gethostname())}:{metrics_port}/metrics")
        
        # Check if video file exists
        import os
        if not os.path.exists(video_path):
            print(f"Error: Video file not found: {video_path}")
            print(f"Current working directory: {os.getcwd()}")
            print(f"Absolute path: {os.path.abspath(video_path)}")
            print("Please provide a valid video file path using --video argument")
            client_socket.close()
            exit()
            
        # Open video file
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print(f"Error: Could not open video file {video_path}")
            print("This could be due to missing codecs or an unsupported video format")
            client_socket.close()
            exit()
        
        # Get video properties
        frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) * scale_factor)
        frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) * scale_factor)
        video_fps = cap.get(cv2.CAP_PROP_FPS)
        
        # Use target FPS from argument or video's FPS
        target_fps = target_fps_arg if target_fps_arg > 0 else video_fps
        
        print(f"Video opened: {frame_width}x{frame_height}")
        print(f"Video FPS: {video_fps}, Target FPS: {target_fps}")
        
        # Send video info to receiver
        print("Preparing to send video info to receiver...")
        video_info = {
            "width": frame_width,
            "height": frame_height,
            "fps": target_fps,
            "quality": jpeg_quality
        }
        print(f"Video info to send: {video_info}")
        
        try:
            # Use pickle protocol 4 for better compatibility
            info_data = pickle.dumps(video_info, protocol=4)
            print(f"Serialized video info: {len(info_data)} bytes")
            
            # Send size first
            size_bytes = struct.pack(">L", len(info_data))
            print(f"Sending size header: {len(size_bytes)} bytes, value: {len(info_data)}")
            client_socket.sendall(size_bytes)
            
            # Send actual data
            print(f"Sending video info data: {len(info_data)} bytes")
            client_socket.sendall(info_data)
            print("Video info sent successfully")
        except Exception as e:
            print(f"Error sending video info: {e}")
            import traceback
            traceback.print_exc()
        
        # Start sending thread
        send_thread = threading.Thread(target=send_frames_thread, args=(client_socket, target_fps))
        send_thread.daemon = True
        send_thread.start()
        
        # Start reading frames
        frame_count = 0
        last_stats_time = time.time()
        
        # Pre-fill buffer (minimal fill for lowest latency)
        print("Pre-filling buffer...")
        buffer_target = min(3, frame_buffer.maxlen)  # Only fill 3 frames
        while len(frame_buffer) < buffer_target and running:
            ret, frame = cap.read()
            if not ret:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue
                
            # Resize frame if needed
            if scale_factor != 1.0:
                frame = cv2.resize(frame, (frame_width, frame_height))
                
            # Add frame to buffer
            with buffer_lock:
                frame_buffer.append(frame)
                
            print(f"Buffer: {len(frame_buffer)}/{frame_buffer.maxlen}", end="\r")
            
        print("\nBuffer filled, starting transmission")
        
        # Calculate frame reading rate - slightly faster than target FPS to keep buffer filled
        read_fps = min(target_fps * 1.1, video_fps)
        read_interval = 1.0 / read_fps
        last_read_time = time.time()
        
        # Main loop - read frames and add to buffer
        while running:
            # Control reading rate to match the video's natural FPS
            current_time = time.time()
            elapsed = current_time - last_read_time
            
            if elapsed >= read_interval:
                # Read a frame from the video
                ret, frame = cap.read()
                
                if not ret:
                    # Loop back to the beginning of the video when it ends
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue
                
                # Resize frame if needed
                if scale_factor != 1.0:
                    frame = cv2.resize(frame, (frame_width, frame_height))
                
                # Display frame immediately for lowest latency
                if display_video:
                    try:
                        # Add text to the frame
                        display_frame = frame.copy()
                        cv2.putText(display_frame, "SENDER PREVIEW", (10, 30),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                        
                        # Show the frame
                        cv2.imshow("Sender Video", display_frame)
                        
                        # Process key presses (q to quit)
                        key = cv2.waitKey(1) & 0xFF
                        if key == ord('q'):
                            running = False
                            break
                    except Exception as e:
                        print(f"Error displaying video: {e}")
                        display_video = False
                
                # Add frame to buffer if there's space
                with buffer_lock:
                    if len(frame_buffer) < frame_buffer.maxlen:
                        frame_buffer.append(frame)
                
                frame_count += 1
                last_read_time = current_time
            else:
                # Not time to read next frame yet, short sleep
                time.sleep(0.001)
            
            # Print statistics every second
            current_time = time.time()
            if current_time - last_stats_time >= 1.0:
                print_stats()
                last_stats_time = current_time
    
    except KeyboardInterrupt:
        print("\nStopped by user")
    
    except Exception as e:
        print(f"Error: {e}")
    
    finally:
        # Clean up resources
        running = False
        if send_thread and send_thread.is_alive():
            send_thread.join(timeout=1.0)
        
        if 'cap' in locals() and cap.isOpened():
            cap.release()
        
        client_socket.close()
        print("Socket closed")
        
        # Stop metrics server
        if metrics_server:
            metrics_server.shutdown()
            metrics_server.server_close()
            print("Metrics server stopped")
        
        if display_video:
            cv2.destroyAllWindows()
            print("Video window closed")