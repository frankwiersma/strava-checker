#!/usr/bin/env python3
"""
Strava Daily Activities Updater

This script connects to the Strava API, retrieves the latest sports activities,
and appends (increments) any new activities to a local JSON file ("activities.json").
Run this script every day (e.g. via a cron job) to keep your activities file updated.

Authentication Instructions:
----------------------------------
1. Log in to your Strava account and navigate to:
   https://www.strava.com/settings/api
   Create a new application to obtain your CLIENT_ID and CLIENT_SECRET.

2. To obtain an access token (which is required to access your data), you can use
   a one-time interactive flow. For example, run the following code snippet:

       from stravalib import Client
       client = Client()
       # Build the authorization URL. For local testing, you can use a redirect_uri like "http://localhost".
       print(client.authorization_url(client_id=YOUR_CLIENT_ID, redirect_uri="http://localhost"))
       # Open the printed URL in your browser, authorize the application, and note the "code" parameter from the redirect URL.
       token_response = client.exchange_code_for_token(
           client_id=YOUR_CLIENT_ID,
           client_secret=YOUR_CLIENT_SECRET,
           code="CODE_FROM_REDIRECT"
       )
       print(token_response)

   The token_response will include an "access_token" (and a "refresh_token").
   **NOTE:** Strava access tokens expire in 6 hours. For a production script you should
   implement token refreshing using the refresh token. For simplicity, this script uses a static access token.

3. Replace the placeholder values for CLIENT_ID, CLIENT_SECRET, and ACCESS_TOKEN in this script
   with your own credentials.

Dependencies:
-------------
Install the required package with:

    pip install stravalib

Usage:
------
    python strava_daily_update.py

This script will:
  • Load existing activities from "activities.json" (or create a new list if the file doesn't exist).
  • Use your access token to fetch the latest 30 activities.
  • Compare each fetched activity by its id to see if it's already stored.
  • Append any new activities to the list and rewrite the JSON file.
"""

import json
import os
import webbrowser
from stravalib.client import Client
from dotenv import load_dotenv
import logging
import http.server
import socketserver
import threading
import urllib.parse
from queue import Queue
import argparse

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# -----------------------------
# CONFIGURATION: Load credentials from environment variables
# -----------------------------
CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
ACCESS_TOKEN = os.getenv('ACCESS_TOKEN')
REFRESH_TOKEN = os.getenv('REFRESH_TOKEN')

# JSON file where activities will be stored
ACTIVITIES_FILE = 'activities.json'

