"""NATS JetStream publisher for publishing scan jobs."""
import json
import os
from typing import Any

import nats
from nats.js import JetStreamContext

NATS_URL = os.getenv("NATS_URL", "nats://nats:4222")

_nc = None
_js: JetStreamContext | None = None


async def get_jetstream() -> JetStreamContext:
    global _nc, _js
    if _nc is None or _nc.is_closed:
        _nc = await nats.connect(NATS_URL)
        _js = _nc.jetstream()
        # Ensure stream exists
        try:
            await _js.add_stream(name="SCANS", subjects=["scan.>"])
        except Exception:
            pass  # Stream already exists
    return _js


async def publish_scan_job(subject: str, payload: dict[str, Any]) -> None:
    """Publish a scan job message to NATS JetStream.

    Subjects used:
    - scan.sast.requested   – triggers the SAST scanner worker
    - scan.dast.requested   – triggers the DAST scanner worker
    """
    js = await get_jetstream()
    data = json.dumps(payload).encode()
    await js.publish(subject, data)


async def close() -> None:
    global _nc
    if _nc and not _nc.is_closed:
        await _nc.drain()
