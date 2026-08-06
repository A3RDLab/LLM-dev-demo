import os
import logging
from pathlib import Path

from dotenv import load_dotenv
from github import Github
import json
from http import HTTPStatus
from openai import OpenAI
from typing import Tuple, List, Dict, Any

# 加载仓库根目录 .env（API_KEY / API_BASE / MODEL，见 .env.example）
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler('agent_debug.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Function definitions remain the same
def _github_client() -> Github:
    """有 GITHUB_TOKEN 则鉴权（限额高），没有则匿名访问（仅公开仓库，60次/小时）"""
    token = os.getenv("GITHUB_TOKEN")
    return Github(token) if token else Github()

def get_repo_tree(repo_full_name: str, branch: str | None = None) -> str:
    try:
        g = _github_client()
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

def get_repo_file_content(repo_full_name: str, file_path: str, branch: str | None = None) -> str:
    try:
        g = _github_client()
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

# Define tools in OpenAI format
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_repo_tree",
            "description": "Get the directory structure of a repository",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo_full_name": {
                        "type": "string",
                        "description": "The full name of the repository, e.g. openai/gpt-3"
                    },
                    "branch": {
                        "type": "string",
                        "description": "The branch name, e.g. master (defaults to 'main' if not provided)"
                    }
                },
                "required": ["repo_full_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_repo_file_content",
            "description": "Get the content of a file in a repository",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo_full_name": {
                        "type": "string",
                        "description": "The full name of the repository, e.g. openai/gpt-3"
                    },
                    "file_path": {
                        "type": "string",
                        "description": "The path to the file in the repository"
                    },
                    "branch": {
                        "type": "string",
                        "description": "The branch name, e.g. master (defaults to 'main' if not provided)"
                    }
                },
                "required": ["repo_full_name", "file_path"]
            }
        }
    }
]

available_functions = {
    "get_repo_tree": get_repo_tree,
    "get_repo_file_content": get_repo_file_content
}

def call_with_messages(messages: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Make a streaming API call to the LLM with tool support.

    流式要点：content 片段实时逐字打印（最终答案打字机效果）；
    tool_calls 片段按 index 归位累积——首个片段携带 id 与函数名，
    后续片段只是 arguments 的文本碎片。返回结构与非流式 message 等价。
    """
    api_key = os.getenv("API_KEY")
    if not api_key:
        raise ValueError("API_KEY environment variable is required")
    
    client = OpenAI(
        api_key=api_key,
        base_url=os.getenv("API_BASE", "https://api.siliconflow.cn/v1/")
    )

    try:
        stream = client.chat.completions.create(
            model=os.getenv("MODEL", "Pro/deepseek-ai/DeepSeek-V3"),
            messages=messages,
            tools=TOOLS,
            temperature=0.5,
            stream=True
        )
        content_parts = []
        tool_calls = {}  # index -> 累积中的工具调用
        answer_started = False

        for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta is None:
                continue
            if delta.content:
                if not answer_started:
                    print("\nFinal Answer (streaming):", flush=True)
                    answer_started = True
                print(delta.content, end="", flush=True)
                content_parts.append(delta.content)
            for tc in delta.tool_calls or []:
                acc = tool_calls.setdefault(tc.index, {"id": "", "function": {"name": "", "arguments": ""}})
                if tc.id:
                    acc["id"] = tc.id
                if tc.function and tc.function.name:
                    acc["function"]["name"] = tc.function.name
                if tc.function and tc.function.arguments:
                    acc["function"]["arguments"] += tc.function.arguments

        if answer_started:
            print()  # 流式回答结束补个换行
        return {
            "role": "assistant",
            "content": "".join(content_parts) or None,
            "tool_calls": [dict(tool_calls[i], type="function") for i in sorted(tool_calls)] or None,
        }
    except Exception as e:
        raise RuntimeError(f"Failed to communicate with LLM: {str(e)}")

def execute_function(tool_call: Dict[str, Any]) -> str:
    """Execute a function based on tool call."""
    function_name = tool_call["function"]["name"]
    function_args = json.loads(tool_call["function"]["arguments"])
    
    if function_name in available_functions:
        logger.debug(f"Executing function: {function_name} with args: {function_args}")
        return available_functions[function_name](**function_args)
    
    raise ValueError(f"Unknown function: {function_name}")

def run_agent(query: str, max_iterations: int = 10) -> str:
    """Run the agent with the given query."""
    logger.info(f"Starting agent with query: {query}")

    def _preview(text: Any, limit: int = 300) -> str:
        """日志截断：工具结果可能有几千行（如仓库目录树），全量打印会刷屏"""
        s = str(text)
        return s if len(s) <= limit else s[:limit] + f"... [共{len(s)}字符，已截断]"

    messages = [
        {"role": "system", "content": "You are a helpful assistant for software development tasks."},
        {"role": "user", "content": query}
    ]
    
    iteration = 0
    while iteration < max_iterations:
        try:
            logger.info("Calling LLM with messages:")
            for msg in messages:
                logger.info(f"{msg['role'].capitalize()}: {_preview(msg['content'])}")
            
            response = call_with_messages(messages)
            logger.info(f"Received LLM response: {_preview(response['content'])} | tool_calls: {len(response['tool_calls'] or [])} 个")
            
            if not response["tool_calls"]:
                # No tool calls, final answer has already been streamed to console
                logger.info("No tool calls detected, returning final answer")
                return response["content"]
            
            # Handle tool calls
            if response["tool_calls"]:
                logger.info(f"Received {len(response['tool_calls'])} tool calls")
                for i, tool_call in enumerate(response["tool_calls"]):
                    logger.info(f"Tool call {i+1}: {tool_call['function']['name']} with args: {tool_call['function']['arguments']}")
                
                # First add the assistant message with tool calls
                messages.append({
                    "role": response["role"],
                    "content": response["content"],
                    "tool_calls": response["tool_calls"]
                })
                
                # Then add tool responses
                for tool_call in response["tool_calls"]:
                    function_response = execute_function(tool_call)
                    logger.info(f"Tool execution result for {tool_call['function']['name']}: {_preview(function_response, 200)}")
                    messages.append({
                        "role": "tool",
                        "content": function_response,
                        "tool_call_id": tool_call["id"],
                        "name": tool_call["function"]["name"]
                    })
            
            iteration += 1
            
        except Exception as e:
            # 不要把错误当正常结果 return，否则调用方会把错误误认为最终答案
            logger.error(f"Error in iteration {iteration}: {str(e)}")
            raise RuntimeError(f"Agent failed in iteration {iteration}: {str(e)}") from e
    
    error_msg = "Agent exceeded maximum iterations without reaching a final answer"
    logger.error(error_msg)
    raise RuntimeError(error_msg)

if __name__ == "__main__":
    try:
        query = "https://github.com/ai-shifu/ChatALL 是如何接入OpenAI的？"
        logger.info(f"Starting agent with query: {query}")
        final_answer = run_agent(query)
        logger.info(f"Agent completed successfully with final answer ({len(final_answer or '')} chars, already streamed to console)")
    except Exception as e:
        logger.error(f"Agent failed with error: {str(e)}")
        print(f"Error: {str(e)}")
