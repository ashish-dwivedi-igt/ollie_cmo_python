import os
from typing import Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from .schemas import (
    IntentDetectionResponse,
    RewrittenQueryResponse,
    ChatMessage,
    MessageRole,
    ConversationIntent
)
from .prompts import (
    INTENT_DETECTION_PROMPT,
    QUERY_REWRITER_PROMPT,
    RESPONSE_SYNTHESIS_PROMPT,
    SUMMARIZATION_PROMPT
)
from .memory import memory_manager
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from logger import debug_log

# Import the existing agent
from Agent.agent import ask_agent

def get_llm():
    return ChatGoogleGenerativeAI(model="gemini-flash-lite-latest", temperature=0.1)

class OrchestratorService:
    def __init__(self):
        self.llm = get_llm()

    async def detect_intent(self, message: str) -> IntentDetectionResponse:
        structured_llm = self.llm.with_structured_output(IntentDetectionResponse)
        chain = INTENT_DETECTION_PROMPT | structured_llm
        try:
            return await chain.ainvoke({"user_message": message})
        except Exception:
            return IntentDetectionResponse(intent=ConversationIntent.GENERAL_CHAT, confidence=1.0)

    async def rewrite_query(self, message: str) -> RewrittenQueryResponse:
        structured_llm = self.llm.with_structured_output(RewrittenQueryResponse)
        chain = QUERY_REWRITER_PROMPT | structured_llm
        try:
            return await chain.ainvoke({"user_message": message})
        except Exception:
            return RewrittenQueryResponse(objective="unknown", platform="meta", search_query=message)

    async def synthesize_response(self, chat_history: str, agent_output: str) -> str:
        chain = RESPONSE_SYNTHESIS_PROMPT | self.llm
        response = await chain.ainvoke({
            "chat_history": chat_history,
            "agent_output": agent_output
        })
        content = response.content
        if isinstance(content, list):
            texts = [item.get("text", "") if isinstance(item, dict) else str(item) for item in content]
            return "".join(texts)
        return str(content)

    async def summarize_conversation(self, conversation_text: str) -> str:
        chain = SUMMARIZATION_PROMPT | self.llm
        response = await chain.ainvoke({
            "conversation_text": conversation_text
        })
        return response.content

    def format_chat_history(self, session_id: str) -> str:
        messages = memory_manager.get_context(session_id)
        if not messages:
            return "No previous conversation."
        
        formatted = []
        for msg in messages:
            role = "User" if msg.role == MessageRole.USER else "Assistant"
            formatted.append(f"{role}: {msg.content}")
        return "\n".join(formatted)

    async def process_message(self, session_id: str, message: str) -> dict:
        debug_log("OrchestratorService.process_message", session_id=session_id, message=message)
        
        # 1. Detect Intent
        debug_log("OrchestratorService.detect_intent", message=message)
        intent_response = await self.detect_intent(message)
        intent = intent_response.intent
        debug_log("OrchestratorService.detect_intent_result", intent=intent.value)
        
        # 2. Rewrite Query
        rewritten_response = None
        search_query = message
        
        if intent != ConversationIntent.GENERAL_CHAT:
            debug_log("OrchestratorService.rewrite_query", message=message, intent=intent.value)
            rewritten_response = await self.rewrite_query(message)
            search_query = rewritten_response.search_query
            debug_log("OrchestratorService.rewrite_query_result", search_query=search_query)

        # 3. Save User Message to Memory
        user_msg = ChatMessage(
            role=MessageRole.USER,
            content=message,
            intent=intent,
            rewritten_query=rewritten_response.search_query if rewritten_response else None
        )
        memory_manager.add_message(session_id, user_msg)
        
        # 4. Format Context
        debug_log("OrchestratorService.format_chat_history", session_id=session_id)
        chat_history = self.format_chat_history(session_id)
        
        # 5. Call Meta Agent
        try:
            debug_log("Agent.ask_agent", search_query=search_query, session_id=session_id)
            # ask_agent now uses LangGraph native memory with session_id
            agent_raw_output = ask_agent(search_query, session_id=session_id)
            debug_log("Agent.ask_agent_result", agent_raw_output_length=len(agent_raw_output))
        except Exception as e:
            agent_raw_output = f"Error communicating with Meta Agent: {str(e)}"
            
        # 6. Synthesize Response
        debug_log("OrchestratorService.synthesize_response", chat_history_length=len(chat_history), agent_raw_output_length=len(agent_raw_output))
        final_response_text = await self.synthesize_response(chat_history, agent_raw_output)
        debug_log("OrchestratorService.synthesize_response_result", final_response_text_length=len(final_response_text))
        
        # 7. Save Assistant Message to Memory
        assistant_msg = ChatMessage(
            role=MessageRole.ASSISTANT,
            content=final_response_text
        )
        memory_manager.add_message(session_id, assistant_msg)
        
        return {
            "session_id": session_id,
            "response": final_response_text,
            "intent": intent
        }

orchestrator_service = OrchestratorService()
