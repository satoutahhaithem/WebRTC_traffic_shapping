#!/usr/bin/env python3
"""
Traffic Control Settings Receiver

This script runs a simple HTTP server that receives traffic control settings
from the sender and stores them for use by the performance measurement script.

Usage:
    python tc_settings_receiver.py [--port PORT]

Author: Roo AI Assistant
Date: May 2025
"""

import argparse
import json
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs

# Default settings
DEFAULT_PORT = 8765

# Global variables
current_settings = {
    "preset": "NONE",
    "rate": 0,
    "delay": 0,
    "loss": 0,
    "timestamp": 0
}

# Lock for thread-safe access to current_settings
settings_lock = threading.Lock()

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

class TCSettingsHandler(BaseHTTPRequestHandler):
    def _set_response(self, status_code=200, content_type='application/json'):
        self.send_response(status_code)
        self.send_header('Content-type', content_type)
        self.end_headers()
    
    def do_GET(self):
        """Handle GET requests to retrieve current settings"""
        if self.path == '/tc_settings':
            # Return current settings
            with settings_lock:
                response = json.dumps(current_settings)
            
            self._set_response()
            self.wfile.write(response.encode('utf-8'))
        else:
            self._set_response(404)
            self.wfile.write(json.dumps({"error": "Not found"}).encode('utf-8'))
    
    def do_POST(self):
        """Handle POST requests to update settings"""
        if self.path == '/tc_settings':
            # Get content length
            content_length = int(self.headers['Content-Length'])
            
            # Read and parse the POST data
            post_data = self.rfile.read(content_length).decode('utf-8')
            
            try:
                # Parse JSON data
                settings = json.loads(post_data)
                
                # Update current settings with thread safety
                with settings_lock:
                    current_settings["preset"] = settings.get("preset", "UNKNOWN")
                    current_settings["rate"] = float(settings.get("rate", 0))
                    current_settings["delay"] = float(settings.get("delay", 0))
                    current_settings["loss"] = float(settings.get("loss", 0))
                    current_settings["timestamp"] = time.time()
                
                # Print the received settings
                print(f"\n{Colors.BLUE}======================================================{Colors.ENDC}")
                print(f"{Colors.BLUE}RECEIVED TRAFFIC CONTROL SETTINGS{Colors.ENDC}")
                print(f"{Colors.BLUE}======================================================{Colors.ENDC}")
                print(f"Preset: {Colors.CYAN}{current_settings['preset']}{Colors.ENDC}")
                print(f"Rate: {Colors.CYAN}{current_settings['rate']} Mbps{Colors.ENDC}")
                print(f"Delay: {Colors.CYAN}{current_settings['delay']} ms{Colors.ENDC}")
                print(f"Loss: {Colors.CYAN}{current_settings['loss']}%{Colors.ENDC}")
                print(f"{Colors.BLUE}======================================================{Colors.ENDC}")
                
                # Send success response
                self._set_response()
                self.wfile.write(json.dumps({"status": "success"}).encode('utf-8'))
            
            except json.JSONDecodeError:
                print(f"{Colors.RED}Error: Invalid JSON data received{Colors.ENDC}")
                self._set_response(400)
                self.wfile.write(json.dumps({"error": "Invalid JSON"}).encode('utf-8'))
            
            except Exception as e:
                print(f"{Colors.RED}Error processing request: {e}{Colors.ENDC}")
                self._set_response(500)
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
        
        else:
            self._set_response(404)
            self.wfile.write(json.dumps({"error": "Not found"}).encode('utf-8'))
    
    def log_message(self, format, *args):
        """Override to customize logging"""
        if args[1] == '200':
            print(f"{Colors.GREEN}[{self.log_date_time_string()}] {args[0]} {args[1]}{Colors.ENDC}")
        else:
            print(f"{Colors.YELLOW}[{self.log_date_time_string()}] {args[0]} {args[1]}{Colors.ENDC}")

def run_server(port):
    """Run the HTTP server"""
    server_address = ('', port)
    httpd = HTTPServer(server_address, TCSettingsHandler)
    print(f"{Colors.GREEN}Starting TC settings receiver server on port {port}...{Colors.ENDC}")
    print(f"{Colors.CYAN}Waiting for traffic control settings from sender...{Colors.ENDC}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print(f"{Colors.YELLOW}Server stopped by user{Colors.ENDC}")
    finally:
        httpd.server_close()

def get_current_settings():
    """Get the current traffic control settings (for use by other scripts)"""
    with settings_lock:
        return current_settings.copy()

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Traffic Control Settings Receiver")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Port to listen on")
    args = parser.parse_args()
    
    run_server(args.port)

if __name__ == "__main__":
    main()