def create_local_server(port=8000, auth_queue=None):
    """
    Create a local server to handle the OAuth callback
    """
    class OAuthHandler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            # Parse the authorization code from the callback URL
            query_components = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            
            # Send a response to the browser
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b"Authorization successful! You can close this window.")
            
            # Put the code in the queue
            if auth_queue and 'code' in query_components:
                auth_queue.put(query_components['code'][0])
    
    # Create and start server in a separate thread
    httpd = socketserver.TCPServer(('localhost', port), OAuthHandler)
    server_thread = threading.Thread(target=httpd.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    
    return httpd

def get_token():
    """
    Get a valid access token, using refresh token if possible
    """
    try:
        # First try to refresh the token
        if REFRESH_TOKEN:
            try:
                logger.info("Attempting to refresh access token...")
                client = Client()
                refresh_response = client.refresh_access_token(
                    client_id=CLIENT_ID,
                    client_secret=CLIENT_SECRET,
                    refresh_token=REFRESH_TOKEN
                )
                
                # Update the .env file with new tokens
                update_env_file(refresh_response)
                logger.info("Successfully refreshed access token!")
                
                return refresh_response['access_token']
                
            except Exception as e:
                logger.warning(f"Token refresh failed: {str(e)}")
        
        # If we don't have a refresh token or refresh failed, we need manual authorization
        if not REFRESH_TOKEN:
            logger.error("No refresh token found. Please run the script once with --authorize flag to perform initial authorization")
            raise ValueError("Missing refresh token. Initial authorization required.")
        
        raise ValueError("Failed to get valid access token")
        
    except Exception as e:
        logger.error(f"Failed to get access token: {str(e)}")
        raise

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

def refresh_access_token():
    """
    Refresh the access token using the refresh token
    """
    client = Client()
    refresh_response = client.refresh_access_token(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        refresh_token=REFRESH_TOKEN
    )
    
    # Update the .env file with new access token
    update_env_file(refresh_response)
    return refresh_response['access_token']

def load_existing_activities(filepath):
    """
    Load existing activities from a JSON file.
    Returns a list of activities or an empty list if file does not exist or is empty.
    """
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []

def save_activities(filepath, activities):
    """
    Save the list of activities to a JSON file with indentation for readability.
    """
    with open(filepath, 'w') as f:
        json.dump(activities, f, indent=4)

def activity_to_dict(activity):
    """
    Convert a Strava activity object to a dictionary with relevant fields.
    Handles properties dynamically and gracefully.
    """
    try:
        # Process base properties (required)
        result = {
            'id': int(activity.id),
            'name': str(activity.name),
            'start_date_local': str(activity.start_date_local),
            'type': str(activity.type),
            'distance': float(activity.distance) if hasattr(activity, 'distance') and activity.distance else 0.0,
            'moving_time': int(activity.moving_time) if hasattr(activity, 'moving_time') and activity.moving_time else 0,
            'elapsed_time': int(activity.elapsed_time) if hasattr(activity, 'elapsed_time') and activity.elapsed_time else 0,
        }

        # Optional numeric properties with proper null handling
        float_properties = {
            'total_elevation_gain': 'total_elevation_gain',
            'average_speed': 'average_speed',
            'max_speed': 'max_speed',
            'average_heartrate': 'average_heartrate',
            'max_heartrate': 'max_heartrate',
            'average_cadence': 'average_cadence',
            'average_watts': 'average_watts',
            'calories': 'calories',
        }
        
        for key, attr in float_properties.items():
            try:
                if hasattr(activity, attr):
                    value = getattr(activity, attr)
                    result[key] = float(value) if value is not None else None
                else:
                    result[key] = None
            except (AttributeError, TypeError, ValueError):
                result[key] = None

        # Optional integer properties
        int_properties = {
            'kudos_count': 'kudos_count',
            'achievement_count': 'achievement_count',
            'athlete_count': 'athlete_count',
        }
        
        for key, attr in int_properties.items():
            try:
                if hasattr(activity, attr):
                    value = getattr(activity, attr)
                    result[key] = int(value) if value is not None else 0
                else:
                    result[key] = 0
            except (AttributeError, TypeError, ValueError):
                result[key] = 0

        # Optional string properties
        str_properties = {
            'gear_id': 'gear_id',
            'device_name': 'device_name',
        }
        
        for key, attr in str_properties.items():
            try:
                if hasattr(activity, attr):
                    value = getattr(activity, attr)
                    result[key] = str(value) if value is not None else None
                else:
                    result[key] = None
            except (AttributeError, TypeError, ValueError):
                result[key] = None

        # Optional boolean properties
        bool_properties = {
            'private': 'private',
            'commute': 'commute',
        }
        
        for key, attr in bool_properties.items():
            try:
                if hasattr(activity, attr):
                    value = getattr(activity, attr)
                    result[key] = bool(value) if value is not None else False
                else:
                    result[key] = False
            except (AttributeError, TypeError, ValueError):
                result[key] = False

        return result

    except Exception as e:
        logger.error(f"Error converting activity {activity.id} to dict: {str(e)}")
        # Return minimal dict with basic info
        return {
            'id': int(activity.id),
            'name': str(activity.name),
            'start_date_local': str(activity.start_date_local),
            'type': str(activity.type),
            'distance': 0.0,
            'moving_time': 0,
            'elapsed_time': 0
        }

def parse_args():
    """
    Parse command line arguments
    """
    parser = argparse.ArgumentParser(description='Strava Activities Updater')
    parser.add_argument('--full-refresh', 
                       action='store_true',
                       help='Perform a full refresh of activities instead of incremental update')
    parser.add_argument('--limit', 
                       type=int,
                       default=30,
                       help='Number of activities to fetch (default: 30, max: 200)')
    return parser.parse_args()

def main():
    """
    Main function to update the activities JSON file with the latest Strava activities.
    """
    try:
        # Parse command line arguments
        args = parse_args()
        
        # Verify credentials
        if not all([CLIENT_ID, CLIENT_SECRET]):
            raise ValueError("Missing CLIENT_ID or CLIENT_SECRET in .env file")
        
        logger.info("Starting Strava activities update...")
        if args.full_refresh:
            logger.info("Mode: Full refresh")
        else:
            logger.info("Mode: Incremental update")
        
        # Get valid access token
        access_token = get_token()
        
        logger.info("Initializing Strava client...")
        client = Client(access_token=access_token)
        
        try:
            logger.info(f"Fetching activities from Strava (limit: {args.limit})...")
            strava_activities = list(client.get_activities(limit=args.limit))
            logger.info(f"Successfully fetched {len(strava_activities)} activities")
            
        except Exception as e:
            logger.error(f"Failed to get activities: {str(e)}")
            return
            
        # Process activities
        logger.info("Processing activities...")
        
        if args.full_refresh:
            # For full refresh, we don't load existing activities
            existing_activities = []
            existing_ids = set()
            logger.info("Full refresh: Clearing existing activities")
        else:
            # For incremental update, load existing activities
            existing_activities = load_existing_activities(ACTIVITIES_FILE)
            existing_ids = {activity.get('id') for activity in existing_activities if 'id' in activity}
        
        new_activities = []
        for activity in strava_activities:
            try:
                activity_dict = activity_to_dict(activity)
                if activity_dict['id'] not in existing_ids:
                    new_activities.append(activity_dict)
            except Exception as e:
                logger.warning(f"Failed to process activity {activity.id}: {str(e)}")
                continue
        
        if new_activities or args.full_refresh:
            if args.full_refresh:
                logger.info(f"Saving {len(new_activities)} activities to {ACTIVITIES_FILE}")
                updated_activities = new_activities
            else:
                logger.info(f"Found {len(new_activities)} new activities. Appending to {ACTIVITIES_FILE}")
                updated_activities = existing_activities + new_activities
            
            updated_activities.sort(key=lambda x: x.get('start_date_local', ''))
            save_activities(ACTIVITIES_FILE, updated_activities)
            logger.info("Successfully updated activities file!")
        else:
            logger.info("No new activities found.")
            
    except ValueError as ve:
        logger.error(f"Configuration error: {ve}")
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")

if __name__ == '__main__':
    main()
