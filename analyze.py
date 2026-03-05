"""
Rowing interval analysis engine.

Finds the fastest continuous intervals in rowing activity data,
filtered by minimum cadence. Reports speed in sec/500m.
Supports both time-based and distance-based interval selection,
and 500m sub-split breakdowns.
"""

import bisect
from dataclasses import dataclass, field


@dataclass
class SubSplit:
    """A 500m (or remainder) sub-segment within an interval."""
    segment_label: str       # "0-500m", "500-1000m", etc.
    distance_meters: float   # 500 (or remainder)
    duration_seconds: float
    split_sec_per_500m: float
    split_formatted: str     # "1:52.3"
    avg_cadence: float


@dataclass
class IntervalResult:
    """Result of a single interval analysis."""
    rank: int
    start_idx: int
    end_idx: int
    start_time_seconds: float
    end_time_seconds: float
    duration_seconds: float
    start_time_formatted: str
    duration_formatted: str
    avg_speed_sec_per_500m: float
    avg_speed_formatted: str
    avg_cadence: float
    distance_meters: float
    avg_velocity_ms: float
    sub_splits: list[SubSplit] = field(default_factory=list)

    def __str__(self):
        return (
            f"#{self.rank}  Speed: {self.avg_speed_formatted}/500m | "
            f"Cadence: {self.avg_cadence:.1f} | "
            f"Distance: {self.distance_meters:,.0f}m | "
            f"Start: {self.start_time_formatted}"
        )

    def to_dict(self):
        """Convert to JSON-serializable dict."""
        return {
            'rank': self.rank,
            'start_time_seconds': self.start_time_seconds,
            'end_time_seconds': self.end_time_seconds,
            'duration_seconds': self.duration_seconds,
            'start_time_formatted': self.start_time_formatted,
            'duration_formatted': self.duration_formatted,
            'avg_speed_sec_per_500m': self.avg_speed_sec_per_500m,
            'avg_speed_formatted': self.avg_speed_formatted,
            'avg_cadence': round(self.avg_cadence, 1),
            'distance_meters': round(self.distance_meters, 1),
            'avg_velocity_ms': round(self.avg_velocity_ms, 3),
            'sub_splits': [
                {
                    'segment_label': s.segment_label,
                    'distance_meters': round(s.distance_meters, 1),
                    'duration_seconds': round(s.duration_seconds, 1),
                    'split_sec_per_500m': round(s.split_sec_per_500m, 1),
                    'split_formatted': s.split_formatted,
                    'avg_cadence': round(s.avg_cadence, 1),
                }
                for s in self.sub_splits
            ],
        }


def format_time(seconds: float) -> str:
    """Format seconds as mm:ss."""
    mins = int(seconds) // 60
    secs = int(seconds) % 60
    return f"{mins}:{secs:02d}"


def format_duration(seconds: float) -> str:
    """Format duration as mm:ss.s."""
    mins = int(seconds) // 60
    secs = seconds - mins * 60
    return f"{mins}:{secs:04.1f}"


def format_speed(sec_per_500m: float) -> str:
    """Format speed as m:ss.s per 500m."""
    mins = int(sec_per_500m) // 60
    secs = sec_per_500m - mins * 60
    return f"{mins}:{secs:04.1f}"


def _weighted_avg_cadence(cadence, time, start_idx, end_idx):
    """Compute time-weighted average cadence over a range."""
    n = len(time)
    cadence_sum = 0.0
    weight_sum = 0.0
    for i in range(start_idx, end_idx):
        if i + 1 < n:
            dt_step = time[i + 1] - time[i]
        else:
            dt_step = 1.0
        cadence_sum += cadence[i] * dt_step
        weight_sum += dt_step
    if weight_sum > 0:
        return cadence_sum / weight_sum
    return 0.0


