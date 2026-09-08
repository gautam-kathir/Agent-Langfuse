import os
import json
import asyncio
from temporalio.worker.workflow_sandbox import SandboxedWorkflowRunner, SandboxRestrictions
from datetime import timedelta
from typing import List, Dict, Any

from temporalio import workflow, activity
from temporalio.client import Client
from temporalio.worker import Worker

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langchain_core.tools import tool
from langfuse.langchain import CallbackHandler

# =====================================================================
# 1. Define Local Tools & Activities
# =====================================================================
@tool
def get_weather(location: str) -> str:
    """Get the current weather for a specific city location."""
    return f"The weather in {location} is currently sunny and 72°F."

@tool
def get_population(location: str) -> str:
    """Get the current population count for a given city or location."""
    if "san diego" in location.lower():
        return "San Diego has a population of approximately 1.4 million people."
    return f"The population of {location} is roughly 500,000."

tools_map = {"get_weather": get_weather, "get_population": get_population}
tools_list = list(tools_map.values())

@activity.defn
async def call_gemini_activity(messages_json: str) -> Dict[str, Any]:
    """Activity that handles the flaky network call to Gemini."""
    # Reconstruct messages from serialization
    raw_msgs = json.loads(messages_json)
    messages = []
    for m in raw_msgs:
        if m["type"] == "human":
            messages.append(HumanMessage(content=m["content"]))
        elif m["type"] == "ai":
            messages.append(AIMessage(content=m["content"], tool_calls=m.get("tool_calls", [])))
        elif m["type"] == "tool":
            messages.append(ToolMessage(content=m["content"], tool_call_id=m["tool_call_id"]))

    # Initialize model with tool binding
    model = ChatGoogleGenerativeAI(model="gemini-3.6-flash", temperature=0)
    model_with_tools = model.bind_tools(tools_list)
    
    # Optional: Attach Langfuse tracing callback
    langfuse_handler = CallbackHandler()
    
    response = await model_with_tools.ainvoke(messages, config={"callbacks": [langfuse_handler]})
    
    # Serialize back safely to pass through Temporal's boundary
    return {
        "content": response.content,
        "tool_calls": response.tool_calls
    }

@activity.defn
async def execute_tool_activity(tool_call: Dict[str, Any]) -> Dict[str, Any]:
    """Activity that safely runs a selected tool locally."""
    name = tool_call["name"]
    args = tool_call["args"]
    tool_id = tool_call["id"]
    
    if name in tools_map:
        result = tools_map[name].invoke(args)
    else:
        result = f"Error: Tool {name} not found."
        
    return {
        "content": str(result),
        "tool_call_id": tool_id
    }

# =====================================================================
# 2. Define the Durable Workflow Engine
# =====================================================================
@workflow.defn
class MultiToolAgentWorkflow:
    @workflow.run
    async def run(self, user_prompt: str) -> str:
        # State inside a Temporal workflow is purely a native Python list
        messages = [{"type": "human", "content": user_prompt}]
        
        while True:
            # 1. Call Gemini to see what step to take next
            response = await workflow.execute_activity(
                call_gemini_activity,
                json.dumps(messages),
                start_to_close_timeout=timedelta(seconds=30)
            )
            
            # Save the agent's thought/decision to our list
            messages.append({
                "type": "ai", 
                "content": response["content"], 
                "tool_calls": response["tool_calls"]
            })
            
            # 2. Check if the model requested any tool calls
            tool_calls = response["tool_calls"]
            if not tool_calls:
                # No more tools requested. We are done!
                return response["content"]
            
            # 3. Parallelize executing tools requested in this loop iteration
            tool_tasks = [
                workflow.execute_activity(
                    execute_tool_activity,
                    tc,
                    start_to_close_timeout=timedelta(seconds=10)
                )
                for tc in tool_calls
            ]
            
            tool_results = await asyncio.gather(*tool_tasks)
            
            # 4. Feed tool results directly back into the state history
            for res in tool_results:
                messages.append({
                    "type": "tool",
                    "content": res["content"],
                    "tool_call_id": res["tool_call_id"]
                })

async def main():
    client = await Client.connect("localhost:7233")

    # Tell the Temporal Sandbox to ignore AI framework internals
    # This prevents the RestrictedWorkflowAccessError
    custom_restrictions = SandboxRestrictions.default.with_passthrough_modules(
        "langchain_google_genai",
        "langfuse",
        "langchain_core",
        "google",
	"langchain"
    )

    worker = Worker(
        client,
        task_queue="agent-task-queue",
        workflows=[MultiToolAgentWorkflow],
        activities=[call_gemini_activity, execute_tool_activity],
        # Add the restrictions parameter right here:
	workflow_runner=SandboxedWorkflowRunner(restrictions=custom_restrictions)
    )
    
    async with worker:
        print("Temporal Worker initialized. Processing incoming agent tasks...")
        
        # Fire off an invocation to our workflow execution engine
        prompt = "Can you check the population of San Diego and see what the weather is like there?"
        print(f"Triggering workflow with prompt: '{prompt}'")
        
        result = await client.execute_workflow(
            MultiToolAgentWorkflow.run,
            prompt,
            id="agent-run-001",
            task_queue="agent-task-queue",
        )
        
        print("\n--- Final Agent Response From Temporal Workflow ---")
        print(result)

if __name__ == "__main__":
    # Make sure your setup.sh is sourced before running
    asyncio.run(main())

