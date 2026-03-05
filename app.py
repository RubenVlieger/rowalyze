"""
Rowalyse — Strava Rowing Session Analyser

Flask web application that lets users analyze their Strava rowing
activities, finding the fastest intervals with 500m sub-splits.
"""

import hashlib
import json
import os
import time as time_module
from datetime import datetime, timezone

import requests as http_requests

from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, jsonify, abort,
)
from dotenv import load_dotenv

from analyze import find_fastest_intervals, get_activity_summary, format_speed
from strava_client import (
    parse_activity_url,
    get_auth_url,
    exchange_code,
    get_valid_token,
    fetch_activity_details,
    fetch_activity_streams,
)
import db

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-change-me')

CLIENT_ID = os.environ.get('STRAVA_CLIENT_ID', '')
CLIENT_SECRET = os.environ.get('STRAVA_CLIENT_SECRET', '')
SERVER_URL = os.environ.get('SERVER_URL', 'http://localhost:5000')

# Simple in-memory cache for API responses
_cache = {}
CACHE_TTL = 3600

# Nijmegen coordinates for wind data
NIJMEGEN_LAT = 51.8426
NIJMEGEN_LON = 5.8526

WIND_DIRECTIONS = [
    'N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE',
    'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW',
]


def _wind_direction_label(deg: float) -> str:
    """Convert wind direction degrees to compass label."""
    idx = round(deg / 22.5) % 16
    return WIND_DIRECTIONS[idx]


def _fetch_wind_data(date_str: str) -> dict | None:
    """
    Fetch wind data for Nijmegen on a given date from Open-Meteo.
    Returns {'speed_kmh': float, 'direction_deg': float, 'direction_label': str} or None.
    """
    if not date_str or len(date_str) < 10:
        return None
    date_str = date_str[:10]  # YYYY-MM-DD
    try:
        resp = http_requests.get(
            'https://api.open-meteo.com/v1/forecast',
            params={
                'latitude': NIJMEGEN_LAT,
                'longitude': NIJMEGEN_LON,
                'daily': 'wind_speed_10m_max,wind_direction_10m_dominant',
                'start_date': date_str,
                'end_date': date_str,
                'timezone': 'Europe/Amsterdam',
            },
            timeout=5,
        )
        resp.raise_for_status()
        data = resp.json()
        daily = data.get('daily', {})
        speed = daily.get('wind_speed_10m_max', [None])[0]
        direction = daily.get('wind_direction_10m_dominant', [None])[0]
        if speed is not None and direction is not None:
            return {
                'speed_kmh': round(speed, 1),
                'direction_deg': round(direction),
                'direction_label': _wind_direction_label(direction),
            }
    except Exception:
        pass
    return None


def _get_redirect_uri():
    return f"{SERVER_URL}/auth/callback"


def _is_authenticated():
    return 'strava_tokens' in session and session['strava_tokens'].get('access_token')


def _get_access_token():
    tokens = session.get('strava_tokens')
    if not tokens:
        return None
    access_token, updated = get_valid_token(tokens, CLIENT_ID, CLIENT_SECRET)
    if updated != tokens:
        session['strava_tokens'] = updated
    return access_token


def _get_user_hash():
    return session.get('user_hash')


def _cache_key(activity_id, params):
    raw = f"{activity_id}:{json.dumps(params, sort_keys=True)}"
    return hashlib.md5(raw.encode()).hexdigest()


