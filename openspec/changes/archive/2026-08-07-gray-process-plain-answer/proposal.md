# Proposal: gray-process-plain-answer

## Why

仓库中涉及流式输出、思考过程、工具调用的 CLI demo 着色方式不统一：`first_llm_app.py` 用“灰色思考 + 青色回复”，其余脚本（text2sql、kb_agent、mini_rag、structured_output 等）完全没有着色。学员在实验路线上切换脚本时，视觉语义不一致会干扰对“哪些是过程、哪些是结果”的判断。

## What Changes

- 建立统一着色规范：**过程信息一律灰色**（思考流、工具调用、中间步骤、日志、状态提示），**最终结果/回答不做任何着色**（使用终端默认前景色，即学员所见的"白色/正常显示"）。
- 对以下脚本按规范改造：
  - `first_llm_app.py`：保留灰色思考；回复正文与"回复:"标记**去掉青色**，改为默认色；
  - `structured_output_demo.py`：`===` 分节标题与降级提示灰色；流式 JSON 与 Pydantic 结果保持默认色；
  - `mini_rag_demo.py`：`[索引]`/`[检索结果]`/`[生成回答]` 等过程标记灰色；流式回答默认色；
  - `text2sql_demo.py`：轮次标题、`[执行 SQL]`、`[查询结果]` 灰色；`[最终回答]` 及正文默认色；
  - `wiki_kb_agent_demo/kb_agent.py`：`🔧 调用工具` 行灰色；`助手:` 与流式回答默认色；
  - `demo-agent-with-tools-arg.py`：控制台 logger 输出灰色（文件 handler 保持无色）；流式 Final Answer 默认色；
  - `agent_harness_demo/agent_harness_demo.py`、`langgraph_demo/`、`mcp_client_agent_demo.py`：过程性打印灰色，最终回答默认色；
  - `first_llm_call.py`：无过程信息，仅核对无需改动。
- 同步更新 `实验手册.md` 中提到输出颜色/观察点的段落。
- **不在范围内**：Streamlit 应用（`AliyunQA_RAG_demo/chat.py`、`excel-process/app.py`、`chat-with-gh.py` 已归档）的 Web UI 输出；`archive/` 内的历史脚本（含本次新归档的 `first_langchain_app.py`、`code_fim.py`、`demo-agent-with-aliyun-2phases.py`）。

## Capabilities

### New Capabilities

- `cli-output-coloring`: CLI demo 终端输出的统一着色规范——过程信息（思考/工具调用/中间步骤/日志）灰色，最终回答与结果使用终端默认色，并保证 messages 历史与返回值中不泄漏 ANSI 转义码。

### Modified Capabilities

（无，`openspec/specs/` 下暂无既有 spec）

## Impact

- **代码**：约 10 个根目录/子目录 CLI 脚本的打印语句；每个脚本自包含定义 `GRAY`/`RESET` 常量（仓库惯例：demo 脚本自包含、不引入公共模块）。
- **文档**：`实验手册.md` 相关实验观察点；各脚本如涉及颜色描述的 README。
- **约束**：着色只作用于终端打印路径；累积进 `messages`、写日志文件、返回给调用方的字符串必须是无 ANSI 码的原始文本；logger 的文件 handler 不着色（避免污染 `agent_debug.log`）。
- **依赖**：无新增依赖（纯 ANSI 转义码，不引入 rich/colorama）。