def compute_500m_splits(
    time: list[float],
    cadence: list[float],
    distance: list[float],
    start_idx: int,
    end_idx: int,
) -> list[SubSplit]:
    """
    Chop an interval into 500m sub-segments.

    Returns a list of SubSplit objects, one per 500m chunk
    plus a remainder if the interval isn't evenly divisible.
    """
    splits = []
    base_dist = distance[start_idx]
    total_dist = distance[end_idx] - base_dist
    n = len(time)

    if total_dist <= 0:
        return splits

    chunk_start_idx = start_idx
    chunk_num = 0

    while chunk_start_idx < end_idx:
        chunk_start_dist = distance[chunk_start_idx] - base_dist
        chunk_target_dist = (chunk_num + 1) * 500.0

        # Find the index where we cross the next 500m boundary
        chunk_end_idx = chunk_start_idx
        while chunk_end_idx < end_idx and (distance[chunk_end_idx] - base_dist) < chunk_target_dist:
            chunk_end_idx += 1

        # Clamp to end of interval
        if chunk_end_idx > end_idx:
            chunk_end_idx = end_idx

        # If we haven't moved, skip
        if chunk_end_idx <= chunk_start_idx:
            break

        seg_dist = distance[chunk_end_idx] - distance[chunk_start_idx]
        seg_time = time[chunk_end_idx] - time[chunk_start_idx]

        if seg_dist <= 0 or seg_time <= 0:
            break

        seg_speed = 500.0 / (seg_dist / seg_time) if seg_dist > 0 else 0
        seg_cadence = _weighted_avg_cadence(cadence, time, chunk_start_idx, chunk_end_idx)

        start_m = int(chunk_num * 500)
        end_m = start_m + int(round(seg_dist))
        is_remainder = seg_dist < 490  # Less than ~500m

        if is_remainder and chunk_end_idx >= end_idx:
            label = f"{start_m}-{start_m + int(round(seg_dist))}m"
        else:
            label = f"{start_m}-{start_m + 500}m"

        splits.append(SubSplit(
            segment_label=label,
            distance_meters=round(seg_dist, 1),
            duration_seconds=round(seg_time, 1),
            split_sec_per_500m=round(seg_speed, 1),
            split_formatted=format_speed(seg_speed),
            avg_cadence=round(seg_cadence, 1),
        ))

        chunk_start_idx = chunk_end_idx
        chunk_num += 1

    return splits


