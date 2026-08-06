# Tasks: gray-process-plain-answer

## 1. 基础调用类脚本

- [x] 1.1 `first_llm_app.py`：保留灰色思考；删除 `CYAN` 常量，"回复:"标记与流式正文改为终端默认色
- [x] 1.2 核对 `first_llm_call.py`：确认无过程信息、无需改动（`code_fim.py` 已归档）

## 2. 结构化输出与 RAG 脚本

- [x] 2.1 `structured_output_demo.py`：定义常量；降级提示与两个 `===` 分节标题灰色；流式 JSON 与 Pydantic 对象输出保持默认色
- [x] 2.2 `mini_rag_demo.py`：定义常量；`[索引]`、向量化进度、`[检索结果]` 及条目、`[生成回答]` 灰色；流式回答默认色；交互模式提示灰色

## 3. Agent 工具循环脚本

- [x] 3.1 `text2sql_demo.py`：定义常量；Schema 输出、`[用户问题]`、`── 第 N 轮 ──`、`[执行 SQL]`、`[查询结果]`、`[最终回答]` 标记灰色；回答正文默认色
- [x] 3.2 `wiki_kb_agent_demo/kb_agent.py`：定义常量；`🔧 调用工具` 行与 index.md 缺失提示灰色；`助手:` 标记灰色、流式回答正文默认色
- [x] 3.3 `demo-agent-with-tools-arg.py`：StreamHandler 配置灰色 formatter、FileHandler 保持无色 formatter；"Final Answer (streaming):"标记灰色、正文默认色
- [x] 3.4 `agent_harness_demo/agent_harness_demo.py`：定义常量；`🛠 调用工具`、`↳ 结果`、任务头与分隔线灰色；`🤖 模型回复` 内容默认色
- [x] 3.5 `langgraph_demo.py`、`langgraph_demo/langgraph_agent_scaffold.py`、`mcp_client_agent_demo.py`：config/工具加载等过程提示灰色；`pretty_print()` 保留原样；`最终回答:` 与内容默认色

## 4. 文档同步

- [x] 4.1 `实验手册.md`：核对全部实验的观察点，凡涉及输出样式的描述统一为"灰色过程信息 + 默认色最终回答"，删除任何青色/白色表述

## 5. 验证

- [x] 5.1 `grep "\\033\["` 全仓库核对：现役脚本中仅剩 `\033[90m`（灰）与 `\033[0m`（复位），无 36/37 色码（archive/ 除外）；同时确认 `first_langchain_app.py`、`code_fim.py`、`demo-agent-with-aliyun-2phases.py` 已在 archive/ 且 archive/README.md 含归档说明
- [x] 5.2 实机运行 `first_llm_app.py`、`structured_output_demo.py`、`text2sql_demo.py`、`kb_agent.py --once`，确认灰色过程与默认色回答正确配对、RESET 闭合无残留
- [x] 5.3 抽查 `demo-agent-with-tools-arg.py` 运行后的 `agent_debug.log` 不含 ANSI 转义码；抽查 messages 累积路径返回值为原始文本
- [x] 5.4 其余改动文件 `python -m py_compile` 语法检查全部通过
