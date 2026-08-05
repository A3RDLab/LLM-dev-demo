# LangGraph 智能体示例

## 概述
演示如何用 LangGraph 构建一个真正能跑的 **tool-calling agent**，并对比两种写法：

1. **手搓 StateGraph**（`langgraph_agent_scaffold.py` 写法一）：完整展示 `agent <-> tools` 的循环控制，便于理解和定制——加审批节点、人工介入（human-in-the-loop）、条件分支都在这层做。
2. **预构建 `create_react_agent`**（写法二）：一行代码得到同样的 ReAct 循环，适合快速起步。

核心思路（现代写法）：模型原生 function calling 返回 `tool_calls`，`ToolNode` 自动执行并把结果回填消息流，模型再决定是否继续调用工具或给出最终回答。**不再手写 ReAct prompt 让模型输出 `Action:` 文本再正则解析**（旧写法已归档至 `../archive/`）。

## 快速开始

1. 安装依赖：
```bash
pip install -r requirements.txt
```

2. 设置环境变量（参考根目录 `.env.example`）：
```bash
export API_KEY=<你的API密钥>
```

3. 运行示例：
```bash
# 默认测试问题（涉及两次工具调用：查天气 + 温度换算）
python langgraph_agent_scaffold.py

# 自定义问题与模型
python langgraph_agent_scaffold.py --query "深圳今天天气如何" --model qwen-max --base_url https://dashscope.aliyuncs.com/compatible-mode/v1
```

写法一会打印完整消息轨迹（可用 `pretty_print()` 观察 agent 与 tools 的每一轮交互），写法二直接输出最终回答。

## 关键组件

| 组件 | 作用 |
|---|---|
| `MessagesState` | LangGraph 内置状态，自动追加式管理消息列表 |
| `llm.bind_tools(tools)` | 把工具 Schema 以原生 function calling 形式传给模型 |
| `ToolNode(tools)` | 预构建节点，自动执行 `tool_calls` 并把结果作为 ToolMessage 回填 |
| `tools_condition` / 自定义条件边 | 判断模型输出是继续调工具还是结束 |
| `create_react_agent` | 预构建的完整 ReAct 图，等价于手搓版 |

## 进一步扩展

- **人工审批**：在 `tools` 节点执行前加 `interrupt()`（LangGraph 1.x 的 human-in-the-loop 机制），对高危工具调用先等人确认
- **持久化**：编译时传入 `checkpointer`（如 `MemorySaver`），即可获得多轮对话记忆与断点恢复
- **结构化输出**：agent 最终结果可结合 `response_format` 参数输出 Pydantic 模型（参见根目录 `structured_output_demo.py`）
- **完整项目示例**：见仓库 `finance_doc_review/`（LangGraph 编排 + YAML 规则引擎 + 结构化输出的生产风格 demo）

## 最佳实践
1. 使用环境变量管理 API 密钥，切勿硬编码
2. 为工具写清晰的 docstring 和参数描述——这是模型正确调用工具的关键
3. 为关键节点添加单元测试，可用 fake LLM 离线验证图结构
4. 实现详细的日志记录（`langsmith` 或自建 tracing）
