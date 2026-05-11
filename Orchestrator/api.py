from fastapi import APIRouter, HTTPException
from typing import Dict
from .schemas import (
    ChatSessionCreateResponse,
    ChatMessageRequest,
    ChatMessageResponse,
    Session
)
from .memory import memory_manager
from .services import orchestrator_service
from Agent.agent import has_agent_runtime
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from logger import debug_log

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])

@router.post("/session", response_model=ChatSessionCreateResponse)
async def create_session():
    """Create a new chat session."""
    session = memory_manager.create_session()
    return ChatSessionCreateResponse(session_id=session.session_id)

@router.get("/session/{session_id}", response_model=Session)
async def get_session(session_id: str):
    """Retrieve a chat session and its history."""
    session = memory_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session

@router.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """Delete a chat session."""
    success = memory_manager.delete_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "deleted"}

@router.post("/message", response_model=ChatMessageResponse)
async def send_message(request: ChatMessageRequest):
    """Send a message within a chat session."""
    debug_log("api.v1.chat.message", session_id=request.session_id, message_length=len(request.message))
    if not has_agent_runtime():
        raise HTTPException(
            status_code=503,
            detail="Gemini API key is not configured. Set GOOGLE_API_KEY or GEMINI_API_KEY to enable chat.",
        )

    session = memory_manager.get_session(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        result = await orchestrator_service.process_message(request.session_id, request.message)
        return ChatMessageResponse(
            session_id=result["session_id"],
            response=result["response"],
            intent=result["intent"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
