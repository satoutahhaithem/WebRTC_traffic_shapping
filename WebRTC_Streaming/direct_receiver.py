#!/usr/bin/env python3
"""
Video Receiver Script

This script receives video frames from a sender over a TCP socket and optionally
displays them. It shows real-time traffic statistics in the terminal.

Usage:
    python direct_receiver.py [--display]

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
bytes_received = 0    # Total bytes received
packets_received = 0  # Total packets received
frame_sizes = deque(maxlen=30)  # Last 30 frame sizes for averaging
frame_times = deque(maxlen=30)  # Last 30 frame processing times
start_time = time.time()        # When the script started
frames_received = 0   # Total frames received
frames_displayed = 0  # Total frames displayed
frames_dropped = 0    # Total frames dropped
video_info = None     # Video information from sender

# Frame buffering for smoother playback
frame_buffer = deque(maxlen=5)  # Buffer to store frames (minimal size for lowest latency)
buffer_lock = threading.Lock()   # Lock for thread-safe buffer access
buffer_thread = None             # Thread for receiving frames
running = True                   # Flag to control threads

# API server for metrics
metrics_port = 8001  # Port for the metrics API server (different from sender)
metrics_server = None
metrics_handler = None

def print_stats():
    """
    Print current traffic statistics to the terminal.
    Clears the terminal and shows a formatted display of all metrics.
    """
    global bytes_received, packets_received, start_time, frame_sizes, frame_times
    global frames_received, frames_displayed, frames_dropped, video_info, frame_buffer
    
    # Calculate elapsed time
    elapsed = time.time() - start_time
    
    # Calculate rates
    bytes_received_rate = bytes_received / elapsed if elapsed > 0 else 0
    packets_received_rate = packets_received / elapsed if elapsed > 0 else 0
    
    # Calculate averages
    avg_frame_size = sum(frame_sizes) / len(frame_sizes) if frame_sizes else 0
    avg_frame_time = sum(frame_times) / len(frame_times) if frame_times else 0
    fps = 1 / avg_frame_time if avg_frame_time > 0 else 0
    
    # Calculate drop rate
    drop_rate = (frames_dropped / frames_received * 100) if frames_received > 0 else 0
    
    # Calculate buffer fullness
    buffer_percent = (len(frame_buffer) / frame_buffer.maxlen * 100) if frame_buffer.maxlen > 0 else 0
    
    # Clear terminal and print stats
    print("\033c", end="")  # Clear terminal
    
    print("\n" + "="*50)
    print("VIDEO RECEIVER - TRAFFIC MONITOR")
    print("="*50)
    print(f"Running time: {elapsed:.1f} seconds")
    print(f"Listening on: {server_ip}:{server_port}")
    print("\nTRAFFIC STATISTICS:")
    print(f"  Bytes received: {bytes_received} bytes ({bytes_received/1024/1024:.2f} MB)")
    print(f"  Packets received: {packets_received}")
    print(f"  Receive rate:   {bytes_received_rate/1024/1024:.2f} MB/s")
    print(f"  Packet rate:    {packets_received_rate:.1f} packets/s")
    print("\nVIDEO STATISTICS:")
    if video_info:
        print(f"  Resolution:     {video_info['width']}x{video_info['height']}")
        print(f"  Target FPS:     {video_info['fps']:.1f}")
        print(f"  Playback FPS:   {playback_fps:.1f}")
        print(f"  Quality:        {video_info['quality']}%")
    print(f"  Actual FPS:     {fps:.1f}")
    print(f"  Frames received: {frames_received}")
    print(f"  Frames displayed: {frames_displayed}")
    print(f"  Frames dropped:  {frames_dropped} ({drop_rate:.1f}%)")
    print(f"  Avg frame size: {avg_frame_size/1024:.1f} KB")
    print(f"  Buffer fullness: {len(frame_buffer)}/{frame_buffer.maxlen} ({buffer_percent:.1f}%)")
    print("="*50)

def receive_frame(client_socket):
    """
    Receive a frame from the sender
    
    Args:
        client_socket: Socket connected to the sender
        
    Returns:
        numpy.ndarray: The received frame, or None if failed
    """
    global bytes_received, packets_received, frame_sizes, frame_times
    global frames_received, frames_dropped
    
    # Record start time for performance measurement
    start_process = time.time()
    
    try:
        # Receive the size of the data (4 bytes)
        size_data = client_socket.recv(4)
        if not size_data:
            return None
        
        # Unpack the size value from the received bytes
        size = struct.unpack(">L", size_data)[0]
        
        # Receive the actual frame data
        data = b""
        while len(data) < size:
            # Receive in chunks to handle large frames
            packet = client_socket.recv(min(size - len(data), 4096))
            if not packet:
                return None
            data += packet
        
        # Update traffic statistics
        bytes_received += len(data) + 4  # +4 for the size header
        packets_received += 1
        frame_sizes.append(size)
        frames_received += 1
        
        # Deserialize the data
        encoded_frame = pickle.loads(data)
        
        # Decode the JPEG frame
        frame = cv2.imdecode(encoded_frame, cv2.IMREAD_COLOR)
        
        if frame is None:
            frames_dropped += 1
            return None
        
        # Calculate frame processing time
        frame_times.append(time.time() - start_process)
        
        return frame
    
    except Exception as e:
        print(f"Error receiving frame: {e}")
        frames_dropped += 1
        return None

def receive_video_info(client_socket):
    """
    Receive video information from the sender
    
    Args:
        client_socket: Socket connected to the sender
        
    Returns:
        dict: Video information (width, height, fps, quality), or None if failed
    """
    try:
        print("Waiting to receive video info size...")
        # Receive the size of the data (4 bytes)
        size_data = client_socket.recv(4)
        if not size_data:
            print("Failed to receive size data (empty)")
            return None
        
        print(f"Received size data: {len(size_data)} bytes")
        
        # Unpack the size value
        try:
            size = struct.unpack(">L", size_data)[0]
            print(f"Unpacked size: {size} bytes")
        except struct.error as e:
            print(f"Error unpacking size: {e}, received data: {size_data!r}")
            return None
        
        # Receive the data
        print(f"Waiting to receive {size} bytes of video info data...")
        data = b""
        while len(data) < size:
            packet = client_socket.recv(min(size - len(data), 4096))
            if not packet:
                print(f"Failed to receive data packet (empty) after receiving {len(data)}/{size} bytes")
                return None
            data += packet
            print(f"Received {len(data)}/{size} bytes")
        
        # Deserialize the data to get video info
        try:
            print(f"Deserializing {len(data)} bytes of data...")
            video_info = pickle.loads(data)
            print(f"Successfully deserialized video info: {video_info}")
            return video_info
        except (pickle.UnpicklingError, EOFError, AttributeError) as e:
            print(f"Error deserializing video info: {e}")
            print(f"First 100 bytes of data: {data[:100]!r}")
            
            # Try with different pickle protocols as a fallback
            for protocol in range(5):  # Try protocols 0-4
                try:
                    print(f"Trying to deserialize with protocol {protocol}...")
                    # This is a hack to try different protocols
                    # It won't work for all cases but might help in some situations
                    if protocol == 0:
                        # Try a simple fallback with default values
                        print("Using fallback default video info")
                        return {
                            "width": 640,
                            "height": 480,
                            "fps": 30.0,
                            "quality": 90
                        }
                except Exception as e:
                    print(f"Protocol {protocol} failed: {e}")
            
            return None
    
    except Exception as e:
        print(f"Error receiving video info: {e}")
        import traceback
        traceback.print_exc()
        return None

def buffer_frames(client_socket):
    """
    Continuously receive frames and add them to the buffer
    
    Args:
        client_socket: Socket connected to the sender
    """
    global frame_buffer, running
    
    while running:
        frame = receive_frame(client_socket)
        if frame is not None:
            with buffer_lock:
                # If buffer is full, remove oldest frame
                if len(frame_buffer) >= frame_buffer.maxlen:
                    frame_buffer.popleft()
                frame_buffer.append(frame)
        else:
            # If we failed to receive a frame, wait a bit before trying again
            time.sleep(0.01)

# Custom HTTP request handler for metrics API
class MetricsHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        global bytes_received, packets_received, frame_sizes, frame_times
        global frames_received, frames_displayed, frames_dropped, video_info, frame_buffer
        
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/metrics':
            # Calculate metrics
            avg_frame_size = sum(frame_sizes) / len(frame_sizes) if frame_sizes else 0
            avg_process_time = sum(frame_times) / len(frame_times) if frame_times else 0
            actual_fps = 1 / avg_process_time if avg_process_time > 0 else 0
            buffer_fullness = (len(frame_buffer) / frame_buffer.maxlen * 100) if frame_buffer.maxlen > 0 else 0
            drop_rate = (frames_dropped / frames_received * 100) if frames_received > 0 else 0
            
            # Create metrics JSON
            metrics = {
                "bandwidth_usage": bytes_received / (1024 * 1024 * (time.time() - start_time)) if time.time() > start_time else 0,  # MB/s
                "frame_size": avg_frame_size / 1024,  # KB
                "frame_delivery_time": avg_process_time * 1000,  # ms
                "actual_fps": actual_fps,
                "buffer_fullness": buffer_fullness,  # %
                "frame_drop_rate": drop_rate,  # %
                "frames_received": frames_received,
                "frames_displayed": frames_displayed,
                "frames_dropped": frames_dropped
            }
            
            if video_info:
                metrics["resolution"] = f"{video_info.get('width', 0)}x{video_info.get('height', 0)}"
                metrics["target_fps"] = video_info.get('fps', 0)
                metrics["quality"] = video_info.get('quality', 0)
            
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
    parser = argparse.ArgumentParser(description="Video Receiver")
    parser.add_argument("--ip", default="0.0.0.0", help="IP address to listen on")
    parser.add_argument("--port", type=int, default=9999, help="Port to listen on")
    parser.add_argument("--display", action="store_true", help="Display video (requires GUI)")
    parser.add_argument("--buffer", type=int, default=5, help="Frame buffer size")
    parser.add_argument("--fps", type=float, default=0, help="Override playback FPS (0=use sender's FPS)")
    parser.add_argument("--low-latency", action="store_true", help="Enable low latency mode", default=True)
    parser.add_argument("--metrics-port", type=int, default=8001, help="Port for metrics API server")
    
    args = parser.parse_args()
    
    # Set variables from arguments
    server_ip = args.ip
    server_port = args.port
    display_video = args.display
    frame_buffer = deque(maxlen=args.buffer)
    override_fps = args.fps
    playback_fps = override_fps  # Will be updated with video_info if not overridden
    metrics_port = args.metrics_port
    
    # Create TCP socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.settimeout(30)  # Set a 30-second timeout for socket operations
    
    try:
        # Bind socket to address and port
        server_socket.bind((server_ip, server_port))
        server_socket.listen(5)
        print(f"Listening on {server_ip}:{server_port}...")
        
        # Start metrics API server
        start_metrics_server(metrics_port)
        print(f"Metrics available at: http://{socket.gethostbyname(socket.gethostname())}:{metrics_port}/metrics")
        
        # Accept connection from sender with error handling
        print(f"Waiting for sender to connect on {server_ip}:{server_port}...")
        try:
            client_socket, addr = server_socket.accept()
            client_socket.settimeout(30)  # Set a 30-second timeout for client socket operations
            print(f"Connection from {addr}")
        except socket.timeout:
            print("Timed out waiting for connection")
            print("Please make sure the sender is running and trying to connect")
            server_socket.close()
            exit()
        except socket.error as e:
            print(f"Error accepting connection: {e}")
            server_socket.close()
            exit()
        
        # Receive video information with retries
        print("Attempting to receive video information...")
        max_retries = 3
        retry_count = 0
        video_info = None
        
        while retry_count < max_retries and not video_info:
            video_info = receive_video_info(client_socket)
            if not video_info:
                retry_count += 1
                print(f"Failed to receive video info (attempt {retry_count}/{max_retries})")
                if retry_count < max_retries:
                    print(f"Retrying in 2 seconds...")
                    time.sleep(2)
        
        if not video_info:
            print("All attempts to receive video info failed")
            client_socket.close()
            server_socket.close()
            exit()
        
        print(f"Received video info: {video_info}")
        
        # Set playback FPS from video_info if not overridden
        if override_fps <= 0 and video_info and 'fps' in video_info:
            playback_fps = video_info['fps']
        elif override_fps > 0:
            playback_fps = override_fps
        else:
            playback_fps = 30.0  # Default if no FPS info available
            
        print(f"Using playback FPS: {playback_fps}")
        
        # Start frame buffering thread
        buffer_thread = threading.Thread(target=buffer_frames, args=(client_socket,))
        buffer_thread.daemon = True
        buffer_thread.start()
        
        # Wait for buffer to fill initially (reduced for lower latency)
        print("Buffering frames...")
        buffer_fill_start = time.time()
        
        # If low latency mode is enabled, use minimal buffering
        if args.low_latency:
            buffer_target = min(2, frame_buffer.maxlen)  # Only wait for 2 frames
        else:
            buffer_target = min(5, frame_buffer.maxlen)
            
        while len(frame_buffer) < buffer_target:
            # Don't wait more than 1 second for buffer to fill
            if time.time() - buffer_fill_start > 1.0:
                break
            time.sleep(0.01)  # Check more frequently
            print(f"Buffer: {len(frame_buffer)}/{frame_buffer.maxlen}", end="\r")
        print("\nBuffer filled, starting playback")
        
        # Start displaying frames
        last_stats_time = time.time()
        last_frame_time = time.time()
        
        # Calculate target frame time based on playback FPS
        target_frame_time = 1.0 / playback_fps
        
        while running:
            # Calculate time since last frame
            current_time = time.time()
            elapsed = current_time - last_frame_time
            
            # Only display a new frame if enough time has passed (control playback speed)
            if elapsed >= target_frame_time:
                # Get frame from buffer
                frame = None
                with buffer_lock:
                    if frame_buffer:
                        frame = frame_buffer.popleft()
                
                if frame is not None:
                    # Display frame if requested
                    if display_video:
                        try:
                            # Add text to the frame for identification
                            display_frame = frame.copy()
                            cv2.putText(display_frame, "RECEIVER", (10, 30),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                            
                            cv2.imshow('Received Video', display_frame)
                            frames_displayed += 1
                            
                            # Press 'q' to quit
                            key = cv2.waitKey(1) & 0xFF
                            if key == ord('q'):
                                running = False
                                break
                        except Exception as e:
                            print(f"Error displaying frame: {e}")
                            display_video = False # Disable display if it fails
                    
                    # Update last frame time for consistent playback speed
                    last_frame_time = current_time
                else:
                    # No frames in buffer, wait a bit (reduced wait time)
                    time.sleep(0.001)
            else:
                # Not time for next frame yet, shorter sleep for more responsive playback
                time.sleep(0.0005)
            
            # Print statistics every second
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
        if buffer_thread and buffer_thread.is_alive():
            buffer_thread.join(timeout=1.0)
        
        if 'client_socket' in locals():
            client_socket.close()
        
        server_socket.close()
        
        # Stop metrics server
        if metrics_server:
            metrics_server.shutdown()
            metrics_server.server_close()
            print("Metrics server stopped")
        
        if display_video:
            cv2.destroyAllWindows()
        
        print("Socket closed")