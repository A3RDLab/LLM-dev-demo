## Why

实验 4 目前只能通过终端日志和流式文本观察 Function Calling 循环，模型消息、工具调用参数、工具结果与最终回答混杂在滚动输出中，不利于学员逐轮理解“模型请求工具 → 代码执行 → 结果回填 → 再次调用模型”的过程。新增一个无需服务端的本地 Web 页面，可以把同一条执行链路转化为可检查、可展开的可视化轨迹。

## What Changes

- 在实验 4 目录新增可直接由浏览器打开的单文件 Web 应用，无需构建工具、后端服务或新增 Python/JavaScript 依赖。
- 在浏览器中复现现有 CLI 的最小 Agent 内核：支持用户问题与模型连接配置、OpenAI 兼容的流式对话、多轮工具调用、最大轮次保护和最终回答展示。
- 将执行过程按轮次呈现为时间线，区分用户问题、模型响应、工具调用请求、工具执行状态与结果、错误和最终回答；长参数及工具结果支持展开查看，避免截断后丢失教学信息。
- 提供开始、停止和清空/重跑等基础操作，并在执行期间清楚标识当前阶段，防止重复提交。
- 由页面直接调用用户配置的 OpenAI 兼容端点和 GitHub 公共 API；API Key 与可选 GitHub Token 仅由用户在页面中输入，不写入源码或持久化存储。
- 保留现有 `demo-agent-with-tools-arg.py` 的命令行行为与教学递进关系，Web 页面作为实验 4 的可选观察入口；同步更新 `实验手册.md` 的启动方式和观察点。

## Capabilities

### New Capabilities

- `agent-execution-web-ui`: 无服务端的实验 4 Agent 执行与可视化能力，包括浏览器端模型/GitHub 调用、流式增量处理、多轮 Function Calling、消息回填、执行控制，以及按轮次展示完整工具调用轨迹和错误状态。

### Modified Capabilities

（无，现有 specs 均不涉及实验 4 的 Agent 执行方式。）

## Impact

- **代码**：新增 `function_call_and_agent_demo/agent_web_ui/index.html`（内联 HTML、CSS 与原生 JavaScript）；现有 CLI 脚本不改动。
- **外部接口**：浏览器直接访问 OpenAI 兼容的 Chat Completions 接口和 GitHub REST API，实际可用性受目标端点 CORS 策略与网络条件影响。
- **安全与配置**：不再复用 Python 的 `.env` 自动加载；密钥只在当前页面内使用，不进入源码、URL、日志下载或 localStorage。
- **文档**：更新 `实验手册.md` 实验 4，说明直接打开 HTML 的方法、配置项、CORS 限制和可视化观察点。
- **依赖**：无新增运行时或构建依赖，不改动根目录 `requirements.txt`。
