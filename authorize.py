#!/usr/bin/env python3
"""
One-time authorization script for Strava API access.
Run this once to get initial access and refresh tokens.
"""

import os
import webbrowser
import http.server
import socketserver
import threading
import urllib.parse
from queue import Queue
from stravalib.client import Client
from dotenv import load_dotenv
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configuration
CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')

def create_local_server(port=8000, auth_queue=None):
    """
    Create a local server to handle the OAuth callback
    """
    class OAuthHandler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            query_components = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b"Authorization successful! You can close this window.")
            
            if auth_queue and 'code' in query_components:
                auth_queue.put(query_components['code'][0])
    
    httpd = socketserver.TCPServer(('localhost', port), OAuthHandler)
    server_thread = threading.Thread(target=httpd.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    
    return httpd

def update_env_file(token_response):
    """
    Update the .env file with new tokens
    """
    env_path = '.env'
    
    # Read existing content
    if os.path.exists(env_path):
        with open(env_path, 'r') as file:
            lines = file.readlines()
    else:
        lines = []
    
    # Update or add tokens
    tokens_updated = {'ACCESS_TOKEN': False, 'REFRESH_TOKEN': False}
    new_lines = []
    
    for line in lines:
        if line.startswith('ACCESS_TOKEN='):
            new_lines.append(f"ACCESS_TOKEN={token_response['access_token']}\n")
            tokens_updated['ACCESS_TOKEN'] = True
        elif line.startswith('REFRESH_TOKEN='):
            new_lines.append(f"REFRESH_TOKEN={token_response['refresh_token']}\n")
            tokens_updated['REFRESH_TOKEN'] = True
        else:
            new_lines.append(line)
    
    # Add any missing tokens
    if not tokens_updated['ACCESS_TOKEN']:
        new_lines.append(f"ACCESS_TOKEN={token_response['access_token']}\n")
    if not tokens_updated['REFRESH_TOKEN']:
        new_lines.append(f"REFRESH_TOKEN={token_response['refresh_token']}\n")
    
    # Write back to file
    with open(env_path, 'w') as file:
        file.writelines(new_lines)

def main():
    """
    Perform initial authorization and save tokens
    """
    try:
        if not all([CLIENT_ID, CLIENT_SECRET]):
            raise ValueError("Missing CLIENT_ID or CLIENT_SECRET in .env file")
        
        auth_queue = Queue()
        server = None
        
        try:
            # Start local server
            port = 8000
            server = create_local_server(port=port, auth_queue=auth_queue)
            logger.info("Started local authentication server")
            
            client = Client()
            
            # Generate authorization URL
            auth_url = client.authorization_url(
                client_id=CLIENT_ID,
                redirect_uri=f'http://localhost:{port}',
                scope=['read_all', 'activity:read_all', 'profile:read_all']
            )
            
            # Open browser for authorization
            logger.info("Opening browser for Strava authorization...")
            webbrowser.open(auth_url)
            
            # Wait for the authorization code
            logger.info("Waiting for authorization (60 seconds timeout)...")
            code = auth_queue.get(timeout=60)
            logger.info("Authorization code received!")
            
            # Exchange the code for tokens
            token_response = client.exchange_code_for_token(
                client_id=CLIENT_ID,
                client_secret=CLIENT_SECRET,
                code=code
            )
            
            # Update the .env file
            update_env_file(token_response)
            logger.info("Successfully obtained and saved tokens!")
            
        finally:
            if server:
                server.shutdown()
                server.server_close()
                
    except Exception as e:
        logger.error(f"Authorization failed: {str(e)}")
        raise

if __name__ == '__main__':
    main() 