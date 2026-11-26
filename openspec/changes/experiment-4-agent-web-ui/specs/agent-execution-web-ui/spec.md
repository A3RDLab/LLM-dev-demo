## ADDED Requirements

### Requirement: 本地零服务端启动与连接配置

系统 SHALL 提供一个可由现代浏览器通过 `file://` 直接打开的单文件 HTML 应用，且不得要求本地服务、构建步骤、第三方前端依赖或远程静态资源。应用 SHALL 提供 API Base、API Key、Model、用户问题、最大轮次和可选 GitHub Token 的配置入口，并以现有 CLI 的 API Base、Model、问题和最大轮次作为非敏感默认值。

#### Scenario: 直接打开页面

- **WHEN** 用户直接用浏览器打开 `function_call_and_agent_demo/agent_web_ui/index.html`
- **THEN** 页面完整显示配置区、问题区、操作区、状态区、最终回答区和执行时间线，且无需启动任何服务或访问 CDN

#### Scenario: 缺少必要配置

- **WHEN** 用户在 API Base、API Key、Model 或问题为空时点击开始
- **THEN** 系统不发起网络请求，并在对应配置或整体状态处显示可理解的校验错误

### Requirement: 流式多轮 Function Calling 执行

系统 SHALL 使用用户配置的 OpenAI 兼容 Chat Completions 端点发起流式请求，提供与 CLI 一致的 system prompt、工具定义和消息历史。系统 SHALL 按 SSE 事件边界解析响应，将正文增量追加到当前轮输出，并按 `tool_calls.index` 累积每个工具调用的 id、函数名和 arguments 文本。

#### Scenario: 工具参数分散在多个流式片段

- **WHEN** 模型在多个网络 chunk 中返回同一工具调用的函数名和 arguments 片段
- **THEN** 系统按工具调用 index 拼接完整参数，显示实时累积状态，并且只在流结束后解析完整 JSON

#### Scenario: 模型请求工具后继续循环

- **WHEN** 一轮模型响应包含一个或多个工具调用
- **THEN** 系统先将包含 tool_calls 的 assistant 消息加入历史，再按返回顺序执行工具，并为每次调用追加具有对应 tool_call_id、工具名和完整结果的 tool 消息后进入下一轮

#### Scenario: 模型给出最终回答

- **WHEN** 一轮模型响应不包含工具调用
- **THEN** 系统停止调用工具，将该轮正文作为最终回答流式显示，并将整体运行标记为成功

#### Scenario: 正文与工具调用同时出现

- **WHEN** 同一轮模型响应同时包含正文增量和工具调用
- **THEN** 系统保留并显示该轮正文，同时继续执行工具循环，不把中间正文误标为最终回答

### Requirement: GitHub 仓库工具

系统 SHALL 实现 `get_repo_tree` 和 `get_repo_file_content` 两个浏览器端工具，其参数、缺省 branch、调用名称及文本结果语义 SHALL 与实验 4 CLI 对齐。系统 SHALL 直接访问 GitHub REST API，在提供 GitHub Token 时用于鉴权，未提供时允许匿名访问公开仓库。

#### Scenario: 获取仓库目录树

- **WHEN** 模型请求 `get_repo_tree` 且提供仓库全名及可选 branch
- **THEN** 系统请求对应仓库的 recursive git tree，将路径按行组成完整文本作为工具结果，缺省 branch 为 `main`

#### Scenario: 获取 UTF-8 文件内容

- **WHEN** 模型请求 `get_repo_file_content` 且提供仓库全名、文件路径及可选 branch
- **THEN** 系统读取指定 ref 的普通文件，将 GitHub 返回的 Base64 内容正确解码为 UTF-8 文本，并将未截断内容作为工具结果

#### Scenario: GitHub 请求失败

- **WHEN** GitHub 返回鉴权、限流、仓库/分支/文件不存在或不支持的内容类型错误
- **THEN** 系统将对应工具卡片标记为失败，显示 HTTP 状态和可读错误，并终止运行而非把错误当成最终回答

