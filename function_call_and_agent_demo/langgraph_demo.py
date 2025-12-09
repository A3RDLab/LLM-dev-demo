import os
import logging
from dotenv import load_dotenv
from github import Github
import operator
from langchain_core.messages import HumanMessage, AnyMessage
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from typing import TypedDict, Annotated, Literal
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from typing import List

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE")


# Define tools using LangChain's @tool decorator
@tool
def get_repo_tree(repo_full_name: str, branch: str | None = None) -> str:
    """
    Get the directory structure of a repository.
    """
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise ValueError("GITHUB_TOKEN environment variable is required")
    
    try:
        g = Github(token)
        repo = g.get_repo(repo_full_name)
    except Exception as e:
        raise RuntimeError(f"Failed to access repository {repo_full_name}: {str(e)}")
    if branch is None:
        branch = "main"
    tree = repo.get_git_tree(sha=branch, recursive=True)
    tree_str = ""
    for item in tree.tree:
        tree_str += f"{item.path}\n"
    return tree_str


@tool
def get_repo_file_content(repo_full_name: str, file_path: str, branch: str | None = None) -> str:
    """
    Get the content of a file in a repository.
    """
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise ValueError("GITHUB_TOKEN environment variable is required")
    
    try:
        g = Github(token)
        repo = g.get_repo(repo_full_name)
    except Exception as e:
        raise RuntimeError(f"Failed to access repository {repo_full_name}: {str(e)}")
    if branch is None:
        branch = "main"
    try:
        file_content = repo.get_contents(file_path, ref=branch)
    except Exception as e:
        raise RuntimeError(f"Failed to get file content from {file_path}: {str(e)}")
    return file_content.decoded_content.decode("utf-8")


# Define tools list
TOOLS = [get_repo_tree, get_repo_file_content]

class AgentState(TypedDict):
    """
    Define the agent state.

    Attributes:
        messages: List of conversation messages. Use Annotated and operator.add to specify
                  that new messages should be appended to the list, not overwrite it.
    """
    messages: Annotated[List[AnyMessage], operator.add]


# Initialize LLM model
model = ChatOpenAI(model="Qwen/Qwen3-235B-A22B", openai_api_base="https://api.siliconflow.cn/v1/", temperature=0).bind_tools(TOOLS)

def call_model(state: AgentState):
    messages = state['messages']
    response = model.invoke(messages)
    return {"messages": [response]}

# Create a ToolNode with the actual tool functions
tool_node = ToolNode(TOOLS)

def should_continue(state: AgentState) -> Literal["tools", "__end__"]:
    last_message = state['messages'][-1]
    if last_message.tool_calls:
        return "tools"
    else:
        return "__end__"


# Build the workflow
workflow = StateGraph(AgentState)

# Add nodes
workflow.add_node("agent", call_model)
workflow.add_node("tools", tool_node)

# Set entry point
workflow.set_entry_point("agent")

# Add conditional edges
workflow.add_conditional_edges(
    "agent",
    should_continue,
    {
        "tools": "tools",
        "__end__": END
    }
)

# Add normal edge
workflow.add_edge("tools", "agent")

# Compile the workflow into a runnable application
app = workflow.compile()

# Generate and save the graph visualization
try:
    image_data = app.get_graph().draw_mermaid_png()
    with open("agent_graph.png", "wb") as f:
        f.write(image_data)
    print("Agent architecture saved as agent_graph.png")
except ImportError:
    print("Please install pygraphviz to generate visualization: pip install pygraphviz")

# Now we can invoke the agent
inputs = {"messages": [HumanMessage(content="https://github.com/ai-shifu/ChatALL 是如何接入OpenAI的？")]}

# Stream the execution step by step
for step_output in app.stream(inputs, stream_mode="values"):
    for message in step_output['messages']:
        message.pretty_print()
    print("\n---\n")

# final_state = app.invoke(inputs)
# final_answer = final_state['messages'][-1]
# print(final_answer.content)
