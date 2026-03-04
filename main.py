#!/usr/bin/env python3
"""
Strava Rowing Interval Analyzer

Usage:
    python main.py <strava_url_or_activity_id> [options]

Examples:
    python main.py https://www.strava.com/activities/13788623920
    python main.py 13788623920 --interval 300 --count 4 --min-cadence 20
"""

import argparse
import os
import sys

from dotenv import load_dotenv

from analyze import find_fastest_intervals
from strava_client import (
    parse_activity_url,
    get_access_token,
    fetch_activity_details,
    fetch_activity_streams,
)


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Find the fastest rowing intervals in a Strava activity.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py https://www.strava.com/activities/13788623920
  python main.py 13788623920 --interval 300 --count 4
  python main.py https://www.strava.com/activities/13788623920 -i 290 -n 3 -c 24
        """,
    )
    parser.add_argument(
        'activity',
        help='Strava activity URL or activity ID',
    )
    parser.add_argument(
        '-i', '--interval',
        type=float,
        default=290.0,
        help='Interval duration in seconds (default: 290 = 4min50s)',
    )
    parser.add_argument(
        '-n', '--count',
        type=int,
        default=3,
        help='Number of fastest intervals to find (default: 3)',
    )
    parser.add_argument(
        '-c', '--min-cadence',
        type=float,
        default=24.0,
        help='Minimum average cadence threshold (default: 24)',
    )
    parser.add_argument(
        '--client-id',
        default=os.environ.get('STRAVA_CLIENT_ID'),
        help='Strava API client ID (or set STRAVA_CLIENT_ID env var)',
    )
    parser.add_argument(
        '--client-secret',
        default=os.environ.get('STRAVA_CLIENT_SECRET'),
        help='Strava API client secret (or set STRAVA_CLIENT_SECRET env var)',
    )

    args = parser.parse_args()

    # Validate credentials
    if not args.client_id or not args.client_secret:
        print("❌ Error: Strava API credentials required.")
        print("   Set STRAVA_CLIENT_ID and STRAVA_CLIENT_SECRET in .env file")
        print("   or pass --client-id and --client-secret arguments.")
        print("\n   Create an app at: https://www.strava.com/settings/api")
        sys.exit(1)

    # Parse activity URL
    try:
        activity_id = parse_activity_url(args.activity)
    except ValueError as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

    # Authenticate
    try:
        access_token = get_access_token(args.client_id, args.client_secret)
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        sys.exit(1)

    # Fetch activity details
    print(f"📡 Fetching activity {activity_id}...")
    try:
        details = fetch_activity_details(access_token, activity_id)
        activity_name = details.get('name', 'Unknown')
        start_date = details.get('start_date_local', 'Unknown')
        activity_type = details.get('type', 'Unknown')
        print(f"   Activity: \"{activity_name}\" ({activity_type})")
        print(f"   Date: {start_date}")
    except Exception as e:
        print(f"⚠️  Could not fetch activity details: {e}")
        activity_name = "Unknown"

    # Fetch streams
    print(f"📊 Fetching stream data...")
    try:
        streams = fetch_activity_streams(access_token, activity_id)
    except Exception as e:
        print(f"❌ Failed to fetch streams: {e}")
        sys.exit(1)

    # Validate stream data
    required = ['time', 'velocity_smooth', 'cadence', 'distance']
    missing = [k for k in required if k not in streams]
    if missing:
        print(f"❌ Missing stream data: {', '.join(missing)}")
        print(f"   Available streams: {', '.join(streams.keys())}")
        sys.exit(1)

    # Run analysis  
    interval_mins = int(args.interval) // 60
    interval_secs = int(args.interval) % 60
    interval_str = f"{interval_mins}m{interval_secs:02d}s" if interval_secs else f"{interval_mins}m"

    print(f"\n🔍 Finding {args.count} fastest {interval_str} intervals (min cadence: {args.min_cadence})...\n")

    results = find_fastest_intervals(
        time=streams['time'],
        velocity_smooth=streams['velocity_smooth'],
        cadence=streams['cadence'],
        distance=streams['distance'],
        interval_duration=args.interval,
        num_intervals=args.count,
        min_cadence=args.min_cadence,
    )

    if not results:
        print("   No intervals found matching the criteria.")
        print("   Try lowering --min-cadence or adjusting --interval duration.")
        sys.exit(0)

    # Print results
    print(f"{'─' * 70}")
    for result in results:
        print(f"  {result}")
    print(f"{'─' * 70}")

    # Summary
    if len(results) > 1:
        avg_speed = sum(r.avg_speed_sec_per_500m for r in results) / len(results)
        avg_cad = sum(r.avg_cadence for r in results) / len(results)
        from analyze import format_speed
        print(f"\n  Average across {len(results)} intervals: "
              f"{format_speed(avg_speed)}/500m | Cadence: {avg_cad:.1f}")

    print()


if __name__ == '__main__':
    main()
