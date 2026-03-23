"""
Server-Sent Events (SSE) endpoint for real-time simulation progress.

Replaces MiroFish's frontend polling pattern entirely.
The client opens one long-lived connection per run and receives events as they happen.
Events are read from the SQLite events table, not from in-memory state,
so reconnects and page refreshes receive the full history automatically.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time

from fastapi import APIRouter, HTTPException, Request
from sse_starlette.sse import EventSourceResponse

from murm.api.store import ProjectStore

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/{run_id}")
async def stream_run(run_id: str, request: Request, since: float = 0.0):
    """
    SSE endpoint. Connect with:
      GET /api/stream/{run_id}?since=0
    Optional 'since' timestamp allows resuming without re-receiving old events.
    Streams until the run completes or the client disconnects.
    """
    store: ProjectStore = request.app.state.store
    run = await store.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")

    return EventSourceResponse(
        _event_generator(run_id, store, request, since),
        media_type="text/event-stream",
    )


async def _event_generator(
    run_id: str,
    store: ProjectStore,
    request: Request,
    since_ts: float,
):
    """
    Yields SSE-formatted events from the events table.
    Polls every 0.5s - fast enough for UI updates, not so fast as to hammer SQLite.
    """
    last_ts = since_ts
    terminal_types = {"simulation_ended", "simulation_failed"}

    while True:
        if await request.is_disconnected():
            logger.debug("SSE client disconnected from run %s", run_id)
            break

        events = await store.get_events_since(run_id, since_ts=last_ts)
        for event in events:
            payload = {
                "type": event["event_type"],
                "ts": event["ts"],
                "payload": event["payload"],
            }
            yield {"data": json.dumps(payload)}
            last_ts = event["ts"]

            if event["event_type"] in terminal_types:
                return

        # Check run status directly in case the engine stopped without emitting a terminal event
        run = await store.get_run(run_id)
        if run and run.get("status") in ("completed", "failed", "cancelled"):
            yield {"data": json.dumps({"type": "done", "status": run["status"]})}
            return

        await asyncio.sleep(0.5)
