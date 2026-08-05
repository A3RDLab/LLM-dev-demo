"""
LangGraph 智能体示例（可运行版）
=================================
演示如何用 LangGraph 构建一个真正能跑的 tool-calling agent。

包含两种写法的对比：
1. 手搓 StateGraph：完整展示 agent <-> tools 的循环控制，便于理解和定制
   （加审批节点、人工介入、条件分支等都在这层做）
2. 预构建 create_react_agent：一行代码得到同样的 ReAct 循环，生产快速起步用

核心思路（现代写法，不再手写 ReAct prompt 解析）：
    模型原生 function calling -> 返回 tool_calls -> ToolNode 执行 -> 结果回填 -> 循环

依赖：pip install langgraph langchain-openai
运行前请设置环境变量 API_KEY（可参考根目录 .env.example）
"""

import os
import argparse
from typing import Literal

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.prebuilt import create_react_agent, ToolNode, tools_condition

# ===== 1. 命令行参数（与仓库其他 demo 保持一致的风格） =====
parser = argparse.ArgumentParser(description='LangGraph Agent 示例')
parser.add_argument('--model', type=str, default=os.getenv("MODEL", "Pro/deepseek-ai/DeepSeek-V3"),
                    help='指定使用的模型名称（默认读环境变量 MODEL）')
parser.add_argument('--api_key', type=str, default=None,
                    help='指定API密钥（默认使用环境变量API_KEY）')
parser.add_argument('--base_url', type=str, default=os.getenv("API_BASE", "https://api.siliconflow.cn/v1/"),
                    help='指定API基础URL（默认读环境变量 API_BASE）')
parser.add_argument('--query', type=str,
                    default='北京和上海今天的天气怎么样？如果北京更热，帮我算一下北京气温的华氏度是多少',
                    help='测试用问题')
args = parser.parse_args()

api_key = args.api_key if args.api_key else os.getenv("API_KEY")

llm = ChatOpenAI(
    model=args.model,
    api_key=api_key,
    base_url=args.base_url,
    temperature=0.2,
)

# ===== 2. 定义工具（用 @tool 装饰器，docstring 即工具说明） =====
@tool
def get_weather(city: Literal["北京", "上海", "深圳"]) -> str:
    """查询指定城市今天的天气（演示用 mock 数据）"""
    mock_data = {
        "北京": "晴，气温 32°C，北风 2 级",
        "上海": "多云，气温 28°C，东南风 3 级",
        "深圳": "雷阵雨，气温 30°C，南风 2 级",
    }
    return mock_data[city]

@tool
def celsius_to_fahrenheit(celsius: float) -> str:
    """把摄氏度换算为华氏度"""
    return f"{celsius}°C = {celsius * 9 / 5 + 32:.1f}°F"

tools = [get_weather, celsius_to_fahrenheit]

# 让模型知道有哪些工具可用（原生 function calling）
llm_with_tools = llm.bind_tools(tools)

# ===== 3. 写法一：手搓 StateGraph =====
# MessagesState 是 LangGraph 内置状态，只有一个 messages 字段并自动做消息追加
def agent_node(state: MessagesState):
    """Agent 节点：调用模型，模型决定直接回答还是发起工具调用"""
    system = SystemMessage("你是一个助手，可以使用工具回答问题，请用中文回答。")
    response = llm_with_tools.invoke([system] + state["messages"])
    return {"messages": [response]}

def route_after_agent(state: MessagesState) -> Literal["tools", "__end__"]:
    """条件边：模型最后一条消息带 tool_calls 就去执行工具，否则结束"""
    last = state["messages"][-1]
    return "tools" if getattr(last, "tool_calls", None) else END

workflow = StateGraph(MessagesState)
workflow.add_node("agent", agent_node)
workflow.add_node("tools", ToolNode(tools))  # ToolNode 自动执行 tool_calls 并回填结果

workflow.add_edge(START, "agent")
workflow.add_conditional_edges("agent", route_after_agent)
workflow.add_edge("tools", "agent")  # 工具结果回到 agent，形成循环

graph = workflow.compile()

# ===== 4. 写法二：预构建 create_react_agent（等价于上面的手搓图） =====
prebuilt_agent = create_react_agent(
    llm,
    tools,
    prompt="你是一个助手，可以使用工具回答问题，请用中文回答。",
)

# ===== 5. 运行对比 =====
if __name__ == "__main__":
    print(f"问题: {args.query}\n")

    print("=== 写法一：手搓 StateGraph ===")
    result = graph.invoke({"messages": [HumanMessage(content=args.query)]})
    # 打印完整轨迹，观察 agent <-> tools 的循环过程
    for m in result["messages"]:
        m.pretty_print()
    print("最终回答:", result["messages"][-1].content)

    print("\n=== 写法二：预构建 create_react_agent ===")
    result = prebuilt_agent.invoke({"messages": [HumanMessage(content=args.query)]})
    print("最终回答:", result["messages"][-1].content)
