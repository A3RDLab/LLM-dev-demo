"""
MCP Client + Agent 示例（Streamable HTTP 传输）
=================================================
连接 mcp_server_demo.py 提供的 MCP 服务器，
把远端工具加载进 LangGraph agent，演示完整的 MCP 工具调用流程。

使用步骤：
    1. 先启动服务器:  python mcp_server_demo.py
    2. 再运行本脚本:  python mcp_client_agent_demo.py

依赖：pip install "mcp[cli]" langchain-mcp-adapters langgraph langchain-openai
运行前请设置环境变量 API_KEY（可参考根目录 .env.example）

说明：MCP 支持三种传输——
    - stdio：本地子进程通信（IDE 插件常用）
    - sse：已被 Streamable HTTP 取代，不建议新项目使用
    - streamable-http：当前推荐的 HTTP 传输，本示例使用它
"""

import os
import asyncio
import argparse

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

# ===== 命令行参数（与仓库其他 demo 保持一致的风格） =====
parser = argparse.ArgumentParser(description='MCP Client Agent 示例')
parser.add_argument('--model', type=str, default='Pro/deepseek-ai/DeepSeek-V3',
                    help='指定使用的模型名称')
parser.add_argument('--api_key', type=str, default=None,
                    help='指定API密钥（默认使用环境变量API_KEY）')
parser.add_argument('--base_url', type=str, default="https://api.siliconflow.cn/v1/",
                    help='指定API基础URL')
parser.add_argument('--mcp_url', type=str, default="http://localhost:8000/mcp",
                    help='MCP 服务器的 Streamable HTTP 地址')
parser.add_argument('--query', type=str,
                    default='北京和上海今天天气怎么样？顺便告诉我现在几点了',
                    help='测试用问题')
args = parser.parse_args()

api_key = args.api_key if args.api_key else os.getenv("API_KEY")

model = ChatOpenAI(
    model=args.model,
    api_key=api_key,
    base_url=args.base_url,
    temperature=0.2,
)


async def main():
    # 通过 Streamable HTTP 连接 MCP 服务器
    async with streamablehttp_client(args.mcp_url) as (read, write, _):
        async with ClientSession(read, write) as session:
            # 初始化连接（协议握手）
            await session.initialize()

            # 发现并加载远端工具为 LangChain tools
            tools = await load_mcp_tools(session)
            print(f"已加载 {len(tools)} 个 MCP 工具: {[t.name for t in tools]}")

            # 交给 LangGraph 预构建 agent 完成推理与工具调用
            agent = create_react_agent(
                model,
                tools,
                prompt="你是一个助手，可以使用工具回答问题，请用中文回答。",
            )

            result = await agent.ainvoke(
                {"messages": [HumanMessage(content=args.query)]}
            )

            # 打印完整轨迹，观察每一步的工具调用
            for m in result["messages"]:
                m.pretty_print()
            print("最终回答:", result["messages"][-1].content)


if __name__ == "__main__":
    asyncio.run(main())