def _run_analysis(streams, interval_mode, interval_duration, interval_distance,
                  num_intervals, min_cadence):
    """Run the analysis engine and return (results, chart_data, summary, overall_avg, interval_desc)."""
    results = find_fastest_intervals(
        time=streams['time'],
        velocity_smooth=streams['velocity_smooth'],
        cadence=streams['cadence'],
        distance=streams['distance'],
        interval_duration=interval_duration,
        interval_distance=interval_distance,
        num_intervals=num_intervals,
        min_cadence=min_cadence,
    )

    summary = get_activity_summary(
        streams['time'], streams['distance'],
        streams['velocity_smooth'], streams['cadence'],
    )

    # Build interval description
    if interval_mode == 'time':
        mins = int(interval_duration) // 60
        secs = int(interval_duration) % 60
        interval_desc = f"{mins}m{secs:02d}s" if secs else f"{mins}m"
    else:
        interval_desc = f"{int(interval_distance)}m"

    # Chart data
    chart_data = []
    for r in results:
        points = []
        start_i = r.start_idx
        end_i = r.end_idx
        base_dist = streams['distance'][start_i]
        for i in range(start_i, min(end_i + 1, len(streams['time']))):
            v = streams['velocity_smooth'][i]
            split_500 = round(500.0 / v, 1) if v > 0.1 else None
            point = {
                'distance': round(streams['distance'][i] - base_dist, 1),
                'split': split_500,
                'cadence': streams['cadence'][i],
            }
            # Add heartrate if available
            if 'heartrate' in streams and i < len(streams['heartrate']):
                point['heartrate'] = streams['heartrate'][i]
            points.append(point)
        chart_data.append({
            'label': f'Interval {r.rank}',
            'points': points,
        })

    # Overall average
    if results:
        avg_speed = sum(r.avg_speed_sec_per_500m for r in results) / len(results)
        avg_cad = sum(r.avg_cadence for r in results) / len(results)
        overall_avg = {
            'speed': format_speed(avg_speed),
            'speed_raw': round(avg_speed, 1),
            'cadence': round(avg_cad, 1),
        }
    else:
        overall_avg = None

    return results, chart_data, summary, overall_avg, interval_desc


# ─── Routes ─────────────────────────────────────────────────────────

@app.route('/')
def index():
    authenticated = _is_authenticated()
    athlete = session.get('athlete_name', '')
    stats = db.get_stats()
    groups = []
    if authenticated and _get_user_hash():
        groups = db.get_user_groups(_get_user_hash())
    return render_template('index.html',
                           authenticated=authenticated,
                           athlete_name=athlete,
                           stats=stats,
                           groups=groups)


@app.route('/auth/strava')
def auth_strava():
    if not CLIENT_ID:
        flash('Strava API credentials not configured on the server.', 'error')
        return redirect(url_for('index'))
    auth_url = get_auth_url(CLIENT_ID, _get_redirect_uri())
    return redirect(auth_url)


@app.route('/auth/callback')
def auth_callback():
    code = request.args.get('code')
    error = request.args.get('error')

    if error:
        flash(f'Strava authorization failed: {error}', 'error')
        return redirect(url_for('index'))

    if not code:
        flash('No authorization code received.', 'error')
        return redirect(url_for('index'))

    try:
        token_data = exchange_code(CLIENT_ID, CLIENT_SECRET, code)
        session['strava_tokens'] = token_data

        athlete = token_data.get('athlete', {})
        name = f"{athlete.get('firstname', '')} {athlete.get('lastname', '')}".strip()
        session['athlete_name'] = name or 'Athlete'

        # Track user (privacy-safe)
        athlete_id = athlete.get('id', name)
        user_hash = db.track_user(athlete_id)
        session['user_hash'] = user_hash

        flash(f'Connected as {session["athlete_name"]}!', 'success')
    except Exception as e:
        flash(f'Failed to complete authorization: {e}', 'error')

    return redirect(url_for('index'))


@app.route('/auth/logout')
def logout():
    session.clear()
    flash('Disconnected from Strava.', 'info')
    return redirect(url_for('index'))


