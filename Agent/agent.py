"""Agent construction and execution helpers."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore

from Tools.meta.metaCreatives import (
    list_ads_with_creatives,
    get_ad_performance_insights,
    fetch_filtered_insights,
    list_campaigns,
    list_adsets,
    search_ad_library,
)

load_dotenv()

DEFAULT_MODEL = "google_genai:gemini-2.5-flash-lite"
DEFAULT_SYSTEM_PROMPT = "You are a helpful CMO assistant with access to Meta advertising tools."

# Global stores for LangGraph memory
global_checkpointer = InMemorySaver()
global_store = InMemoryStore()


@dataclass(frozen=True, slots=True)
class AgentConfig:
    """Configuration for building the agent."""

    model: str = DEFAULT_MODEL
    system_prompt: str = DEFAULT_SYSTEM_PROMPT


def get_api_key() -> str | None:
    """Return the configured Gemini API key, if one exists."""
    return os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")


def has_agent_runtime() -> bool:
    """Return whether the Gemini-backed agent can be created."""
    return get_api_key() is not None


def build_agent(config: AgentConfig | None = None):
    """Create a LangChain agent when Gemini credentials are available."""
    if not has_agent_runtime():
        raise RuntimeError("Gemini API key is not configured.")

    agent_config = config or AgentConfig()
    return create_agent(
        model=agent_config.model,
        tools=[
            list_ads_with_creatives,
            get_ad_performance_insights,
            fetch_filtered_insights,
            list_campaigns,
            list_adsets,
            search_ad_library,
        ],
        system_prompt=agent_config.system_prompt,
        checkpointer=global_checkpointer,
        store=global_store,
    )


def _extract_message_text(message: Any) -> str:
    content = getattr(message, "content", None)
    if isinstance(content, str):
        return content
    if content is not None:
        return str(content)
    return str(message)


def ask_agent(question: str, session_id: str = "default_session", config: AgentConfig | None = None) -> str:
    """Ask the agent a question and return the final text response."""
    if not has_agent_runtime():
        raise RuntimeError("Gemini API key is not configured.")

    agent = build_agent(config)
    result = agent.invoke(
        {"messages": [{"role": "user", "content": question}]},
        config={"configurable": {"thread_id": session_id}}
    )
    messages = result.get("messages", [])
    if not messages:
        return ""

    return _extract_message_text(messages[-1])