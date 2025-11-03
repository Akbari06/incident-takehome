# Incident Schedule Renderer

This repository ships a single Python CLI (`./render-schedule`) that produces an on-call schedule with overrides applied and the result truncated to a requested window.

---

## Usage

The CLI defaults to the sample JSON files in the repository root. Override the inputs by pointing to your own data:
```bash
./render-schedule \
  --schedule schedule.json \
  --overrides overrides.json \
  --from 2025-11-07T17:00:00Z \
  --until 2025-11-21T17:00:00Z
```

Both JSON payloads mirror the structures described in the take-home brief. The resulting merged schedule prints to stdout in the same format.

---

## My Approach

I implemented the schedule renderer by:

1. Parsing command-line arguments and input files using `argparse` and `json`
2. Generating a repeating base schedule using the start date, interval, and user list
3. Detecting overlapping overrides and replacing affected time ranges
4. Splitting original shifts to insert overrides while keeping unaffected parts intact
5. Truncating schedule entries to fit within the `--from` and `--until` time window
6. Outputting the final schedule as formatted JSON with UTC timestamps

---

## Implementation Details

### Parsing Input and Arguments

- Used `argparse` to handle `--schedule`, `--overrides`, `--from`, and `--until` arguments
- Loaded input files with `json` to build the base schedule and override lists

### Generating the Base Schedule

- Implemented `generate_schedule()` to create a repeating rotation using `handover_start_at` and `handover_interval_days`
- Used `users[i % len(users)]` to loop through the user list cyclically until the `--until` date

### Applying Overrides

- Built `apply_overrides()` to detect overlapping overrides, split affected shifts into three parts (before, during, after), and insert overrides correctly
- Ensured that no two users overlap within the same time window

### Truncating the Schedule

- Used `truncate()` to trim any shifts that started before `--from` or ended after `--until`, keeping only relevant time ranges

### Outputting JSON

- Implemented `to_json()` to convert final schedule entries into ISO 8601 UTC format (Z for UTC) and print as formatted JSON

---

## File Layout

- **`render-schedule`** – CLI entry point containing the scheduling logic
- **`schedule.json`** / **`overrides.json`** – Sample inputs used by default