@app.route('/analyze', methods=['POST'])
def analyze():
    if not _is_authenticated():
        flash('Please connect with Strava first.', 'error')
        return redirect(url_for('index'))

    activity_url = request.form.get('activity_url', '').strip()
    interval_mode = request.form.get('interval_mode', 'time')
    num_intervals = int(request.form.get('num_intervals', 3))
    min_cadence = float(request.form.get('min_cadence', 24))

    if not activity_url:
        flash('Please enter a Strava activity URL.', 'error')
        return redirect(url_for('index'))

    try:
        activity_id = parse_activity_url(activity_url)
    except ValueError as e:
        flash(str(e), 'error')
        return redirect(url_for('index'))

    interval_duration = None
    interval_distance = None
    if interval_mode == 'time':
        minutes = int(request.form.get('interval_minutes', 4))
        seconds = int(request.form.get('interval_seconds', 50))
        interval_duration = minutes * 60 + seconds
    else:
        interval_distance = float(request.form.get('interval_distance_m', 2000))

    # Fetch from Strava API
    try:
        access_token = _get_access_token()
        if not access_token:
            flash('Strava session expired. Please reconnect.', 'error')
            return redirect(url_for('index'))

        details = fetch_activity_details(access_token, activity_id)
        streams = fetch_activity_streams(access_token, activity_id)
    except Exception as e:
        flash(f'Failed to fetch activity data: {e}', 'error')
        return redirect(url_for('index'))

    required = ['time', 'velocity_smooth', 'cadence', 'distance']
    missing = [k for k in required if k not in streams]
    if missing:
        flash(f'Activity missing required data: {", ".join(missing)}.', 'error')
        return redirect(url_for('index'))

    results, chart_data, summary, overall_avg, interval_desc = _run_analysis(
        streams, interval_mode, interval_duration, interval_distance,
        num_intervals, min_cadence,
    )

    activity_data = {
        'id': activity_id,
        'name': details.get('name', 'Unknown Activity'),
        'date': details.get('start_date_local', '')[:10],
        'type': details.get('type', 'Rowing'),
        'url': f'https://www.strava.com/activities/{activity_id}',
    }

    # Fetch wind data for activity date
    wind = _fetch_wind_data(activity_data['date'])

    results_dicts = [r.to_dict() for r in results]

    # Save session to DB
    default_name = f"{num_intervals}×{interval_desc}@{int(min_cadence)}"
    session_id = db.save_session(
        user_hash=_get_user_hash(),
        activity_id=activity_id,
        activity_name=activity_data['name'],
        activity_date=activity_data['date'],
        interval_desc=default_name,
        params={
            'mode': interval_mode,
            'duration': interval_duration,
            'distance': interval_distance,
            'count': num_intervals,
            'min_cadence': min_cadence,
        },
        results=results_dicts,
        chart_data=chart_data,
        summary=summary,
        activity=activity_data,
        wind_speed_kmh=wind['speed_kmh'] if wind else None,
        wind_direction_deg=wind['direction_deg'] if wind else None,
    )

    return redirect(url_for('view_results', session_id=session_id))


@app.route('/results/<session_id>')
def view_results(session_id):
    """View saved analysis results."""
    sess = db.get_session(session_id)
    if not sess:
        flash('Session not found.', 'error')
        return redirect(url_for('index'))

    # Get user's groups for the "save to group" dropdown
    groups = []
    if _is_authenticated() and _get_user_hash():
        groups = db.get_user_groups(_get_user_hash())

    has_heartrate = False
    if sess['chart_data']:
        for interval in sess['chart_data']:
            if interval.get('points') and any('heartrate' in p for p in interval['points']):
                has_heartrate = True
                break

    share_url = f"{SERVER_URL}/share/{session_id}"

    # Wind data
    wind = None
    if sess.get('wind_speed_kmh') is not None:
        wind = {
            'speed_kmh': sess['wind_speed_kmh'],
            'direction_deg': sess['wind_direction_deg'],
            'direction_label': _wind_direction_label(sess['wind_direction_deg']),
        }

    # Activity ID for Strava embed
    activity_id = sess['activity'].get('id', '')

    return render_template('results.html',
                           activity=sess['activity'],
                           summary=sess['summary'],
                           results=sess['results'],
                           interval_desc=sess['interval_desc'],
                           interval_mode=sess['params'].get('mode', 'time'),
                           num_intervals=sess['params'].get('count', 3),
                           min_cadence=sess['params'].get('min_cadence', 24),
                           chart_data=sess['chart_data'],
                           overall_avg=_compute_overall_avg(sess['results']),
                           session_id=session_id,
                           groups=groups,
                           share_url=share_url,
                           has_heartrate=has_heartrate,
                           is_owner=(_get_user_hash() == sess.get('user_hash')),
                           wind=wind,
                           activity_id=activity_id)


