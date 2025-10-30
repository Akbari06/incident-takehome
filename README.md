# Incident Schedule Renderer

This project demonstrates a small end-to-end stack for rendering on-call schedules with overrides. It ships with:

- a reusable Python scheduling engine and CLI (`./render-schedule`)
- a FastAPI backend that exposes the scheduling logic over HTTP (`backend/`)
- a React + Vite frontend that visualises the generated timeline (`frontend/`)

The CLI and backend share the same scheduling core, ensuring parity between local scripts and productised APIs.

## Why FastAPI and React?

- **FastAPI** provides expressive request validation with Pydantic models, async-ready routing, and automatic documentation (Swagger/OpenAPI) which is valuable when exposing scheduling logic to other services or teammates.
- **React** excels at composing interactive UIs. Using Vite keeps the tooling lightweight while offering instant feedback, making it easier to experiment with timeline layouts like the example screenshot.

## Getting Started

### Python environment

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

### CLI usage

```bash
./render-schedule \
  --schedule=examples/schedule.json \
  --overrides=examples/overrides.json \
  --from='2025-11-07T17:00:00Z' \
  --until='2025-11-21T17:00:00Z'
```

Supply your own JSON files matching the structures in the brief. The command outputs a merged schedule, truncated to the requested window.

### Running the API

```bash
uvicorn backend.main:app --reload
```

POST a payload to `http://localhost:8000/schedule`:

```json
{
  "schedule": {
    "users": ["alice", "bob", "charlie"],
    "handover_start_at": "2025-11-07T17:00:00Z",
    "handover_interval_days": 7
  },
  "overrides": [
    {
      "user": "charlie",
      "start_at": "2025-11-10T17:00:00Z",
      "end_at": "2025-11-10T22:00:00Z"
    }
  ],
  "from": "2025-11-07T17:00:00Z",
  "until": "2025-11-21T17:00:00Z"
}
```

The response mirrors the CLI output, making it easy to feed into other tooling or the frontend.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The React app expects the FastAPI service to be available at `http://localhost:8000`. It allows inline editing of the schedule/override payloads and renders both a timeline and tabular view.

## Project Structure

- `scheduler/engine.py` – pure scheduling logic with documented helpers.
- `render-schedule` – CLI wrapper around the shared engine.
- `backend/` – FastAPI application and Python dependencies.
- `frontend/` – React + Vite interface for visual exploration of schedules.

Feel free to extend the engine with additional rules (escalations, follow-the-sun rotations) and both the API and UI will pick them up automatically.
