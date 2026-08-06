# Design: gray-process-plain-answer

## Context

这是 LLM 教学实验仓库，学员按实验手册顺序运行各 CLI demo。当前着色现状（实机核查）：

- `first_llm_app.py`：灰色思考（`\033[90m`）+ **青色**回复（`\033[36m`）；
- 其余所有脚本（`structured_output_demo.py`、`mini_rag_demo.py`、`text2sql_demo.py`、`kb_agent.py`、`demo-agent-with-tools-arg.py`、`agent_harness_demo.py`、langgraph/MCP demo）：完全无着色。

> 注：`first_langchain_app.py`、`code_fim.py`、`demo-agent-with-aliyun-2phases.py` 经核查不在实验手册教学路线上，已移入 `archive/`，不在本变更范围内。

用户要求的新规范：思考过程、工具调用、中间步骤统一**灰色**；最终结果/回答使用**终端默认色**（不施加任何 ANSI 码，即"白色/正常显示"）。

## Goals / Non-Goals

**Goals:**
- 所有 CLI demo 建立统一视觉语义：灰色 = 过程（思考流、工具调用、中间日志、状态提示），默认色 = 结果（最终回答、JSON 结果、Pydantic 对象）。
- 消除 `first_llm_app.py` 的青色回复这一不一致点，并为其余无着色的脚本补齐灰色过程信息。
- 同步 `实验手册.md` 中涉及输出观察点的描述。

**Non-Goals:**
- 不改 Streamlit Web UI（`AliyunQA_RAG_demo/chat.py`、`excel-process/app.py`）；
- 不改 `archive/` 内历史脚本（含 `demo-agent-with-react-prompt.py` 的白色思考）；
- 不引入 rich/colorama 等依赖；不处理非 TTY 管道场景的 ANSI 抑制（教学场景从简）；
- 不替换 LangChain 的 `pretty_print()`（它是框架自带的消息轨迹渲染，属于"过程"范畴，保留原样）。

## Decisions

**决策 1：两色方案 = `GRAY` + 不着色，删除所有 `CYAN`/白色思考**
- 定义：`GRAY = "\033[90m"`、`RESET = "\033[0m"`；最终回答与结果直接 `print` 原始文本。
- 备选：保留青色回复（first_llm_app 现状）——否决，用户明确要求结果用终端默认色；备选：白色 `\033[37m` 显式标注结果——否决，在深色/浅色终端主题下 `\033[37m` 表现不一，默认色才是"和终端正常显示一致"的正确实现。

**决策 2：每个脚本自包含定义常量，不建公共模块**
- 仓库惯例是 demo 脚本自包含、可独立复制运行（AGENTS.md 明确各 demo 为自包含脚本）。每个需要着色的脚本顶部定义自己的 `GRAY`/`RESET`。
- 备选：抽 `utils/colors.py` 公共模块——否决，破坏 demo 的独立可复制性。

**决策 3：着色只发生在打印路径，数据路径零污染**
- 累积进 `messages` 的 delta、函数返回值（如 `stream_completion` 返回的 content）、日志文件内容一律使用未着色原文。着色仅包裹在 `print(f"{GRAY}...{RESET}")` 的格式化层。
- `demo-agent-with-tools-arg.py` 的 logger：StreamHandler 用带灰色的 formatter，FileHandler 保持无色 formatter，避免 ANSI 码写入 `agent_debug.log`。

**决策 4：各脚本具体着色清单**（过程灰 / 结果默认）

| 脚本 | 灰色（过程） | 默认色（结果） |
|---|---|---|
| `first_llm_app.py` | "正在思考..."、思考流、"[模型只输出了思考过程]" | "回复:"标记与回复正文（**去掉 CYAN**） |
| `structured_output_demo.py` | `===` 分节标题、降级提示 | 流式 JSON、Pydantic 对象输出 |
| `mini_rag_demo.py` | `[索引]`、向量化进度、`[检索结果]` 及条目、`[生成回答]` | 流式回答 |
| `text2sql_demo.py` | Schema、`[用户问题]`、`── 第 N 轮 ──`、`[执行 SQL]`、`[查询结果]` | `[最终回答]`与正文 |
| `kb_agent.py` | `🔧 调用工具`、"知识库中没有 index.md"提示 | `助手:`与流式回答 |
| `demo-agent-with-tools-arg.py` | 控制台 logger 全部输出 | 流式 Final Answer 正文（"Final Answer (streaming):"标记灰色） |
| `agent_harness_demo.py` | `🛠 调用工具`、`↳ 结果`、分隔线与任务头 | `🤖 模型回复`内容 |
| `langgraph_demo.py` / `langgraph_agent_scaffold.py` / `mcp_client_agent_demo.py` | `pretty_print()` 保留原样（框架轨迹）、config/工具加载提示灰色 | `最终回答:`与内容 |

## Risks / Trade-offs

- **[ANSI 码污染数据流]** → 着色严格限于 print 格式化层；验证时抽查 `messages` 历史与返回值不含 `\033`。
- **[管道/重定向时输出带转义码]** → 教学场景从简不处理；如需可后续加 `sys.stdout.isatty()` 判断（本次不做）。
- **[手册描述与实机不符]** → 手册中所有提到"青色/颜色"的观察点同步改为"灰色过程 + 默认色结果"。
- **[遗漏某个打印点]** → tasks.md 按文件逐一列出改造点并配验证步骤；用 `grep "\\033\["` 与肉眼跑通双重核对。

## Migration Plan

纯代码与文档修改，无迁移。回滚策略：单提交实现，`git revert` 即可整体回退。

## Open Questions

无。
