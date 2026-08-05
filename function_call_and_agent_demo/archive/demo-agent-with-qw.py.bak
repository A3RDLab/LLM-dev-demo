import os
from github import Github
import json
from http import HTTPStatus
import dashscope
from typing import Tuple

# 定义颜色代码
GREEN = '\033[92m'
WHITE = '\033[97m'
RESET = '\033[0m'

# 函数定义区
def get_repo_tree(repo_full_name, branch=None):
    token = os.getenv("GITHUB_TOKEN", None)
    g = Github(token)
    repo = g.get_repo(f"{repo_full_name}")
    if branch is None:
        branch = "main"
    tree = repo.get_git_tree(sha=branch, recursive=True)
    tree_str = ""
    for item in tree.tree:
        tree_str += f"{item.path}\n"
    return tree_str

def get_repo_file_content(repo_full_name, file_path, branch=None):
    token = os.getenv("GITHUB_TOKEN", None)
    g = Github(token)
    repo = g.get_repo(f"{repo_full_name}")
    if branch is None:
        branch = "main"
    file_content = repo.get_contents(file_path, ref=branch)
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
            'description': 'The branch name, e.g. master',
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
            'description': 'The branch name, e.g. master',
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

REACT_PROMPT = """Answer the following questions as best you can. You have access to the following tools:

{tool_descs}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can be repeated zero or more times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Question: {query}"""

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

def call_with_messages(prompt):
    messages = [{'role': 'system', 'content': 'You are a helpful assistant.'},
                {'role': 'user', 'content': prompt}]

    response = dashscope.Generation.call(
        dashscope.Generation.Models.qwen_plus,
        messages=messages,
        result_format='message',
    )
    if response.status_code == HTTPStatus.OK:
        return(response['output']['choices'][0]['message']['content'])
    else:
        return('Request id: %s, Status code: %s, error code: %s, error message: %s' % (
            response.request_id, response.status_code,
            response.code, response.message
        ))

def parse_latest_plugin_call(text: str) -> Tuple[str, str]:
    i = text.rfind('\nAction:')
    j = text.rfind('\nAction Input:')
    k = text.rfind('\nObservation:')
    if 0 <= i < j:
        if k < j:
            text = text.rstrip() + '\nObservation:'
            k = text.rfind('\nObservation:')
    if 0 <= i < j < k:
        plugin_name = text[i + len('\nAction:'):j].strip()
        plugin_args = text[j + len('\nAction Input:'):k].strip()
        return plugin_name, plugin_args
    return '', ''

def use_api(tools, response):
    use_toolname, action_input = parse_latest_plugin_call(response)
    if use_toolname == "":
        return "no tool founds"
    action_input = json.loads(action_input)
    try:
        if use_toolname == "get_repo_tree":
            observed_content = available_functions["get_repo_tree"](action_input.get("repo_full_name"), action_input.get("branch"))
        if use_toolname == "get_repo_file_content":
            observed_content = available_functions["get_repo_file_content"](action_input.get("repo_full_name"), action_input.get("file_path"), action_input.get("branch"))
    except Exception as e:
        return f"Error: {e}"
    return observed_content

def color_text(text: str) -> str:
    # 将Thought部分用绿色，其他部分用白色
    colored_text = ""
    lines = text.split('\n')
    for line in lines:
        if line.startswith("Thought:"):
            colored_text += f"{GREEN}{line}{RESET}\n"
        else:
            colored_text += f"{WHITE}{line}{RESET}\n"
    return colored_text

prompt = build_planning_prompt(TOOLS, query="分析https://github.com/shadow1ng/fscan，查看相关源码，告诉我redis系统反弹shell相关的代码在哪里，并解释这些代码的含义。")
print(prompt)
response = call_with_messages(prompt)
print(color_text(response))
while "Final Answer" not in response:
    api_output = use_api(TOOLS, response)
    if api_output == "no tool founds":
        continue
    prompt = prompt + response + "Observation:\n" + api_output
    print("Observation:\n" + api_output)
    response = call_with_messages(prompt)
    print(color_text(response))

