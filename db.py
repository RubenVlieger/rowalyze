"""
Database layer for RowSplit.

SQLite-backed persistence for analytics, sessions, and groups.
"""

import hashlib
import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone


DB_DIR = os.environ.get('ROWSPLIT_DATA_DIR', os.path.join(os.path.dirname(__file__), 'data'))
DB_PATH = os.path.join(DB_DIR, 'rowsplit.db')


def _get_db() -> sqlite3.Connection:
    """Get a database connection."""
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Create tables if they don't exist."""
    conn = _get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_hash TEXT PRIMARY KEY,
            first_seen TEXT NOT NULL,
            last_seen TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            user_hash TEXT,
            activity_id TEXT NOT NULL,
            activity_name TEXT,
            activity_date TEXT,
            interval_desc TEXT,
            params_json TEXT,
            results_json TEXT,
            chart_data_json TEXT,
            summary_json TEXT,
            activity_json TEXT,
            created_at TEXT NOT NULL,
            is_shark INTEGER DEFAULT 0,
            FOREIGN KEY (user_hash) REFERENCES users(user_hash)
        );

        CREATE TABLE IF NOT EXISTS groups (
            id TEXT PRIMARY KEY,
            user_hash TEXT NOT NULL,
            name TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_hash) REFERENCES users(user_hash)
        );

        CREATE TABLE IF NOT EXISTS group_sessions (
            group_id TEXT NOT NULL,
            session_id TEXT NOT NULL,
            added_at TEXT NOT NULL,
            PRIMARY KEY (group_id, session_id),
            FOREIGN KEY (group_id) REFERENCES groups(id),
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        );
    """)
    conn.commit()
    conn.close()


# ─── User Tracking ─────────────────────────────────────────────────

def _hash_athlete(athlete_id) -> str:
    """Privacy-safe hash of Strava athlete ID."""
    return hashlib.sha256(str(athlete_id).encode()).hexdigest()[:16]


def track_user(athlete_id) -> str:
    """Track a unique user. Returns the user_hash."""
    user_hash = _hash_athlete(athlete_id)
    now = datetime.now(timezone.utc).isoformat()
    conn = _get_db()
    conn.execute("""
        INSERT INTO users (user_hash, first_seen, last_seen) VALUES (?, ?, ?)
        ON CONFLICT(user_hash) DO UPDATE SET last_seen = ?
    """, (user_hash, now, now, now))
    conn.commit()
    conn.close()
    return user_hash


# ─── Session Tracking ──────────────────────────────────────────────

def save_session(
    user_hash: str | None,
    activity_id: str,
    activity_name: str,
    activity_date: str,
    interval_desc: str,
    params: dict,
    results: list[dict],
    chart_data: list,
    summary: dict,
    activity: dict,
    is_shark: bool = False,
) -> str:
    """Save an analysis session. Returns session ID."""
    session_id = uuid.uuid4().hex[:12]
    now = datetime.now(timezone.utc).isoformat()
    conn = _get_db()
    conn.execute("""
        INSERT INTO sessions (id, user_hash, activity_id, activity_name, activity_date,
                              interval_desc, params_json, results_json, chart_data_json,
                              summary_json, activity_json, created_at, is_shark)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        session_id, user_hash, activity_id, activity_name, activity_date,
        interval_desc, json.dumps(params), json.dumps(results),
        json.dumps(chart_data), json.dumps(summary), json.dumps(activity),
        now, 1 if is_shark else 0,
    ))
    conn.commit()
    conn.close()
    return session_id


def get_session(session_id: str) -> dict | None:
    """Load a saved session by ID."""
    conn = _get_db()
    row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
    conn.close()
    if not row:
        return None
    return {
        'id': row['id'],
        'user_hash': row['user_hash'],
        'activity_id': row['activity_id'],
        'activity_name': row['activity_name'],
        'activity_date': row['activity_date'],
        'interval_desc': row['interval_desc'],
        'params': json.loads(row['params_json']) if row['params_json'] else {},
        'results': json.loads(row['results_json']) if row['results_json'] else [],
        'chart_data': json.loads(row['chart_data_json']) if row['chart_data_json'] else [],
        'summary': json.loads(row['summary_json']) if row['summary_json'] else {},
        'activity': json.loads(row['activity_json']) if row['activity_json'] else {},
        'created_at': row['created_at'],
        'is_shark': bool(row['is_shark']),
    }