@app.route('/share/<session_id>')
def share_results(session_id):
    """Public shareable link — no auth required."""
    sess = db.get_session(session_id)
    if not sess:
        abort(404)

    has_heartrate = False
    if sess['chart_data']:
        for interval in sess['chart_data']:
            if interval.get('points') and any('heartrate' in p for p in interval['points']):
                has_heartrate = True
                break

    share_url = f"{SERVER_URL}/share/{session_id}"

    # Wind data
    wind = None
    if sess.get('wind_speed_kmh') is not None:
        wind = {
            'speed_kmh': sess['wind_speed_kmh'],
            'direction_deg': sess['wind_direction_deg'],
            'direction_label': _wind_direction_label(sess['wind_direction_deg']),
        }

    activity_id = sess['activity'].get('id', '')

    return render_template('results.html',
                           activity=sess['activity'],
                           summary=sess['summary'],
                           results=sess['results'],
                           interval_desc=sess['interval_desc'],
                           interval_mode=sess['params'].get('mode', 'time'),
                           num_intervals=sess['params'].get('count', 3),
                           min_cadence=sess['params'].get('min_cadence', 24),
                           chart_data=sess['chart_data'],
                           overall_avg=_compute_overall_avg(sess['results']),
                           session_id=session_id,
                           groups=[],
                           share_url=share_url,
                           has_heartrate=has_heartrate,
                           is_owner=False,
                           is_shared=True,
                           wind=wind,
                           activity_id=activity_id)


def _compute_overall_avg(results):
    if not results:
        return None
    avg_speed = sum(r['avg_speed_sec_per_500m'] for r in results) / len(results)
    avg_cad = sum(r['avg_cadence'] for r in results) / len(results)
    return {
        'speed': format_speed(avg_speed),
        'speed_raw': round(avg_speed, 1),
        'cadence': round(avg_cad, 1),
    }


# ─── Groups / Playlists ────────────────────────────────────────────

@app.route('/groups')
def groups_page():
    if not _is_authenticated():
        flash('Please connect with Strava first.', 'error')
        return redirect(url_for('index'))

    user_hash = _get_user_hash()
    groups = db.get_user_groups(user_hash)
    return render_template('groups.html',
                           authenticated=True,
                           athlete_name=session.get('athlete_name', ''),
                           groups=groups)


@app.route('/groups/create', methods=['POST'])
def create_group():
    if not _is_authenticated():
        return jsonify({'error': 'Not authenticated'}), 401

    name = request.form.get('name', '').strip()
    if not name:
        flash('Group name required.', 'error')
        return redirect(url_for('groups_page'))

    group_id = db.create_group(_get_user_hash(), name)
    flash(f'Created group "{name}".', 'success')

    # If came from results page, redirect back
    redirect_to = request.form.get('redirect_to')
    if redirect_to:
        return redirect(redirect_to)
    return redirect(url_for('groups_page'))


@app.route('/groups/<group_id>')
def group_detail(group_id):
    if not _is_authenticated():
        flash('Please connect with Strava first.', 'error')
        return redirect(url_for('index'))

    group = db.get_group(group_id)
    if not group:
        flash('Group not found.', 'error')
        return redirect(url_for('groups_page'))

    sessions = db.get_group_sessions(group_id)
    return render_template('group_detail.html',
                           authenticated=True,
                           athlete_name=session.get('athlete_name', ''),
                           group=group,
                           sessions=sessions)


@app.route('/groups/<group_id>/add', methods=['POST'])
def add_to_group(group_id):
    if not _is_authenticated():
        return jsonify({'error': 'Not authenticated'}), 401

    session_id = request.form.get('session_id')
    if session_id:
        db.add_session_to_group(group_id, session_id)
        flash('Session added to group!', 'success')

    redirect_to = request.form.get('redirect_to', url_for('groups_page'))
    return redirect(redirect_to)


