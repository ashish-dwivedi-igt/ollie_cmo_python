from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timezone

class ConversationIntent(str, Enum):
    CREATIVE_ANALYSIS = "creative_analysis"
    MESSAGING_ITERATION = "messaging_iteration"
    HOOK_ANALYSIS = "hook_analysis"
    PERFORMANCE_BREAKDOWN = "performance_breakdown"
    AUDIENCE_ANALYSIS = "audience_analysis"
    FATIGUE_DETECTION = "fatigue_detection"
    COMPARISON = "comparison"
    RECOMMENDATION = "recommendation"
    FOLLOW_UP_QUESTION = "follow_up_question"
    GENERAL_CHAT = "general_chat"

class IntentDetectionResponse(BaseModel):
    intent: ConversationIntent = Field(description="The detected intent of the user's message.")
    confidence: float = Field(description="Confidence score between 0.0 and 1.0.")

class RewrittenQueryResponse(BaseModel):
    objective: str = Field(description="The primary objective of the query.")
    platform: str = Field(description="The platform, usually 'meta'.", default="meta")
    audience: Optional[str] = Field(description="Target audience if mentioned.", default=None)
    analysis_type: Optional[str] = Field(description="Type of analysis requested.", default=None)
    search_query: str = Field(description="A clean, structured search query string to pass to the agent.")

class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

def utcnow():
    return datetime.now(timezone.utc)

class ChatMessage(BaseModel):
    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=utcnow)
    intent: Optional[ConversationIntent] = None
    rewritten_query: Optional[str] = None

class Session(BaseModel):
    session_id: str
    messages: List[ChatMessage] = Field(default_factory=list)
    summary: Optional[str] = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

class ChatSessionCreateResponse(BaseModel):
    session_id: str

class ChatMessageRequest(BaseModel):
    session_id: str
    message: str

class ChatMessageResponse(BaseModel):
    session_id: str
    response: str
    intent: Optional[ConversationIntent] = None
