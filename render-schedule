#!/usr/bin/env python3
"""CLI entry point for the on-call schedule renderer."""

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent


def candidate_paths(path_str):
    """Return likely locations for a user-supplied path."""
    path = Path(path_str)
    if path.is_absolute():
        return [path]
    return [Path.cwd() / path, REPO_ROOT / path]


def load_json_file(path_str, description):
    """Load JSON, expanding relative paths and surfacing a clear error."""
    candidates = []
    for candidate in candidate_paths(path_str):
        if candidate not in candidates:
            candidates.append(candidate)
    for candidate in candidates:
        try:
            with candidate.open() as fh:
                return json.load(fh)
        except FileNotFoundError:
            continue
    locations = "\n  ".join(str(c) for c in candidates)
    sys.exit(f"Could not find {description} file {path_str!r}. Checked:\n  {locations}")


def parse_iso(dt_str):
    """Parse an ISO 8601 string while tolerating Zulu suffixes."""
    return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))  # Handle 'Z' as UTC


def generate_schedule(users, start_at, interval_days, until):
    """Build the base rotation given users, start time, and interval."""
    schedule = []
    start = start_at
    interval = timedelta(days=interval_days)
    i = 0
    while start < until:
        end = start + interval
        schedule.append({
            "user": users[i % len(users)],
            "start": start,
            "end": end
        })
        start = end
        i += 1
    return schedule


def apply_overrides(schedule, overrides):
    """Overlay overrides onto the base schedule, preserving gaps."""
    new_schedule = []
    for entry in schedule:
        start, end = entry["start"], entry["end"]
        overlapping = [o for o in overrides if not (o["end"] <= start or o["start"] >= end)]
        if not overlapping:
            new_schedule.append(entry)
            continue
        current_start = start
        for o in sorted(overlapping, key=lambda x: x["start"]):
            if o["start"] > current_start:
                new_schedule.append({"user": entry["user"], "start": current_start, "end": o["start"]})
            new_schedule.append(o)
            current_start = max(current_start, o["end"])
        if current_start < end:
            new_schedule.append({"user": entry["user"], "start": current_start, "end": end})
    return new_schedule


def truncate(schedule, start_range, end_range):
    """Trim schedule entries so they fit within the requested window."""
    truncated = []
    for s in schedule:
        start = max(s["start"], start_range)
        end = min(s["end"], end_range)
        if start < end:
            truncated.append({"user": s["user"], "start": start, "end": end})
    return truncated


def to_json(schedule):
    """Serialize the final schedule list back into JSON."""
    return json.dumps([
        {"user": s["user"],
         "start_at": s["start"].isoformat().replace("+00:00", "Z"),
         "end_at": s["end"].isoformat().replace("+00:00", "Z")}
        for s in schedule
    ], indent=2)


def main():
    """Parse CLI arguments, synthesize the schedule, and print JSON."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--schedule", default="schedule.json",
                        help="Path to the base schedule JSON (default: schedule.json)")
    parser.add_argument("--overrides", default="overrides.json",
                        help="Path to the overrides JSON (default: overrides.json)")
    parser.add_argument("--from", dest="from_", required=True)
    parser.add_argument("--until", required=True)
    args = parser.parse_args()

    schedule_data = load_json_file(args.schedule, "schedule")
    overrides_data = load_json_file(args.overrides, "overrides")

    from_time = parse_iso(args.from_)
    until_time = parse_iso(args.until)

    base_schedule = generate_schedule(
        schedule_data["users"],
        parse_iso(schedule_data["handover_start_at"]),
        schedule_data["handover_interval_days"],
        until_time
    )

    overrides = [
        {"user": o["user"], "start": parse_iso(o["start_at"]), "end": parse_iso(o["end_at"])}
        for o in overrides_data
    ]

    final_schedule = apply_overrides(base_schedule, overrides)
    final_schedule = truncate(final_schedule, from_time, until_time)

    print(to_json(final_schedule))


if __name__ == "__main__":
    main()