### Requirement: 可检查的轮次时间线

系统 SHALL 将每次执行按轮次展示为时间线，清楚区分用户问题、模型正文、工具调用请求、工具执行状态、工具结果、最终回答、停止和错误。工具卡片 SHALL 展示名称、参数和执行状态；完整参数与完整工具结果 SHALL 可展开检查，不得只用截断预览代替。

#### Scenario: 多轮工具调用轨迹

- **WHEN** 一次运行依次完成目录树调用、文件内容调用和最终回答
- **THEN** 时间线按真实顺序显示各轮模型响应和工具卡片，用户能辨认每次工具结果回填后触发的下一轮模型请求

#### Scenario: 查看长工具结果

- **WHEN** 工具返回长目录树或长文件内容
- **THEN** 页面默认以折叠或受控滚动方式保持时间线可读，且用户展开后能查看未经日志截断的完整结果

#### Scenario: 流式内容更新

- **WHEN** 模型正文或工具 arguments 持续到达
- **THEN** 系统只更新对应卡片内容，不重置其他卡片已展开/折叠的状态

### Requirement: 执行控制与轮次保护

系统 SHALL 提供开始、停止和清空操作，并在运行期间防止重复启动或修改本次配置。停止 SHALL 取消当前网络请求并阻止后续工具执行和后续轮次，同时保留已产生的轨迹。系统 SHALL 在达到最大轮次仍未获得最终回答时终止并报错。

#### Scenario: 用户主动停止

- **WHEN** 用户在模型流式响应或 GitHub 工具执行期间点击停止
- **THEN** 系统取消当前请求，将运行标记为已停止，保留现有轨迹，不再执行后续工具或模型请求，也不显示成功状态

#### Scenario: 达到最大轮次

- **WHEN** 模型在用户设置的最大轮次内持续请求工具且没有给出最终回答
- **THEN** 系统停止循环并显示明确的轮次上限错误，最终回答区不得显示成功结果

#### Scenario: 清空并重跑

- **WHEN** 一次运行已完成、失败或停止后用户点击清空并开始新运行
- **THEN** 系统清除旧时间线、最终回答和错误状态，使用一份全新的模型消息历史，不混入上一轮消息

### Requirement: 可见且可诊断的失败状态

系统 SHALL 对模型 HTTP 错误、流式响应解析错误、无效工具 JSON、未知工具、网络失败和跨域失败显示错误状态，并终止当前运行。错误提示 SHALL 帮助区分配置/网络/CORS 问题与 Agent 执行问题。

#### Scenario: 模型接口返回错误

- **WHEN** 模型端点返回非成功 HTTP 状态或错误载荷
- **THEN** 系统显示状态码和不含密钥的错误摘要，将当前轮标记为失败，并且不进入下一轮

#### Scenario: 浏览器跨域请求被拒绝

- **WHEN** 浏览器因目标端点 CORS 策略阻止请求
- **THEN** 页面显示可能由 CORS 或网络连接导致的明确提示，保留已完成轨迹，并建议检查端点是否允许浏览器直接访问

### Requirement: 密钥与动态内容安全

系统 MUST NOT 将 API Key 或 GitHub Token 硬编码到 HTML、写入 URL、localStorage、sessionStorage、时间线或诊断日志。系统 MUST 将密钥仅用于相应请求的 Authorization 头，并将模型正文、工具参数、工具结果和错误文本作为纯文本渲染。

#### Scenario: 页面刷新后不保留密钥

- **WHEN** 用户输入密钥并刷新或重新打开页面
- **THEN** API Key 和 GitHub Token 输入框为空，浏览器存储和页面源码中不存在所输入的密钥

#### Scenario: 外部文本包含 HTML

- **WHEN** 模型或 GitHub 工具返回包含脚本标签、事件处理器或其他 HTML 的文本
- **THEN** 页面按文本原样显示该内容，不创建可执行元素或运行其中脚本
