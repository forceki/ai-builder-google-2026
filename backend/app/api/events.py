import uuid

import jwt
from litestar import WebSocket, websocket
from litestar.exceptions import WebSocketDisconnect
from sqlalchemy import select

from app.config import get_settings
from app.events import channel
from app.models import Project, User

PROTOCOL = "heatmark"
PING_SECONDS = 20.0


def _offered_token(socket: WebSocket) -> str:
    offered = [p.strip() for p in socket.headers.get("sec-websocket-protocol", "").split(",")]
    return offered[1] if len(offered) == 2 and offered[0] == PROTOCOL else ""


@websocket("/api/projects/{project_no:str}/events")
async def project_events(socket: WebSocket, project_no: str) -> None:
    try:
        claims = jwt.decode(_offered_token(socket), get_settings().jwt_secret.get_secret_value(), algorithms=["HS256"])
        user_id = uuid.UUID(claims["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        await socket.close(code=4401, reason="not signed in")
        return

    async with socket.app.state.sessionmaker() as session:
        user = await session.get(User, user_id)
        project = await session.scalar(
            select(Project).where(Project.no == project_no, Project.owner_id == user_id)
        )
    if user is None or project is None:
        await socket.close(code=4404 if user else 4401, reason="not found" if user else "not signed in")
        return

    pubsub = socket.app.state.queue.pubsub()
    await pubsub.subscribe(channel(project.id))
    await socket.accept(subprotocols=PROTOCOL)
    try:
        await socket.send_json({"event": "hello"})
        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=PING_SECONDS)
            if message is None:
                await socket.send_json({"event": "ping"})
                continue
            data = message["data"]
            await socket.send_text(data.decode() if isinstance(data, bytes) else data)
    except (WebSocketDisconnect, RuntimeError, OSError):
        pass
    finally:
        await pubsub.unsubscribe()
        await pubsub.aclose()
