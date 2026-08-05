import os
import logging
from github import Github
import json
from http import HTTPStatus
from openai import OpenAI
from typing import Tuple

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler('agent_debug.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 函数定义区
def get_repo_tree(repo_full_name: str, branch: str | None = None) -> str:
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

def get_repo_file_content(repo_full_name: str, file_path: str, branch: str | None = None) -> str:
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

# 参考如下示例为上述函数写tools描述
# TOOLS = [
#     {
#         'name_for_human':
#         '夸克搜索',
#         'name_for_model':
#         'quark_search',
#         'description_for_model':
#         '夸克搜索是一个通用搜索引擎，可用于访问互联网、查询百科知识、了解时事新闻等。',
#         'parameters': [{
#             'name': 'search_query',
#             'description': '搜索关键词或短语',
#             'required': True,
#             'schema': {
#                 'type': 'string'
#             },
#         }],
#     },
#     {
#         'name_for_human':
#         '通义万相',
#         'name_for_model':
#         'image_gen',
#         'description_for_model':
#         '通义万相是一个AI绘画（图像生成）服务，输入文本描述，返回根据文本作画得到的图片的URL',
#         'parameters': [{
#             'name': 'query',
#             'description': '中文关键词，描述了希望图像具有什么内容',
#             'required': True,
#             'schema': {
#                 'type': 'string'
#             },
#         }],
#     },
# ]
TOOLS = [
    {
        'name_for_human': '获取repo目录结构',
        'name_for_model': 'get_repo_tree',
        'description_for_model': 'Get the directory structure of a repository',
        'parameters': [{
            'name': 'repo_full_name',
            'description': 'The full name of the repository, e.g. openai/gpt-3',
            'required': True,
            'schema': {
                'type': 'string'
            },
        }, {
            'name': 'branch',
            'description': 'The branch name, e.g. master (defaults to "main" if not provided)',
            'required': False,
            'schema': {
                'type': 'string'
            },
        }],
    },
    {
        'name_for_human': '获取repo文件内容',
        'name_for_model': 'get_repo_file_content',
        'description_for_model': 'Get the content of a file in a repository',
        'parameters': [{
            'name': 'repo_full_name',
            'description': 'The full name of the repository, e.g. openai/gpt-3',
            'required': True,
            'schema': {
                'type': 'string'
            },
        }, {
            'name': 'file_path',
            'description': 'The path to the file in the repository',
            'required': True,
            'schema': {
                'type': 'string'
            },
        }, {
            'name': 'branch',
            'description': 'The branch name, e.g. master (defaults to "main" if not provided)',
            'required': False,
            'schema': {
                'type': 'string'
            },
        }],
    },
]

available_functions = {
    "get_repo_tree": get_repo_tree,
    "get_repo_file_content": get_repo_file_content,
}

TOOL_DESC = """{name_for_model}: Call this tool to interact with the {name_for_human} API. What is the {name_for_human} API useful for? {description_for_model} Parameters: {parameters} Format the arguments as a JSON object."""

REACT_PROMPT = """I am trying to answer the questions: {query}

I have access to the following tools:

{tool_descs}

I will write exactly one of the these elements per response:

- Thought: I always think about what to do, analyze the problem step by step, and explain my reasoning process.
- Action: the action to take, should be one of [{tool_names}]. Action Input: the input to the action, should be a valid JSON object.
- Observation: the result of the action.
- Final Answer: the final answer to the original question.

I NEVER guess or assume repository structures, file contents, or code details based on my own knowledge, but use the provided tools to get REAL data from the GitHub repository.
The results of 'Observation' should always be get by tool calls, I NEVER make up any content of 'Observation'.

Begin!
"""

def build_planning_prompt(TOOLS, query):
    tool_descs = []
    tool_names = []
    for info in TOOLS:
        tool_descs.append(
            TOOL_DESC.format(
                name_for_model=info['name_for_model'],
                name_for_human=info['name_for_human'],
                description_for_model=info['description_for_model'],
                parameters=json.dumps(
                    info['parameters'], ensure_ascii=False),
            )
        )
        tool_names.append(info['name_for_model'])
    tool_descs = '\n\n'.join(tool_descs)
    tool_names = ','.join(tool_names)

    prompt = REACT_PROMPT.format(tool_descs=tool_descs, tool_names=tool_names, query=query)
    return prompt

def call_with_messages(prompt: str) -> str:
    """Make a streaming API call to the LLM and handle the response.
    
    Args:
        prompt: The input prompt to send to the LLM
        
    Returns:
        The accumulated response content from the LLM
        
    Raises:
        RuntimeError: If the API call fails or returns an error
    """
    api_key = os.getenv("API_KEY")
    if not api_key:
        raise ValueError("API_KEY environment variable is required")
    
    try:
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.siliconflow.cn/v1/"
        )

        messages = [{'role': 'system', 'content': 'You is a helpful assistant in software developing.'},
                    {'role': 'assistant', 'content': prompt}]

        reasoning_content = ""  # 记录完整思考过程
        answer_content = ""     # 记录完整回复
        is_answering = False    # 标记是否开始回复
        has_reasoning = False   # 标记模型是否具有思考能力
        current_line = ""       # 用于累积当前行的内容
        
        # 创建流式请求
        completion = client.chat.completions.create(
            model="Qwen/Qwen2.5-Coder-32B-Instruct",
            messages=messages,
            stream=True,
            stop=["Observation:"]
        )

        for chunk in completion:
            if not chunk.choices:
                if hasattr(chunk, 'usage'):
                    pass
            else:
                delta = chunk.choices[0].delta
                
                if hasattr(delta, 'reasoning_content') and delta.reasoning_content is not None:
                    if not has_reasoning:
                        has_reasoning = True
                        print(f"\nAI 正在思考...")
                    
                    print(f"\033[37m{delta.reasoning_content}\033[0m", end='', flush=True)
                    reasoning_content += delta.reasoning_content
                
                elif hasattr(delta, 'content') and delta.content is not None:
                    if not is_answering:
                        if has_reasoning:
                            print(f"\n\nAI 回复:", end='', flush=True)
                        else:
                            print(f"\nAI 回复:", end='', flush=True)
                        is_answering = True
                    
                    print(delta.content, end='', flush=True)
                    current_line += delta.content
                    answer_content += delta.content
        
        # Handle any remaining content in current_line
        if current_line and not is_answering:
            print(current_line)
        
        return answer_content

    except Exception as e:
        raise RuntimeError(f"Failed to communicate with LLM: {str(e)}")

