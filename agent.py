import os
from langfuse.langchain import CallbackHandler
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

# 2. Define your Graph State
class State(TypedDict):
    messages: Annotated[list, add_messages]

# 3. Initialize the Gemini Model
# Using 'gemini-1.5-flash' for fast text generation tasks
model = ChatGoogleGenerativeAI(model="gemini-3.6-flash")

# 4. Define a simple LLM Node
def call_gemini(state: State):
    response = model.invoke(state["messages"])
    return {"messages": [response]}

# 5. Build and compile the Graph
workflow = StateGraph(State)
workflow.add_node("gemini_node", call_gemini)
workflow.add_edge(START, "gemini_node")
workflow.add_edge("gemini_node", END)
app = workflow.compile()

# 6. Execute the Graph with Langfuse Callbacks attached
langfuse_handler = CallbackHandler()
config = {"callbacks": [langfuse_handler]}

inputs = {"messages": [("user", "Explain quantum computing in one sentence.")]}
response = app.invoke(inputs, config=config)

print(response["messages"][-1].content)

