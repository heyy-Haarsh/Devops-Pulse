"""
Tiny async TTL cache so that several dashboard endpoints polled at the same
moment share one round-trip to the Kubernetes / Prometheus APIs.
"""
import asyncio
import time
from typing import Any, Awaitable, Callable, Dict, Tuple

_store: Dict[str, Tuple[float, Any]] = {}
_locks: Dict[str, asyncio.Lock] = {}


async def cached(key: str, ttl: float, producer: Callable[[], Awaitable[Any]]) -> Any:
    now = time.monotonic()
    hit = _store.get(key)
    if hit and now - hit[0] < ttl:
        return hit[1]

    lock = _locks.setdefault(key, asyncio.Lock())
    async with lock:
        hit = _store.get(key)
        if hit and time.monotonic() - hit[0] < ttl:
            return hit[1]
        value = await producer()
        _store[key] = (time.monotonic(), value)
        return value


def clear() -> None:
    _store.clear()
