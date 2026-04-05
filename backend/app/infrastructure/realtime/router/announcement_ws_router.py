import asyncio

import logfire
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from redis.asyncio import Redis

from app.infrastructure.realtime.service import ANNOUNCEMENTS_CHANNEL

router = APIRouter(prefix="/realtime", tags=["realtime"])


@router.websocket("/announcements/ws")
async def announcements_websocket(websocket: WebSocket) -> None:
    await websocket.accept()

    redis: Redis = websocket.app.state.redis
    pubsub = redis.pubsub()
    await pubsub.subscribe(ANNOUNCEMENTS_CHANNEL)

    try:
        await websocket.send_json({"event": "connected", "channel": ANNOUNCEMENTS_CHANNEL})
        while True:
            try:
                # Allow clients to send keepalive messages and detect closed sockets.
                await asyncio.wait_for(websocket.receive_text(), timeout=0.2)
            except TimeoutError:
                pass
            except WebSocketDisconnect:
                break

            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if not message:
                continue

            payload = message.get("data")
            if isinstance(payload, bytes):
                payload = payload.decode("utf-8")
            await websocket.send_text(str(payload))
    except Exception as exc:
        logfire.warn("Announcements websocket closed with error", error=str(exc))
    finally:
        await pubsub.unsubscribe(ANNOUNCEMENTS_CHANNEL)
        await pubsub.aclose()