# ─── Analytics / Stats ─────────────────────────────────────────────

def get_stats() -> dict:
    """Get analytics stats for the homepage."""
    conn = _get_db()
    total_sessions = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
    unique_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]

    # Sessions per day since launch
    rows = conn.execute("""
        SELECT DATE(created_at) as day, COUNT(*) as count
        FROM sessions
        GROUP BY DATE(created_at)
        ORDER BY day
    """).fetchall()
    sessions_by_date = [{'date': r['day'], 'count': r['count']} for r in rows]

    conn.close()
    return {
        'total_sessions': total_sessions,
        'unique_users': unique_users,
        'sessions_by_date': sessions_by_date,
    }


# ─── Groups / Playlists ────────────────────────────────────────────

def get_user_groups(user_hash: str) -> list[dict]:
    """List all groups for a user."""
    conn = _get_db()
    rows = conn.execute("""
        SELECT g.*, COUNT(gs.session_id) as session_count,
               MAX(s.created_at) as latest_session
        FROM groups g
        LEFT JOIN group_sessions gs ON g.id = gs.group_id
        LEFT JOIN sessions s ON gs.session_id = s.id
        WHERE g.user_hash = ?
        GROUP BY g.id
        ORDER BY g.created_at DESC
    """, (user_hash,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_group(user_hash: str, name: str) -> str:
    """Create a new group. Returns group ID."""
    group_id = uuid.uuid4().hex[:12]
    now = datetime.now(timezone.utc).isoformat()
    conn = _get_db()
    conn.execute("INSERT INTO groups (id, user_hash, name, created_at) VALUES (?, ?, ?, ?)",
                 (group_id, user_hash, name, now))
    conn.commit()
    conn.close()
    return group_id


def add_session_to_group(group_id: str, session_id: str):
    """Add a session to a group."""
    now = datetime.now(timezone.utc).isoformat()
    conn = _get_db()
    conn.execute("""
        INSERT OR IGNORE INTO group_sessions (group_id, session_id, added_at)
        VALUES (?, ?, ?)
    """, (group_id, session_id, now))
    conn.commit()
    conn.close()


def remove_session_from_group(group_id: str, session_id: str):
    """Remove a session from a group."""
    conn = _get_db()
    conn.execute("DELETE FROM group_sessions WHERE group_id = ? AND session_id = ?",
                 (group_id, session_id))
    conn.commit()
    conn.close()


def get_group(group_id: str) -> dict | None:
    """Get group details."""
    conn = _get_db()
    row = conn.execute("SELECT * FROM groups WHERE id = ?", (group_id,)).fetchone()
    conn.close()
    if not row:
        return None
    return dict(row)


def get_group_sessions(group_id: str) -> list[dict]:
    """List sessions in a group with metadata."""
    conn = _get_db()
    rows = conn.execute("""
        SELECT s.id, s.activity_name, s.activity_date, s.interval_desc,
               s.created_at, s.is_shark,
               json_extract(s.summary_json, '$.avg_split_formatted') as avg_split,
               json_extract(s.summary_json, '$.total_distance_meters') as total_distance,
               json_extract(s.summary_json, '$.avg_cadence') as avg_cadence
        FROM group_sessions gs
        JOIN sessions s ON gs.session_id = s.id
        WHERE gs.group_id = ?
        ORDER BY s.created_at DESC
    """, (group_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_group(group_id: str):
    """Delete a group and its session associations."""
    conn = _get_db()
    conn.execute("DELETE FROM group_sessions WHERE group_id = ?", (group_id,))
    conn.execute("DELETE FROM groups WHERE id = ?", (group_id,))
    conn.commit()
    conn.close()


def get_user_sessions(user_hash: str, limit: int = 50) -> list[dict]:
    """Get recent sessions for a user."""
    conn = _get_db()
    rows = conn.execute("""
        SELECT id, activity_name, activity_date, interval_desc, created_at, is_shark
        FROM sessions WHERE user_hash = ?
        ORDER BY created_at DESC LIMIT ?
    """, (user_hash, limit)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# Initialize on import
init_db()
