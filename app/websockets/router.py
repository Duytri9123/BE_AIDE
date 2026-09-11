from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from .manager import manager
from uuid import UUID

router = APIRouter()

@router.websocket("/ws/notifications")
async def notifications_endpoint(websocket: WebSocket):
    await manager.connect("notifications", websocket)
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect("notifications", websocket)

@router.websocket("/ws/analysis/{session_id}")
async def analysis_progress_endpoint(websocket: WebSocket, session_id: UUID):
    channel = f"analysis_{session_id}"
    await manager.connect(channel, websocket)
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(channel, websocket)
