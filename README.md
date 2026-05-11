# Ollie CMO - AI Marketing Assistant

Ollie CMO is a sophisticated agentic AI platform designed to orchestrate and manage Meta advertising workflows. It uses a dual-agent architecture to provide precise marketing insights and creative analysis.

## Getting Started

### Prerequisites

- **Python 3.12+**
- **uv**: A fast Python package installer and resolver.

### Setup

1. **Install Dependencies**
   Use `uv` to synchronize your environment and install all necessary dependencies:
   ```bash
   uv sync
   ```

2. **Configure Environment Variables**
   Create a `.env` file in the root directory (you can use `.env.example` as a template) and add your API keys:
   ```env
   # LLM Configuration
   GOOGLE_API_KEY=your_gemini_api_key

   # Meta API Configuration
   META_ACCESS_TOKEN=your_meta_token
   META_AD_ACCOUNT_ID=your_ad_account_id
   META_APP_ID=your_app_id
   META_APP_SECRET=your_app_secret
   ```

## How to Start

To launch the FastAPI backend and the chatbot interface, run:

```bash
uv run main.py
```

The server will start at `http://localhost:8000`, where you can access the interactive chat interface.

## How it Works

The project implements a robust **Agentic Workflow** consisting of two primary layers:

### 1. The Orchestrator
The Orchestrator acts as the system's supervisor. When a user sends a message, the Orchestrator:
- **Detects Intent**: Determines if the user is asking for performance data, creative analysis, or general chat.
- **Rewrites Queries**: Optimizes the user's prompt into a search query that the downstream agent can better understand.
- **Manages Memory**: Maintains session context and chat history to ensure coherent multi-turn conversations.
- **Synthesizes Responses**: Combines raw agent output with conversational context to provide a polished final answer.

### 2. Meta Creative Agent
The Meta Creative Agent is a specialized worker agent focused on advertising operations. It is equipped with specific tools to interact with the Meta marketing ecosystem:
- `list_ads_with_creatives`: Fetches active ads and their associated creative assets.
- `get_ad_performance_insights`: Retrieves engagement and conversion metrics.
- `search_ad_library`: Searches Meta's Ad Library for competitive research.

### The Pipeline
1. **User Message** → **Orchestrator** (Intent & Rewriting)
2. **Orchestrator** → **Meta Creative Agent** (Execution via Tools)
3. **Meta Creative Agent** → **Orchestrator** (Raw Data/Insights)
4. **Orchestrator** → **User** (Final Synthesized Response)
