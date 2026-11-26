## Context

实验 4 的 `demo-agent-with-tools-arg.py` 以 Python 手写循环实现了最小 Function Calling Agent：`call_with_messages` 消费流式响应并按 `index` 累积工具调用，`execute_function` 调用 PyGithub，`run_agent` 将 assistant/tool 消息回填后进入下一轮。当前所有过程均输出到终端，长目录树和文件内容还会为控制刷屏而截断。

本次新增独立的 `function_call_and_agent_demo/agent_web_ui/index.html`，作为同一实验的可选观察入口。页面必须能通过 `file://` 直接打开，不能依赖 Python 服务、Node 服务、构建步骤或 CDN。由于浏览器无法直接复用 PyGithub、OpenAI Python SDK 和根目录 `.env`，Web 版需用原生 JavaScript 实现相同协议，同时由用户在页面中提供连接配置。现有 CLI 保持原样。

## Goals / Non-Goals

**Goals:**

- 用单个本地 HTML 文件完成配置、真实模型调用、GitHub 工具执行和完整 Agent 循环。
- 按“轮次 → 模型响应 → 工具调用 → 工具结果”呈现执行轨迹，长内容默认折叠但可查看全文。
- 保留流式最终回答体验，并让工具调用参数从增量片段到完整 JSON 的过程可观察。
- 提供开始、停止、清空重跑、最大轮次限制，以及明确的运行/成功/失败/停止状态。
- 不在源码、持久化存储或页面轨迹中保存 API Key、GitHub Token；动态模型与工具文本不得作为 HTML 注入。

**Non-Goals:**

- 不替换或重构现有 Python CLI，不改变实验 4 → LangGraph → Agent Harness 的教学顺序。
- 不增加通用 Agent 框架、会话历史持久化、多会话管理、工具审批或自定义工具编辑器。
- 不绕过模型供应商或 GitHub 的 CORS、鉴权、限流策略，也不提供代理服务。
- 不展示或保存模型隐藏的推理内容；只展示模型实际返回的正文与结构化工具调用。
- 不引入离线演示数据、录制回放或响应式移动端之外的复杂产品能力。

## Decisions

### 决策 1：单文件原生 HTML/CSS/JavaScript，浏览器直连外部 API

所有标记、样式和逻辑内联在 `index.html`，不加载第三方包、字体或脚本。模型请求使用 OpenAI 兼容的 `POST {API_BASE}/chat/completions`，GitHub 工具使用公开 REST API；默认连接值与 CLI 一致，API Key 和可选 GitHub Token 由密码输入框接收。

选择该方案是因为用户明确接受本地 HTML 且不需要服务端，同时单文件便于学员复制和检查。备选方案包括 Streamlit/Flask（需要服务端，否决）、Pyodide 运行现有 Python（下载体积大、依赖与网络兼容复杂，否决）、Node 构建的 React 应用（引入工具链，违背零依赖目标，否决）。

### 决策 2：独立运行状态机驱动 Agent 循环，渲染与协议处理分离

脚本内部按职责划分函数：配置读取与校验、模型流式请求、SSE 解析、工具参数累积、GitHub 工具执行、消息历史管理、时间线渲染和运行控制。`messages` 是唯一发送给模型的数据历史；DOM 节点只承担展示，不能反向充当协议状态。

每次运行拥有独立的 `runId` 和 `AbortController`。主循环最多执行用户指定轮次（默认 10，与 CLI 一致）：发送当前 messages → 收集 assistant content/tool_calls → 若无工具调用则完成；否则先追加完整 assistant 消息，再按模型返回顺序逐个执行工具并追加对应 `role="tool"` 消息。异常不被包装成最终回答，达到轮次上限也明确失败。

### 决策 3：按 SSE 事件边界解析流，按 `tool_calls.index` 累积增量

使用 `fetch` + `ReadableStream` + `TextDecoder` 读取响应，正确处理网络 chunk 与 SSE 事件边界不一致、CRLF、跨 chunk 的 JSON 和 `[DONE]`。每个事件只解析 `data:` 载荷；正文增量立即追加到当前轮模型正文，工具调用则按 `index` 保存 id、函数名和 arguments 字符串，不能假设单个 chunk 含完整调用。

