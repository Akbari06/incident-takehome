"""FastAPI wrapper that exposes the scheduling engine over HTTP."""

from datetime import datetime
from pathlib import Path
from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field, field_validator

# Ensure the project root (where ``scheduler`` lives) is importable when running as a script.
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scheduler import ScheduleError, generate_schedule, to_payload


class ScheduleModel(BaseModel):
    """Request payload describing the base rotation."""

    users: List[str]
    handover_start_at: datetime
    handover_interval_days: int


class OverrideModel(BaseModel):
    """Request payload describing a temporary override."""

    user: str
    start_at: datetime
    end_at: datetime

    @field_validator("end_at")
    def validate_range(cls, end_at: datetime, info):
        """Ensure overrides are supplied with a positive duration."""

        start_at = info.data.get("start_at")
        if start_at and end_at <= start_at:
            raise ValueError("override end_at must be after start_at")
        return end_at


class ScheduleRequest(BaseModel):
    """Envelope for the schedule endpoint request body."""

    model_config = ConfigDict(populate_by_name=True)

    schedule: ScheduleModel
    overrides: List[OverrideModel] = []
    start_at: datetime = Field(..., alias="from")
    end_at: datetime = Field(..., alias="until")

    @field_validator("end_at")
    def validate_window(cls, end_at: datetime, info):
        """Ensure the request window is sensible."""

        start_at = info.data.get("start_at")
        if start_at and end_at <= start_at:
            raise ValueError("until must be after from")
        return end_at


app = FastAPI(title="Incident Schedule Renderer")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/schedule")
def render_schedule(request: ScheduleRequest):
    """Compute the merged schedule for the provided configuration."""

    schedule_payload = {
        "users": request.schedule.users,
        "handover_start_at": request.schedule.handover_start_at.isoformat(),
        "handover_interval_days": request.schedule.handover_interval_days,
    }
    overrides_payload = [
        {
            "user": override.user,
            "start_at": override.start_at.isoformat(),
            "end_at": override.end_at.isoformat(),
        }
        for override in request.overrides
    ]

    try:
        segments = generate_schedule(
            schedule_payload,
            overrides_payload,
            request.start_at,
            request.end_at,
        )
    except ScheduleError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return to_payload(segments)