@app.route('/groups/<group_id>/remove', methods=['POST'])
def remove_from_group(group_id):
    if not _is_authenticated():
        return jsonify({'error': 'Not authenticated'}), 401

    session_id = request.form.get('session_id')
    if session_id:
        db.remove_session_from_group(group_id, session_id)
        flash('Session removed from group.', 'info')

    return redirect(url_for('group_detail', group_id=group_id))


@app.route('/groups/<group_id>/delete', methods=['POST'])
def delete_group(group_id):
    if not _is_authenticated():
        return jsonify({'error': 'Not authenticated'}), 401
    db.delete_group(group_id)
    flash('Group deleted.', 'info')
    return redirect(url_for('groups_page'))


# ─── Shark Mode ─────────────────────────────────────────────────────

@app.route('/api/shark', methods=['POST'])
def shark_analyze():
    """Receive client-side stream data and run analysis."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data received'}), 400

    streams = data.get('streams', {})
    params = data.get('params', {})
    activity_info = data.get('activity', {})

    # Unwrap nested {data: [...]} objects (from key_by_type=true format)
    if isinstance(streams, dict):
        for key in list(streams.keys()):
            val = streams[key]
            if isinstance(val, dict) and 'data' in val:
                streams[key] = val['data']

    required = ['time', 'velocity_smooth', 'cadence', 'distance']
    missing = [k for k in required if k not in streams]
    if missing:
        return jsonify({'error': f'Missing streams: {", ".join(missing)}'}), 400

    interval_mode = params.get('mode', 'time')
    interval_duration = params.get('duration')
    interval_distance = params.get('distance')
    num_intervals = params.get('count', 3)
    min_cadence = params.get('min_cadence', 24)

    if interval_mode == 'time' and interval_duration is None:
        interval_duration = 290
    if interval_mode == 'distance' and interval_distance is None:
        interval_distance = 2000

    try:
        results, chart_data, summary, overall_avg, interval_desc = _run_analysis(
            streams, interval_mode, interval_duration, interval_distance,
            num_intervals, min_cadence,
        )
    except Exception as e:
        return jsonify({'error': f'Analysis failed: {e}'}), 500

    activity_data = {
        'id': activity_info.get('id', 'shark'),
        'name': activity_info.get('name', '🦈 Shark Activity'),
        'date': activity_info.get('date', ''),
        'type': 'Rowing',
        'url': activity_info.get('url', '#'),
    }

    # Fetch wind data
    wind_date = activity_data['date'] or datetime.now(timezone.utc).strftime('%Y-%m-%d')
    wind = _fetch_wind_data(wind_date)

    results_dicts = [r.to_dict() for r in results]
    default_name = f"{num_intervals}×{interval_desc}@{int(min_cadence)}"

    user_hash = _get_user_hash() if _is_authenticated() else None

    session_id = db.save_session(
        user_hash=user_hash,
        activity_id=activity_data['id'],
        activity_name=activity_data['name'],
        activity_date=activity_data['date'],
        interval_desc=default_name,
        params={'mode': interval_mode, 'duration': interval_duration,
                'distance': interval_distance, 'count': num_intervals,
                'min_cadence': min_cadence},
        results=results_dicts,
        chart_data=chart_data,
        summary=summary,
        activity=activity_data,
        is_shark=True,
        wind_speed_kmh=wind['speed_kmh'] if wind else None,
        wind_direction_deg=wind['direction_deg'] if wind else None,
    )

    return jsonify({'session_id': session_id, 'url': url_for('view_results', session_id=session_id)})


@app.route('/shark/receive', methods=['POST'])
def shark_receive():
    """Receive stream data from the bookmarklet (form POST from strava.com)."""
    raw_streams = request.form.get('streams', '')
    activity_url = request.form.get('activity_url', '')
    activity_name = request.form.get('activity_name', '🦈 Shark Activity')

    # Read interval params from form (set by bookmarklet)
    interval_mode = request.form.get('interval_mode', 'time')
    try:
        num_intervals = int(request.form.get('num_intervals', 3))
    except (ValueError, TypeError):
        num_intervals = 3
    try:
        min_cadence = float(request.form.get('min_cadence', 24))
    except (ValueError, TypeError):
        min_cadence = 24

    interval_duration = None
    interval_distance = None
    if interval_mode == 'time':
        try:
            minutes = int(request.form.get('interval_minutes', 4))
            seconds = int(request.form.get('interval_seconds', 50))
            interval_duration = minutes * 60 + seconds
        except (ValueError, TypeError):
            interval_duration = 290
    else:
        try:
            interval_distance = float(request.form.get('interval_distance', 2000))
        except (ValueError, TypeError):
            interval_distance = 2000

    if not raw_streams:
        flash('No stream data received from bookmarklet.', 'error')
        return redirect(url_for('index'))

    try:
        streams = json.loads(raw_streams)
    except json.JSONDecodeError:
        flash('Invalid JSON data from bookmarklet.', 'error')
        return redirect(url_for('index'))

    # Parse streams (handle both list-of-objects and dict formats)
    if isinstance(streams, list):
        # Format: [{"type": "time", "data": [...]}, ...]
        parsed = {}
        for s in streams:
            if isinstance(s, dict) and 'type' in s and 'data' in s:
                parsed[s['type']] = s['data']
        streams = parsed
    elif isinstance(streams, dict):
        # Format from key_by_type=true: {"time": {"data": [...], ...}, ...}
        for key in list(streams.keys()):
            val = streams[key]
            if isinstance(val, dict) and 'data' in val:
                streams[key] = val['data']

    required = ['time', 'velocity_smooth', 'cadence', 'distance']
    missing = [k for k in required if k not in streams]
    if missing:
        flash(f'Missing required streams: {", ".join(missing)}.', 'error')
        return redirect(url_for('index'))

    try:
        results, chart_data, summary, overall_avg, interval_desc = _run_analysis(
            streams, interval_mode, interval_duration, interval_distance,
            num_intervals, min_cadence,
        )
    except Exception as e:
        flash(f'Analysis failed: {e}', 'error')
        return redirect(url_for('index'))

    # Extract activity ID from URL
    activity_id = 'shark'
    try:
        from strava_client import parse_activity_url
        activity_id = parse_activity_url(activity_url)
    except Exception:
        pass

    # Use today's date for wind (shark mode doesn't always have activity date)
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    wind = _fetch_wind_data(today)

    activity_data = {
        'id': activity_id,
        'name': activity_name,
        'date': today,
        'type': 'Rowing',
        'url': activity_url or '#',
    }

    results_dicts = [r.to_dict() for r in results]
    default_name = f"{num_intervals}×{interval_desc}@{int(min_cadence)}"

    user_hash = _get_user_hash() if _is_authenticated() else None

    session_id = db.save_session(
        user_hash=user_hash,
        activity_id=activity_data['id'],
        activity_name=activity_data['name'],
        activity_date=today,
        interval_desc=default_name,
        params={'mode': interval_mode, 'duration': interval_duration,
                'distance': interval_distance, 'count': num_intervals,
                'min_cadence': min_cadence},
        results=results_dicts,
        chart_data=chart_data,
        summary=summary,
        activity=activity_data,
        is_shark=True,
        wind_speed_kmh=wind['speed_kmh'] if wind else None,
        wind_direction_deg=wind['direction_deg'] if wind else None,
    )

    return redirect(url_for('view_results', session_id=session_id))


@app.route('/api/stats')
def api_stats():
    """JSON stats for the homepage chart."""
    return jsonify(db.get_stats())


@app.route('/privacy')
def privacy():
    """Privacy policy page."""
    return render_template('privacy.html',
                           authenticated=_is_authenticated(),
                           athlete_name=session.get('athlete_name', ''))


if __name__ == '__main__':
    app.run(debug=True, port=5000)

