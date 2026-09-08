# Multi-Tool AI Agent Ecosystem: LangGraph, Temporal, and Langfuse

This repository contains two distinct, battle-tested architectural implementations of a multi-tool AI Agent powered by **Google Gemini**. Both implementations dynamically decide when to execute tools and loop through tasks until they gather enough information to answer a user's prompt. 

Telemetry, token counts, prompt metrics, and costs are tracked continuously using a local **Langfuse** engine.

---

## Architecture Archetypes

### 1. LangGraph Implementation (`agent.py`)
* **Best For:** Rapid prototyping, visual design experimentation, and modeling complex multi-agent conversations.
* **How it works:** It models your loops visually as a cyclic state graph. LangGraph orchestrates the state machine via nodes and conditional edges.
* **Limitation:** Runs purely in-memory/process; if the host machine crashes mid-loop, active states are lost.

### 2. Temporal Implementation (`agent_temporal.py`)
* **Best For:** Enterprise production infrastructure, heavy long-running background tasks, and critical durability.
* **How it works:** Replaces abstract graph nodes with **Durable Temporal Activities** and native Python `while` loops. 
* **Advantage:** If your server or API goes down mid-execution, Temporal freezes the exact state and resumes precisely where it left off, avoiding duplicate LLM costs and data loss.

---

## Shared Capabilities (The Core Agent)

Both environments share the exact same multi-tool logic:
* **LLM Engine:** Utilizes `gemini-1.5-flash` natively bound to tools.
* **Dynamic Multi-Tool Loops:** Gemini evaluates the prompt and can request parallel tool executions (e.g., retrieving weather or checking population sizes) sequentially until it resolves the answer.
* **Observability:** Leverages Langfuse's `CallbackHandler` to capture nested traces. In the Temporal module, the `workflow_id` is linked as the Langfuse `session_id` to unify infrastructure logs with semantic LLM metrics.

---

## File Structure

```text
├── agent.py               # Cyclic Agent built using LangGraph
├── agent_temporal.py      # Resilient, Durable Agent built using Temporal
├── setup.sh               # Local environment secrets and endpoints
└── README.md              # Project onboarding guide
```

---

## Getting Started

### 1. Fire Up Local Infrastructure
Start your local Temporal dev server engine in a separate terminal:
```bash
temporal server start-dev
```

Launch your local Langfuse instance via Docker:
```bash
docker compose up -d
```

### 2. Install Virtual Environment Dependencies
Ensure your `.venv` is active and install the complete combined stack packages:
```bash
pip install -U langgraph langchain-google-genai langfuse langchain temporalio
```

### 3. Load Credentials (`setup.sh`)
Populate your environment variables with your target endpoints:
```bash
export GOOGLE_API_KEY="AIzaSy..."
export LANGFUSE_PUBLIC_KEY="pk-lf-..."
export LANGFUSE_SECRET_KEY="sk-lf-..."
export LANGFUSE_HOST="http://localhost:3000"
```

### 4. Running the Implementations

**To run the LangGraph prototyping app:**
```bash
source setup.sh
python agent.py
```

**To run the production-grade Temporal durable workflow:**
```bash
source setup.sh
python agent_temporal.py
```

---

## Monitoring Dashboards

* **Temporal Console ([http://localhost:8233](http://localhost:8233)):** Monitor execution heartbeats, fine-grained activity retry lifecycles, and view live execution stack traces.
* **Langfuse Dashboard ([http://localhost:3000](http://localhost:3000)):** Inspect semantic prompt trees, trace system prompt overrides, evaluate agent completions, and audit token API expenses.

