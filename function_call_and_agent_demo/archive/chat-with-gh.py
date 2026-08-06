from github import Github
import numpy as np
import streamlit as st
import tiktoken
from openai import OpenAI
import logging
from redis import Redis
from redis.commands.search.query import Query
import os
from datetime import date, datetime, timedelta
import json

# Define a function to get the session id and the remote ip 
# Caution: this function is implemented in a hacky way and may break in the future
from streamlit import runtime
from streamlit.runtime.scriptrunner import get_script_run_ctx

GPT_MODEL = "gpt-4-turbo"
client = OpenAI()

# 函数定义区
# 调用github库读取一个repo的目录结构，并以树的形式的字符串返回
def get_repo_tree(repo_full_name, branch=None):
    # 从环境变量里读取github的token
    token = os.getenv("GITHUB_TOKEN", None)
    # 创建一个github对象
    g = Github(token)
    # 获取一个repo对象
    repo = g.get_repo(f"{repo_full_name}")
    # 获取repo的目录结构
    # Ensure branch is not None
    if branch is None:
        branch = "master"
    tree = repo.get_git_tree(sha=branch, recursive=True)
    # 构造树形式的字符串
    tree_str = ""
    for item in tree.tree:
        tree_str += f"{item.path}\n"
    return tree_str

# 调用github库读取一个repo中的某个文件的内容
def get_repo_file_content(repo_full_name, file_path, branch=None):
    # 从环境变量里读取github的token
    token = os.getenv("GITHUB_TOKEN", None)
    # 创建一个github对象
    g = Github(token)
    # 获取一个repo对象
    repo = g.get_repo(f"{repo_full_name}")
    # 获取文件内容
    # Ensure branch is not None
    if branch is None:
        branch = "master"
    file_content = repo.get_contents(file_path, ref=branch)
    return file_content.decoded_content.decode("utf-8")

# 按照GPT-4的API为上述函数写tools描述
# 示例如下：
# def get_current_weather(location, unit="fahrenheit"):
# ...

#     tools = [
#         {
#             "type": "function",
#             "function": {
#                 "name": "get_current_weather",
#                 "description": "Get the current weather in a given location",
#                 "parameters": {
#                     "type": "object",
#                     "properties": {
#                         "location": {
#                             "type": "string",
#                             "description": "The city and state, e.g. San Francisco, CA",
#                         },
#                         "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
#                     },
#                     "required": ["location"],
#                 },
#             },
#         }
#     ]
tools = [
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
                        "description": "The full name of the repository, e.g. openai/gpt-3",
                    },
                    "branch": {"type": "string", "description": "The branch name, e.g. master"},
                },
                "required": ["repo_full_name"],
            },
        },
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
                        "description": "The full name of the repository, e.g. openai/gpt-3",
                    },
                    "file_path": {"type": "string", "description": "The path to the file in the repository"},
                    "branch": {"type": "string", "description": "The branch name, e.g. master"},
                },
                "required": ["repo_full_name", "file_path"],
            },
        },
    },
]

available_functions = {
    "get_repo_tree": get_repo_tree,
    "get_repo_file_content": get_repo_file_content,
}

# Set up logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
# The streamlit script starts here
logging.info("Starting Streamlit script ...")


st.set_page_config(
    page_title="Chat with Github - just a demo",
    page_icon="🤖",
)
st.subheader("Chat with Github - just a demo")

if "messages" not in st.session_state.keys():
    # Initialize the session_state.messages
    st.session_state.messages = [{"role": "system", "content": "你是一个帮助用户解读Github上代码库的软件专家。"}]
else: # Since streamlit script is executed every time a widget is changed, this "else" is not necessary, but improves readability
    # Display chat messages
    for message in st.session_state.messages:
        if message["role"] == "user" or message["role"] == "assistant":
            # 判断是否存在content
            if "content" in message.keys():
                with st.chat_message(message["role"]):
                    st.write(message["content"])

# Check the api_key to call OpenAI
try:
    os.getenv("OPENAI_API_KEY")
except:
    logging.error("KEY is not set.")
    st.error('KEY未设置，请联系我的主人。')
    st.stop() 

# User-provided prompt
if user_prompt := st.chat_input('在此输入您的问题'):
    logging.info(f"User's prompt: {user_prompt}")
    with st.chat_message("user"):
        st.write(user_prompt)
        st.session_state.messages.append({"role": "user", "content": user_prompt})
    with st.chat_message("assistant"):
        with st.spinner("人工智能正在思考..."):

            gpt_response = client.chat.completions.create(
                    model=GPT_MODEL,
                    messages=st.session_state.messages,
                    tools=tools,
                    )
            response_msg = gpt_response.choices[0].message
            tool_calls = response_msg.tool_calls
            if tool_calls:
                st.session_state.messages.append({"role": "assistant", "tool_calls": response_msg.tool_calls})
                for tool_call in tool_calls:
                    function_args = json.loads(tool_call.function.arguments)
                    logging.info(f"Function call: {tool_call.function.name} with arguments: {function_args}")
                    if tool_call.function.name == "get_repo_tree":
                        function_response = available_functions["get_repo_tree"](function_args.get("repo_full_name"), function_args.get("branch"))
                    if tool_call.function.name == "get_repo_file_content":
                        function_response = available_functions["get_repo_file_content"](function_args.get("repo_full_name"), function_args.get("file_path"), function_args.get("branch"))
                    logging.info(f"Function {tool_call.function.name} responsed")
                    st.session_state.messages.append(
                        {
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": tool_call.function.name,
                            "content": function_response,
                        })
                secondary_gpt_response = client.chat.completions.create(
                    model=GPT_MODEL,
                    messages=st.session_state.messages,
                    )
                secondary_gpt_response_msg = secondary_gpt_response.choices[0].message
                if secondary_gpt_response_msg.role == "assistant":
                        st.write(secondary_gpt_response_msg.content)
                        st.session_state.messages.append({"role": "assistant", "content": secondary_gpt_response_msg.content})
            else:
                if response_msg.role == "assistant":
                    st.write(response_msg.content)
                    st.session_state.messages.append({"role": "assistant", "content": response_msg.content})

st.write("**注意：人工智能生成内容仅供参考。**")
logging.info("Streamlit script ended.")