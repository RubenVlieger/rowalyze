"""
Strava API client for fetching activity data.

Handles OAuth2 authentication for both CLI and web modes,
and stream data retrieval.
"""

import json
import os
import re
import time as time_module
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, urlencode

import requests


TOKEN_FILE = os.path.expanduser("~/.strava_tokens.json")
STRAVA_AUTH_URL = "https://www.strava.com/oauth/authorize"
STRAVA_TOKEN_URL = "https://www.strava.com/oauth/token"
STRAVA_API_BASE = "https://www.strava.com/api/v3"
REDIRECT_PORT = 8642
REDIRECT_URI = f"http://localhost:{REDIRECT_PORT}/callback"


def parse_activity_url(url: str) -> str:
    """
    Extract activity ID from a Strava activity URL.

    Supports:
        https://www.strava.com/activities/13788623920
        https://strava.com/activities/13788623920
        13788623920 (just the ID)
    """
    if re.match(r'^\d+$', url.strip()):
        return url.strip()
    match = re.search(r'strava\.com/activities/(\d+)', url)
    if match:
        return match.group(1)
    raise ValueError(f"Could not extract activity ID from: {url}")


# ─── Web OAuth2 Flow ────────────────────────────────────────────────

def get_auth_url(client_id: str, redirect_uri: str) -> str:
    """Generate Strava OAuth authorization URL for web flow."""
    params = urlencode({
        'client_id': client_id,
        'redirect_uri': redirect_uri,
        'response_type': 'code',
        'scope': 'activity:read_all',
        'approval_prompt': 'force',
    })
    return f"{STRAVA_AUTH_URL}?{params}"


def exchange_code(client_id: str, client_secret: str, code: str) -> dict:
    """Exchange authorization code for access + refresh tokens."""
    resp = requests.post(STRAVA_TOKEN_URL, data={
        'client_id': client_id,
        'client_secret': client_secret,
        'code': code,
        'grant_type': 'authorization_code',
    })
    resp.raise_for_status()
    return resp.json()


def refresh_token(client_id: str, client_secret: str, refresh_tok: str) -> dict:
    """Refresh an expired access token."""
    resp = requests.post(STRAVA_TOKEN_URL, data={
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': 'refresh_token',
        'refresh_token': refresh_tok,
    })
    resp.raise_for_status()
    return resp.json()


def get_valid_token(token_data: dict, client_id: str, client_secret: str) -> tuple[str, dict]:
    """
    Ensure we have a valid access token, refreshing if needed.

    Returns (access_token, updated_token_data).
    """
    expires_at = token_data.get('expires_at', 0)
    if time_module.time() < expires_at - 60:
        return token_data['access_token'], token_data

    # Need to refresh
    new_tokens = refresh_token(client_id, client_secret, token_data['refresh_token'])
    return new_tokens['access_token'], new_tokens


# ─── CLI OAuth2 Flow ────────────────────────────────────────────────

def _load_tokens() -> dict | None:
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'r') as f:
            return json.load(f)
    return None


def _save_tokens(tokens: dict):
    with open(TOKEN_FILE, 'w') as f:
        json.dump(tokens, f, indent=2)


class _OAuthCallbackHandler(BaseHTTPRequestHandler):
    authorization_code = None

    def do_GET(self):
        query = parse_qs(urlparse(self.path).query)
        if 'code' in query:
            _OAuthCallbackHandler.authorization_code = query['code'][0]
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(b'<html><body style="font-family:sans-serif;text-align:center;padding:50px;">'
                             b'<h1>&#x2705; Authorization successful!</h1>'
                             b'<p>You can close this window.</p></body></html>')
        else:
            self.send_response(400)
            self.end_headers()

    def log_message(self, format, *args):
        pass