一轮结束后将 arguments 作为 JSON 解析并执行。若 JSON 无效、函数名未知、HTTP 非成功或响应缺少可读取的流，则终止当前运行并在对应步骤显示错误。备选方案是非流式请求（实现更简单，但丢失实时观察体验，否决）或按每个网络 chunk 直接 JSON.parse（无法处理拆包，否决）。

### 决策 4：GitHub 工具保持 CLI 的参数与返回语义，但改用 REST

- `get_repo_tree`：请求仓库 recursive git tree，返回逐行路径文本；branch 缺省为 `main`。
- `get_repo_file_content`：请求指定 ref 的文件内容，将 Base64 响应按 UTF-8 解码；branch 缺省为 `main`。

路径与 ref 需正确 URL 编码；仓库不存在、分支错误、文件不是普通文件及限流等错误显示原始状态与可读摘要。多个工具调用按顺序执行，以保持与 CLI 一致并简化教学轨迹。可选 Token 仅放入 GitHub 请求的 `Authorization` 请求头；匿名访问保持公开仓库能力。

### 决策 5：时间线以语义卡片展示，完整内容用 `<details>` 折叠

页面包含配置区、问题输入与操作区、整体状态区、最终回答区和执行时间线。每轮有固定编号，卡片类型及颜色明确区分用户、模型、工具请求、执行中、工具结果、错误和停止状态。工具名称、参数、耗时、结果字符数位于摘要，完整 JSON 参数和未截断结果放在折叠区；模型正文与最终回答使用适合流式追加的文本容器。

所有动态文本通过 `textContent`/`createTextNode` 写入。渲染增量时只更新对应卡片，避免重建整个时间线导致折叠状态丢失。API 请求头、密钥及完整配置对象不进入轨迹。

### 决策 6：停止是协作式取消，保留已产生的轨迹

停止按钮触发当前模型或 GitHub 请求的 abort，并通过 runId/运行状态检查阻止后续工具与下一轮请求。界面将本次运行标为“已停止”，不将其误报为模型最终回答，已显示的参数和结果保留。运行中禁用开始及配置编辑，停止后才允许清空或重新运行，避免并发运行互相污染。

## Risks / Trade-offs

- **[模型端点不允许 `file://`/`Origin: null` 跨域访问]** → 在手册和页面错误提示中明确这是供应商 CORS 限制，而非 Agent 逻辑错误；允许更换支持浏览器跨域的兼容端点，不内置绕过代理。实机验证需选择允许该来源的端点，无法验证的供应商不作兼容承诺。
- **[浏览器直连会暴露用户输入的密钥给所配置端点及本机页面使用者]** → 密钥使用 password 输入、仅保存在运行时变量、禁用自动持久化，不写入源码/localStorage/URL/日志；手册提示仅在可信端点和本机使用。
- **[SSE 实现差异或代理缓冲导致流式效果不一致]** → 严格按事件边界解析，同时以完整响应 EOF 为最终累积边界；若端点不支持流式读取则给出明确错误。
- **[GitHub 匿名限流、默认分支并非 main 或大文件响应]** → 暴露 branch 参数给模型、支持可选 Token，并显示 HTTP 错误；工具结果不截断但默认折叠，避免长内容撑乱页面。
- **[模型生成恶意 HTML/Markdown 或超长工具结果]** → 一律按纯文本渲染，不执行返回代码；长内容折叠并采用换行/滚动容器。
- **[Web 与 Python 版协议实现漂移]** → 以现有 TOOLS、system prompt、默认 branch、顺序回填和 max_iterations 为对照；通过固定 mock 流验证消息序列，并做一次真实端点冒烟测试。
- **[单文件随功能增加而变长]** → 这是可接受的教学取舍；用清晰的函数分区和注释保持可读性，不为了抽象引入模块加载或构建步骤。

## Migration Plan

1. 新增单文件页面并完成协议与交互验证，不影响现有 CLI 用户。
2. 更新 `实验手册.md` 实验 4：CLI 仍为默认主线，新增“可选：网页观察执行过程”及直接打开文件的步骤、配置说明和 CORS 注意事项。
3. 回滚时删除 `agent_web_ui/` 并还原手册对应段落即可，无数据或依赖迁移。

## Open Questions

无阻塞问题。不同模型供应商的浏览器 CORS 策略属于运行时环境差异，按上述限制如实提示，不在本变更中通过新增服务端解决。
