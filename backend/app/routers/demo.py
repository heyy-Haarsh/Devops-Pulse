"""
Safe, opt-in endpoints used by the dashboard's "Traffic Generator" to make
monitoring graphs move during a demo. They only affect the request that calls
them — nothing is crashed, deleted or reconfigured.
"""
import asyncio

from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/api/demo", tags=["Demo"])


@router.get("/ok")
async def demo_ok():
    """A normal, fast request."""
    return {"result": "ok"}


@router.get("/error")
async def demo_error():
    """Returns HTTP 500 so error-rate panels and alerts can be demonstrated."""
    raise HTTPException(status_code=500, detail="Simulated error for monitoring demo")


@router.get("/slow")
async def demo_slow(ms: int = Query(800, ge=0, le=3000)):
    """Waits `ms` milliseconds (max 3 s) to create a visible latency spike."""
    await asyncio.sleep(ms / 1000)
    return {"result": "ok", "delay_ms": ms}
