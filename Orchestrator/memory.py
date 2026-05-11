import uuid
from typing import Dict, Optional, List
from .schemas import Session, ChatMessage, MessageRole, utcnow

class SessionMemoryManager:
    def __init__(self, max_context_messages: int = 10):
        # In-memory storage for MVP
        self.sessions: Dict[str, Session] = {}
        self.max_context_messages = max_context_messages

    def create_session(self) -> Session:
        session_id = str(uuid.uuid4())
        session = Session(session_id=session_id)
        self.sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> Optional[Session]:
        return self.sessions.get(session_id)

    def delete_session(self, session_id: str) -> bool:
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False

    def add_message(self, session_id: str, message: ChatMessage) -> None:
        session = self.get_session(session_id)
        if session:
            session.messages.append(message)
            session.updated_at = utcnow()

    def get_context(self, session_id: str) -> List[ChatMessage]:
        """Returns the recent messages within the sliding window."""
        session = self.get_session(session_id)
        if not session:
            return []
        
        # Sliding context window
        return session.messages[-self.max_context_messages:]

# Singleton instance for the MVP
memory_manager = SessionMemoryManager()
