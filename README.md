# LangGraph Multi-Tool Agent with Gemini & Langfuse

This repository contains a minimal, production-ready AI agent built using **LangGraph**. The agent uses **Google Gemini 1.5** to dynamically decide when to execute tools and loops through tasks until it gathers all necessary information to answer a user's prompt. All agent operations are tracked locally or in the cloud using **Langfuse**.

## What the Code Does

When a user asks a complex question that requires external data, the script orchestrates the following automated loop:

1. **Evaluates Intent:** Google Gemini reads the user's prompt and determines if it needs specialized tools to answer the request.
2. **Executes Tools:** If required, LangGraph pauses the model and routes control to a dedicated execution node to fetch data from custom tools (e.g., pulling local weather or city population numbers).
3. **Appends & Loops:** The data fetched by the tools is appended to a shared memory state. The workflow loops back to Gemini, allowing it to inspect the new data.
4. **Finalizes Response:** Once the model confirms it has all the details it needs, it breaks out of the loop and returns a cohesive conversational summary to the terminal.

## Core Features

* **State Management:** Uses LangGraph's unified memory system (`State`) to pass chat history cleanly between nodes.
* **Cyclic Logic:** Rather than a simple linear pipeline, the agent loops dynamically based on how many tool calls the LLM requests.
* **Observability Ecosystem:** Uses Langfuse's standard `CallbackHandler` to capture every step of the graph, showing exactly how long individual nodes took to execute, what prompts were sent, and token metrics.

## Visual Workflow Diagram

```text
[START] ──> [ Agent Node (Gemini) ] ──(Has Tool Requests?)──> YES ──> [ Tools Node ]
                     │                                                      │
                     └── (No Tool Requests / Finished) ──> [END] <──────────┘
```

## How to Run It

1. Set up your environment variables via your `setup.sh` file.
2. Run the application:
   ```bash
   source setup.sh
   python agent.py
   ```
3. Open your browser to `http://localhost:3000` to review the execution tree inside your local Langfuse instance.
