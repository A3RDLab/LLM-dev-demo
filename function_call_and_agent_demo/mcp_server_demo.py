"""
MCP Server 示例（最新协议：Streamable HTTP）
=============================================
用官方 Python SDK 的 FastMCP 快速实现一个 MCP 服务器，
通过 Streamable HTTP 传输对外提供服务（MCP 2025-03-26 规范起的推荐传输，
取代了早期的 SSE 传输）。

启动方式：
    python mcp_server_demo.py
默认监听 http://localhost:8000/mcp

随后运行客户端示例：
    python mcp_client_agent_demo.py
"""

import random
from datetime import datetime, timezone, timedelta
from typing import Literal

from mcp.server.fastmcp import FastMCP

# 创建 MCP 服务器（name 会在客户端 list_tools 时体现）
mcp = FastMCP("demo-weather-server")


# ===== 用 @mcp.tool() 装饰器声明工具，docstring 即工具描述 =====
@mcp.tool()
def get_weather(city: Literal["北京", "上海", "深圳"]) -> str:
    """查询指定城市今天的天气（演示用 mock 数据）"""
    mock_data = {
        "北京": "晴，气温 32°C，北风 2 级",
        "上海": "多云，气温 28°C，东南风 3 级",
        "深圳": "雷阵雨，气温 30°C，南风 2 级",
    }
    return mock_data[city]


@mcp.tool()
def get_current_time(timezone_offset: int = 8) -> str:
    """获取当前时间，timezone_offset 为 UTC 偏移小时数（默认东八区）"""
    now = datetime.now(timezone(timedelta(hours=timezone_offset)))
    return now.strftime("%Y-%m-%d %H:%M:%S")


@mcp.tool()
def lottery() -> str:
    """随机抽一个幸运数字（演示无参数工具）"""
    return f"你的幸运数字是 {random.randint(1, 100)}！"


if __name__ == "__main__":
    # Streamable HTTP 传输：客户端通过 http://localhost:8000/mcp 连接
    # （如需老客户端兼容可改为 transport="sse"，新项目不建议）
    mcp.run(transport="streamable-http")
