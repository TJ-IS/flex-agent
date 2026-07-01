from __future__ import annotations

import asyncio
import itertools
from typing import Any

from fastapi import WebSocket

_id_counter = itertools.count(1)


def _new_connection_id() -> int:
    return next(_id_counter)


class PresenceManager:
    """Track live WebSocket connections per session and broadcast presence stats.

    ``online_sessions`` counts distinct session ids with at least one open
    WebSocket. ``online_connections`` counts total open WebSockets (a session
    may have several tabs open).
    """

    def __init__(self) -> None:
        # session_id -> {connection_id: websocket}
        self._sessions: dict[str, dict[int, WebSocket]] = {}
        # presence subscribers: connection_id -> websocket (for /api/presence/stream)
        self._subscribers: dict[int, WebSocket] = {}
        self._lock = asyncio.Lock()

    async def register_session(self, session_id: str, websocket: WebSocket) -> int:
        async with self._lock:
            conn_id = _new_connection_id()
            self._sessions.setdefault(session_id, {})[conn_id] = websocket
        await self.broadcast()
        return conn_id

    async def unregister_session(self, session_id: str, conn_id: int) -> None:
        async with self._lock:
            conns = self._sessions.get(session_id)
            if conns is not None:
                conns.pop(conn_id, None)
                if not conns:
                    self._sessions.pop(session_id, None)
        await self.broadcast()

    async def subscribe(self, websocket: WebSocket) -> int:
        async with self._lock:
            conn_id = _new_connection_id()
            self._subscribers[conn_id] = websocket
        await websocket.send_text(self._serialize(self.stats_sync()))
        return conn_id

    async def unsubscribe(self, conn_id: int) -> None:
        async with self._lock:
            self._subscribers.pop(conn_id, None)

    def stats_sync(self) -> dict[str, int]:
        return {
            "online_sessions": len(self._sessions),
            "online_connections": sum(len(conns) for conns in self._sessions.values()),
        }

    async def stats(self) -> dict[str, int]:
        async with self._lock:
            return self.stats_sync()

    @staticmethod
    def _serialize(stats: dict[str, int]) -> str:
        import json

        payload = {"type": "presence", **stats}
        return json.dumps(payload, ensure_ascii=False)

    async def broadcast(self) -> None:
        async with self._lock:
            stats = self.stats_sync()
            subscribers = list(self._subscribers.values())
        if not subscribers:
            return
        message = self._serialize(stats)
        stale: list[WebSocket] = []
        for ws in subscribers:
            try:
                await ws.send_text(message)
            except Exception:
                stale.append(ws)
        if stale:
            async with self._lock:
                for ws in stale:
                    self._subscribers = {
                        cid: w for cid, w in self._subscribers.items() if w is not ws
                    }


presence_manager = PresenceManager()
