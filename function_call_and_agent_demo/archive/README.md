# 归档目录

本目录存放**已过时的历史写法**，仅作为演进过程参考，不建议照抄。

| 文件 | 归档原因 |
|---|---|
| `demo-agent-with-react-prompt.py` | 手写 ReAct prompt + 正则解析模型输出的旧式 agent 写法。现在应使用模型原生 function calling（见 `../demo-agent-with-tools-arg.py`）或 LangGraph（见 `../langgraph_demo/`） |
| `demo-agent-with-mcp.py` | 依赖已被官方废弃的 `@modelcontextprotocol/server-github`（npm 包已 deprecate），且使用 stdio 传输。新写法见 `../mcp_server_demo.py` + `../mcp_client_agent_demo.py`（FastMCP + Streamable HTTP） |
| `chat-with-gh.py` | 早期 Streamlit + function calling 读 GitHub 仓库的 demo。直连 OpenAI 并硬编码 `gpt-4-turbo`，不符合仓库统一的 `.env`/`API_BASE`/多平台参数约定；GitHub agent 路线已由 MCP demo 替代 |
| `失败例子_thoughtMCP.py` | MCP 早期探索的失败案例，保留作为教训参考 |
| `demo-agent-with-qw.py.bak` | 历史备份文件 |

当前推荐的 agent 实现路线：
1. 入门：`../demo-agent-with-tools-arg.py`（原生 function calling + 手写调用循环）
2. 进阶：`../langgraph_demo/langgraph_agent_scaffold.py`（LangGraph 图编排）
3. MCP：`../mcp_server_demo.py` + `../mcp_client_agent_demo.py`（FastMCP + Streamable HTTP）
4. 生产风格：仓库根目录 `finance_doc_review/`（LangGraph + 规则引擎 + 结构化输出）
