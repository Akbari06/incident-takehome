# Incident Schedule Renderer

This repository ships a single Python CLI (`./render-schedule`) that produces an on-call schedule with overrides applied and the result truncated to a requested window.


The CLI defaults to the sample JSON files in the repository root. Override the inputs by pointing to your own data:

```bash
./render-schedule \
  --schedule schedule.json \
  --overrides overrides.json \
  --from 2025-11-07T17:00:00Z \
  --until 2025-11-21T17:00:00Z

```

Both JSON payloads mirror the structures described in the take-home brief. The resulting merged schedule prints to stdout in the same format.

## File layout

- `render-schedule` – CLI entry point containing the scheduling logic.
- `schedule.json` / `overrides.json` – sample inputs used by default.
