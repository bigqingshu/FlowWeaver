from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from flowweaver.protocols.enums import EventType

router = APIRouter(tags=["events"])


@router.websocket("/ws/v1/events")
async def websocket_events(websocket: WebSocket) -> None:
    token = websocket.query_params.get("token")
    container = websocket.app.state.container
    if token != container.config.local_api_token:
        await websocket.close(code=1008)
        return
    origin = websocket.headers.get("origin")
    if origin and origin not in container.config.allowed_origins:
        await websocket.close(code=1008)
        return

    await websocket.accept()
    ready = await container.event_router.publish(
        EventType.ENGINE_READY,
        payload={"status": "connected"},
    )
    await websocket.send_json(ready.to_payload())
    queue = await container.event_router.subscribe()
    try:
        while True:
            event = await queue.get()
            await websocket.send_json(event.to_payload())
    except WebSocketDisconnect:
        return
    finally:
        container.event_router.unsubscribe(queue)
