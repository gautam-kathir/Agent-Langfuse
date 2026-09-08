import os
import warnings
from typing import TypedDict, Annotated

# Suppress annoying Google SDK warnings
warnings.filterwarnings("ignore", category=UserWarning, module="google.generativeai")

from langfuse.langchain import CallbackHandler
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

# ==========================================
# 1. Define Your Custom Tools
# ==========================================
@tool
def get_weather(location: str) -> str:
    """Get the current weather for a specific city location."""
    # Simulated response
    return f"The weather in {location} is currently sunny and 72°F."

@tool
def get_population(location: str) -> str:
    """Get the current population count for a given city or location."""
    # Simulated response
    if "san diego" in location.lower():
        return "San Diego has a population of approximately 1.4 million people."
    return f"The population of {location} is roughly 500,000."

# Bundle tools into a list
tools = [get_weather, get_population]

# ==========================================
# 2. Configure State and Gemini Model
# ==========================================
class State(TypedDict):
    messages: Annotated[list, add_messages]

# Initialize model and bind tools natively to Gemini
model = ChatGoogleGenerativeAI(model="gemini-3.6-flash", temperature=0)
model_with_tools = model.bind_tools(tools)

# Define the node that calls Gemini
def call_model(state: State):
    response = model_with_tools.invoke(state["messages"])
    return {"messages": [response]}

# ==========================================
# 3. Construct the Cyclic LangGraph
# ==========================================
workflow = StateGraph(State)

# Add our two main operating nodes
workflow.add_node("agent", call_model)
workflow.add_node("tools", ToolNode(tools)) # Prebuilt LangGraph node to execute tools

# Wire up the loops
workflow.add_edge(START, "agent")

# tools_condition handles checking if the LLM output wants to execute a tool or stop
workflow.add_conditional_edges(
    "agent",
    tools_condition,
)

# After running tools, always loop back to the agent node to let it evaluate the answers
workflow.add_edge("tools", "agent")

app = workflow.compile()

# ==========================================
# 4. Run execution with Langfuse Tracing
# ==========================================
langfuse_handler = CallbackHandler()
config = {"callbacks": [langfuse_handler]}

# Provide a prompt that forces the agent to use BOTH tools sequentially
prompt = "Can you look up the population of San Diego and find out what the weather is like there right now?"
inputs = {"messages": [("user", prompt)]}

print("Starting Agent execution loops...")
response = app.invoke(inputs, config=config)

print("\n--- Final Agent Response ---")
print(response["messages"][-1].content)

