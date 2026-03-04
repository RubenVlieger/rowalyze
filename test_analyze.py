#!/usr/bin/env python3
"""
Test the analysis engine using existing sample stream data.

This script loads the stream data from the .txt files captured from
Strava's network requests and runs the interval analysis on them.
"""

import json
import sys
import os

# Add parent dir to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from analyze import find_fastest_intervals, format_time, format_speed


def load_stream_file(filepath: str) -> dict:
    """Load a stream JSON file and return the parsed dict."""
    with open(filepath, 'r') as f:
        return json.load(f)


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Load stream2.txt which has all the data we need:
    # velocity_smooth, cadence, distance, time
    print("📂 Loading stream data from stream2.txt...")
    stream2 = load_stream_file(os.path.join(script_dir, 'stream2.txt'))
    
    # Extract arrays
    time_data = stream2['time']
    velocity_data = stream2['velocity_smooth']
    cadence_data = stream2['cadence']
    distance_data = stream2['distance']
    
    print(f"   Data points: {len(time_data)}")
    print(f"   Total time: {format_time(time_data[-1])} ({time_data[-1]:.0f}s)")
    print(f"   Total distance: {distance_data[-1]:,.0f}m")
    
    # Print cadence stats to understand the data
    nonzero_cadence = [c for c in cadence_data if c > 0]
    if nonzero_cadence:
        print(f"   Cadence range (non-zero): {min(nonzero_cadence)} - {max(nonzero_cadence)}")
        print(f"   Cadence median (non-zero): {sorted(nonzero_cadence)[len(nonzero_cadence)//2]}")
    
    # Run analysis with default parameters
    print(f"\n🔍 Finding 3 fastest 4m50s intervals (min cadence: 24)...\n")
    
    results = find_fastest_intervals(
        time=time_data,
        velocity_smooth=velocity_data,
        cadence=cadence_data,
        distance=distance_data,
        interval_duration=290.0,
        num_intervals=3,
        min_cadence=24.0,
    )
    
    if not results:
        print("   ⚠️  No intervals found with min cadence 24.")
        print("   Trying with lower cadence threshold...")
        
        # Try with much lower threshold to debug
        for threshold in [20, 15, 10, 5, 1, 0]:
            results = find_fastest_intervals(
                time=time_data,
                velocity_smooth=velocity_data,
                cadence=cadence_data,
                distance=distance_data,
                interval_duration=290.0,
                num_intervals=3,
                min_cadence=threshold,
            )
            if results:
                print(f"   Found intervals with min cadence >= {threshold}")
                break
    
    print(f"{'─' * 70}")
    for result in results:
        print(f"  {result}")
    print(f"{'─' * 70}")
    
    if len(results) > 1:
        avg_speed = sum(r.avg_speed_sec_per_500m for r in results) / len(results)
        avg_cad = sum(r.avg_cadence for r in results) / len(results)
        print(f"\n  Average across {len(results)} intervals: "
              f"{format_speed(avg_speed)}/500m | Cadence: {avg_cad:.1f}")
    
    # Validation checks
    print("\n✅ Validation:")
    all_pass = True
    
    for r in results:
        if r.avg_speed_sec_per_500m <= 0:
            print(f"   ❌ Speed should be > 0: {r.avg_speed_sec_per_500m}")
            all_pass = False
        
        if r.distance_meters <= 0:
            print(f"   ❌ Distance should be > 0: {r.distance_meters}")
            all_pass = False
        
        if r.avg_cadence <= 0:
            print(f"   ❌ Cadence should be > 0: {r.avg_cadence}")
            all_pass = False
    
    # Check non-overlap
    for i, r1 in enumerate(results):
        for j, r2 in enumerate(results):
            if i >= j:
                continue
            overlap_start = max(r1.start_time_seconds, r2.start_time_seconds)
            overlap_end = min(r1.end_time_seconds, r2.end_time_seconds)
            overlap = max(0, overlap_end - overlap_start)
            if overlap > 290 * 0.1:
                print(f"   ❌ Intervals #{r1.rank} and #{r2.rank} overlap by {overlap:.0f}s")
                all_pass = False
    
    if all_pass:
        print("   All checks passed!")
    
    print()


if __name__ == '__main__':
    main()