def get_access_token(client_id: str, client_secret: str) -> str:
    """Get a valid access token for CLI use."""
    tokens = _load_tokens()

    if tokens:
        expires_at = tokens.get('expires_at', 0)
        if time_module.time() < expires_at - 60:
            return tokens['access_token']
        refresh_tok = tokens.get('refresh_token')
        if refresh_tok:
            try:
                tokens = refresh_token(client_id, client_secret, refresh_tok)
                _save_tokens(tokens)
                return tokens['access_token']
            except Exception:
                pass

    params = urlencode({
        'client_id': client_id,
        'redirect_uri': REDIRECT_URI,
        'response_type': 'code',
        'scope': 'activity:read_all',
        'approval_prompt': 'auto',
    })
    auth_url = f"{STRAVA_AUTH_URL}?{params}"
    print(f"\n🔐 Opening browser for Strava authorization...")
    webbrowser.open(auth_url)

    server = HTTPServer(('localhost', REDIRECT_PORT), _OAuthCallbackHandler)
    server.timeout = 120
    while _OAuthCallbackHandler.authorization_code is None:
        server.handle_request()

    code = _OAuthCallbackHandler.authorization_code
    _OAuthCallbackHandler.authorization_code = None
    server.server_close()

    resp = requests.post(STRAVA_TOKEN_URL, data={
        'client_id': client_id,
        'client_secret': client_secret,
        'code': code,
        'grant_type': 'authorization_code',
    })
    resp.raise_for_status()
    tokens = resp.json()
    _save_tokens(tokens)
    return tokens['access_token']


# ─── API Calls ──────────────────────────────────────────────────────
def fetch_recent_activities(access_token: str, per_page: int = 50) -> list[dict]: # Bumped to 50
    """Fetch recent activities from Strava, returning rowing-type activities."""
    resp = requests.get(
        f"{STRAVA_API_BASE}/athlete/activities",
        headers={'Authorization': f'Bearer {access_token}'},
        params={'per_page': per_page, 'page': 1},
    )
    resp.raise_for_status()
    activities = resp.json()
    
    # Filter to rowing activities and return compact data
    result =[]
    from datetime import datetime
    for a in activities:
        if a.get('type') in ('Rowing', 'VirtualRowing') or a.get('sport_type') in ('Rowing', 'VirtualRowing'):
            raw_date = (a.get('start_date_local', '') or '')[:10]
            try:
                dt = datetime.fromisoformat(raw_date)
                formatted_date = dt.strftime('%A, %b %d, %Y')
            except Exception:
                formatted_date = raw_date
            result.append({
                'id': a['id'],
                'name': a.get('name', 'Untitled'),
                'distance': round(a.get('distance', 0)),
                'date': formatted_date,
                'url': f"https://www.strava.com/activities/{a['id']}",
            })
    return result[:10]  # Return max 15


def fetch_activity_details(access_token: str, activity_id: str) -> dict:
    """Fetch activity metadata."""
    resp = requests.get(
        f"{STRAVA_API_BASE}/activities/{activity_id}",
        headers={'Authorization': f'Bearer {access_token}'},
    )
    resp.raise_for_status()
    return resp.json()


def fetch_activity_streams(access_token: str, activity_id: str) -> dict:
    """
    Fetch activity stream data (time, velocity, cadence, distance).

    Returns dict with keys: time, velocity_smooth, cadence, distance.
    """
    stream_types = 'time,velocity_smooth,cadence,distance,heartrate'
    resp = requests.get(
        f"{STRAVA_API_BASE}/activities/{activity_id}/streams",
        headers={'Authorization': f'Bearer {access_token}'},
        params={
            'keys': stream_types,
            'key_by_type': 'true',
        },
    )
    resp.raise_for_status()
    data = resp.json()

    # API returns a list of stream objects
    if isinstance(data, list):
        streams = {}
        for stream in data:
            streams[stream['type']] = stream['data']
        return streams

    # If keyed by type
    result = {}
    for key in ['time', 'velocity_smooth', 'cadence', 'distance', 'heartrate']:
        if key in data:
            if isinstance(data[key], dict) and 'data' in data[key]:
                result[key] = data[key]['data']
            else:
                result[key] = data[key]
    return result