def parse_latest_plugin_call(text: str) -> Tuple[str, str]:
    """Parse the latest plugin call from the response text.
    
    Args:
        text: The response text containing plugin call information
        
    Returns:
        A tuple containing (plugin_name, plugin_args) if found, 
        otherwise empty strings
    """
    action_start = text.rfind('\nAction:')
    action_input_start = text.rfind('\nAction Input:')
    observation_start = text.rfind('\nObservation:')
    
    # Ensure we have complete action and action input
    if 0 <= action_start < action_input_start:
        # If observation is missing or appears before action input,
        # add it to ensure proper parsing
        if observation_start < action_input_start:
            text = text.rstrip() + '\nObservation:'
            observation_start = text.rfind('\nObservation:')
    
    # We have complete action, action input and observation
    if 0 <= action_start < action_input_start < observation_start:
        plugin_name = text[action_start + len('\nAction:'):action_input_start].strip()
        plugin_args = text[action_input_start + len('\nAction Input:'):observation_start].strip()
        return plugin_name, plugin_args
    
    return '', ''

def use_api(tools, response):
    logger.debug(f"\nRaw response text:\n{response}")
    
    use_toolname, action_input = parse_latest_plugin_call(response)
    if use_toolname == "":
        logger.debug("No tool call found in response")
        return "no tool found"
    
    logger.debug(f"Parsed tool name: {use_toolname}")
    logger.debug(f"Parsed action input: {action_input}")
    
    try:
        action_input = json.loads(action_input)
        logger.debug(f"Decoded action input: {action_input}")
        
        if use_toolname == "get_repo_tree":
            logger.debug("Calling get_repo_tree function")
            observed_content = available_functions["get_repo_tree"](
                action_input.get("repo_full_name"), 
                action_input.get("branch")
            )
            
        elif use_toolname == "get_repo_file_content":
            logger.debug("Calling get_repo_file_content function") 
            observed_content = available_functions["get_repo_file_content"](
                action_input.get("repo_full_name"),
                action_input.get("file_path"),
                action_input.get("branch")
            )
            
        logger.debug(f"Function call successful. Result length: {len(observed_content)}")
        return observed_content
        
    except Exception as e:
        logger.error(f"Error in use_api: {str(e)}")
        return f"Error: {e}"

def run_agent(query: str, max_iterations: int = 10) -> str:
    """Run the agent with the given query.
    
    Args:
        query: The input query to process
        max_iterations: Maximum number of iterations to run
        
    Returns:
        The final answer from the agent
        
    Raises:
        RuntimeError: If the agent exceeds the maximum iterations
    """
    prompt = build_planning_prompt(TOOLS, query)
    print(prompt)
    
    response = call_with_messages(prompt)
    iteration = 0
    
    while "Final Answer" not in response and iteration < max_iterations:
        api_output = use_api(TOOLS, response)
        if api_output == "no tool founds":
            iteration += 1
            continue
            
        prompt = prompt + response + "Observation:\n" + api_output
        print("\nObservation:\n" + api_output)
        response = call_with_messages(prompt)
        iteration += 1
    
    if iteration >= max_iterations:
        raise RuntimeError("Agent exceeded maximum iterations without reaching a final answer")
    
    return response

if __name__ == "__main__":
    try:
        # query = "分析https://github.com/shadow1ng/fscan，查看相关源码，告诉我redis系统反弹shell相关的代码在哪里，并解释这些代码的含义。"
        query = "https://github.com/ai-shifu/ChatALL 是如何接入OpenAI的？。"
        final_answer = run_agent(query)
        print(f"\nFinal Answer:\n{final_answer}")
    except Exception as e:
        print(f"Error: {str(e)}")