def find_fastest_intervals(
    time: list[float],
    velocity_smooth: list[float],
    cadence: list[float],
    distance: list[float],
    interval_duration: float | None = 290.0,
    interval_distance: float | None = None,
    num_intervals: int = 3,
    min_cadence: float = 24.0,
    overlap_threshold: float = 0.1,
) -> list[IntervalResult]:
    """
    Find the N fastest non-overlapping intervals.

    Supports two modes:
    - Time-based: interval_duration is set (seconds), finds windows of that duration
    - Distance-based: interval_distance is set (meters), finds windows covering that distance

    Args:
        time: Time array (seconds from activity start, irregular spacing)
        velocity_smooth: Smoothed velocity array (m/s)
        cadence: Cadence array (strokes per minute)
        distance: Cumulative distance array (meters)
        interval_duration: Duration in seconds (time-based mode)
        interval_distance: Distance in meters (distance-based mode)
        num_intervals: Number of fastest intervals to return
        min_cadence: Minimum average cadence for a valid interval
        overlap_threshold: Maximum fraction of overlap allowed between intervals

    Returns:
        List of IntervalResult sorted by speed (fastest first)
    """
    n = len(time)
    if n == 0:
        return []

    assert len(velocity_smooth) == n
    assert len(cadence) == n
    assert len(distance) == n

    distance_mode = interval_distance is not None
    candidates = []

    for start_idx in range(n):
        if distance_mode:
            # Find end index where distance[end] - distance[start] >= interval_distance
            target_dist = distance[start_idx] + interval_distance
            end_idx = bisect.bisect_left(distance, target_dist, lo=start_idx)
        else:
            # Find end index where time[end] - time[start] >= interval_duration
            target_time = time[start_idx] + interval_duration
            end_idx = bisect.bisect_left(time, target_time, lo=start_idx)

        if end_idx >= n:
            break

        dt = time[end_idx] - time[start_idx]
        if dt <= 0:
            continue

        dist = distance[end_idx] - distance[start_idx]
        if dist <= 0:
            continue

        avg_vel = dist / dt
        avg_cad = _weighted_avg_cadence(cadence, time, start_idx, end_idx)

        if avg_cad < min_cadence:
            continue

        sec_per_500m = 500.0 / avg_vel if avg_vel > 0 else float('inf')

        candidates.append({
            'start_idx': start_idx,
            'end_idx': end_idx,
            'start_time': time[start_idx],
            'end_time': time[end_idx],
            'duration': dt,
            'avg_vel': avg_vel,
            'sec_per_500m': sec_per_500m,
            'avg_cadence': avg_cad,
            'distance': dist,
        })

    # Sort by speed (lowest sec/500m = fastest)
    candidates.sort(key=lambda c: c['sec_per_500m'])

    # For overlap check, use whichever dimension defines the interval
    ref_duration = interval_distance if distance_mode else interval_duration

    # Select top N non-overlapping intervals
    selected = []
    for candidate in candidates:
        if len(selected) >= num_intervals:
            break

        overlaps = False
        for sel in selected:
            overlap_start = max(candidate['start_time'], sel['start_time'])
            overlap_end = min(candidate['end_time'], sel['end_time'])
            overlap_dur = max(0, overlap_end - overlap_start)
            # Use the actual candidate duration for threshold
            if overlap_dur > candidate['duration'] * overlap_threshold:
                overlaps = True
                break

        if not overlaps:
            selected.append(candidate)

    # Convert to IntervalResult with 500m sub-splits
    results = []
    for rank, sel in enumerate(selected, 1):
        sub_splits = compute_500m_splits(
            time, cadence, distance,
            sel['start_idx'], sel['end_idx'],
        )

        results.append(IntervalResult(
            rank=rank,
            start_idx=sel['start_idx'],
            end_idx=sel['end_idx'],
            start_time_seconds=sel['start_time'],
            end_time_seconds=sel['end_time'],
            duration_seconds=sel['duration'],
            start_time_formatted=format_time(sel['start_time']),
            duration_formatted=format_duration(sel['duration']),
            avg_speed_sec_per_500m=sel['sec_per_500m'],
            avg_speed_formatted=format_speed(sel['sec_per_500m']),
            avg_cadence=sel['avg_cadence'],
            distance_meters=sel['distance'],
            avg_velocity_ms=sel['avg_vel'],
            sub_splits=sub_splits,
        ))

    # Sort by start time (chronological) before returning
    results.sort(key=lambda r: r.start_time_seconds)

    return results


def get_activity_summary(time, distance, velocity_smooth, cadence):
    """Compute overall activity summary stats."""
    total_time = time[-1] - time[0] if len(time) > 1 else 0
    total_distance = distance[-1] - distance[0] if len(distance) > 1 else 0

    # Average speed for moving portions (velocity > 0.5 m/s)
    moving_vel = []
    for i, v in enumerate(velocity_smooth):
        if v > 0.5:
            moving_vel.append(v)

    avg_vel = sum(moving_vel) / len(moving_vel) if moving_vel else 0
    avg_split = 500.0 / avg_vel if avg_vel > 0 else 0

    # Non-zero cadence average
    nonzero_cad = [c for c in cadence if c > 0]
    avg_cad = sum(nonzero_cad) / len(nonzero_cad) if nonzero_cad else 0

    return {
        'total_time_seconds': total_time,
        'total_time_formatted': format_time(total_time),
        'total_distance_meters': round(total_distance, 0),
        'avg_split_sec_per_500m': round(avg_split, 1),
        'avg_split_formatted': format_speed(avg_split) if avg_vel > 0 else '-',
        'avg_cadence': round(avg_cad, 1),
        'data_points': len(time),
    }
