from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(tags=["events"])


@router.websocket("/ws/v1/events")
async def websocket_events(websocket: WebSocket) -> None:
    await websocket.accept()
    await websocket.send_json(
        {
            "event_type": "ENGINE_READY",
            "event_version": "1.0",
            "payload": {"status": "connected"},
        }
    )
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        return
