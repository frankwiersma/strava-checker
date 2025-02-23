# Strava Activity Checker

A Python script that automatically fetches and stores your Strava activities in a local JSON file. It supports both incremental updates and full refresh of your activity history. The data is stored locally for privacy, but you can optionally submit your activities to [strava.osint-app.com](https://strava.osint-app.com) for analysis.

## Features

- Automatic OAuth2 authentication with Strava
- Token refresh handling
- Incremental activity updates
- Full activity refresh option
- Configurable activity fetch limit
- Local JSON storage for privacy
- Detailed activity data including distance, time, and other metrics
- Optional: Submit to strava.osint-app.com for analysis

## Installation

1. Clone this repository:
```bash
git clone https://github.com/yourusername/strava-checker.git
cd strava-checker
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

## First-Time Setup

1. Create a Strava API Application:
   - Go to https://www.strava.com/settings/api
   - Create a new application
   - Set the "Authorization Callback Domain" to `localhost`
   - Note your `Client ID` and `Client Secret`

2. Configure your credentials:
   - Open `.env` file
   - Replace `YOUR_CLIENT_ID` with your Strava Client ID
   - Replace `YOUR_CLIENT_SECRET` with your Strava Client Secret

3. Run the authorization script:
```bash
python authorize.py
```
   - This will open your browser
   - Log in to Strava if needed
   - Click "Authorize"
   - The script will automatically save your tokens

## Usage

### Basic Usage

To fetch new activities:
```bash
python strava-checker.py
```

This will:
- Automatically refresh tokens if needed
- Fetch the latest 30 activities
- Add any new activities to `activities.json`
- Skip already stored activities

### Advanced Options

Full refresh of all activities:
```bash
python strava-checker.py --full-refresh
```

Fetch a specific number of activities:
```bash
python strava-checker.py --limit 100
```

Combine options:
```bash
python strava-checker.py --full-refresh --limit 200
```

## Privacy & Data Analysis

### Local Storage
All your activity data is stored locally in `activities.json` for privacy. This includes:
- Activity details (distance, time, type)
- Performance metrics
- Route information
- No personal identification beyond activity IDs

### Local Analysis
All analysis is performed locally on your machine using your `activities.json` file:
- Advanced activity statistics and trends
- Pattern detection in your training
- Privacy-preserving data insights
- No data leaves your computer

Your data remains anonymous and you control what you share.

## For New Users

### Understanding the Process

1. **Authentication Flow**:
   - Strava uses OAuth2 for security
   - One-time authorization required
   - Automatic token refresh handling
   - Credentials stored in `.env` file

2. **Activity Storage**:
   - Activities saved in `activities.json`
   - Each activity includes:
     - Basic info (ID, name, type)
     - Distance and times
     - Heart rate data (if available)
     - Speed and elevation data
     - Additional metrics when available

3. **Update Modes**:
   - **Incremental** (default):
     - Only fetches new activities
     - Preserves existing activity data
     - Fastest for regular updates
   
   - **Full Refresh**:
     - Fetches all activities again
     - Replaces existing data
     - Use when you want fresh data

### Common Issues

1. **Authorization Fails**:
   - Verify your Client ID and Secret
   - Check your internet connection
   - Ensure localhost:8000 is available

2. **Missing Activities**:
   - Use `--limit` to fetch more activities
   - Try `--full-refresh` for complete history
   - Check Strava privacy settings

3. **Token Errors**:
   - The script should handle these automatically
   - If persistent, delete tokens from `.env` and reauthorize

### Best Practices

1. **Regular Updates**:
   - Run daily for best results
   - Use cron/scheduler for automation
   - Keep default incremental mode

2. **Data Security**:
   - Backup `activities.json` regularly
   - Keep `.env` secure (contains tokens)
   - Review data before sharing

3. **Rate Limits**:
   - Strava limits API calls
   - Default settings are rate-limit friendly
   - Space out full refreshes