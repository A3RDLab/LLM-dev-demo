## 1. 单文件页面与配置区

- [x] 1.1 新建 `function_call_and_agent_demo/agent_web_ui/index.html`，内联全部 HTML、CSS 和原生 JavaScript，不引用 CDN、外部字体、第三方脚本或构建产物
- [x] 1.2 实现配置表单：API Base、API Key、Model、可选 GitHub Token、最大轮次和用户问题；填入与 CLI 一致的非敏感默认值，密钥输入框留空且不自动填充持久化值
- [x] 1.3 实现配置校验、操作按钮、整体状态、最终回答区和空时间线；完成窄屏布局、长文本换行/滚动及不同语义状态的样式

## 2. 模型流式协议与工具协议

- [x] 2.1 定义与 Python 版一致的 system prompt、两个 OpenAI function tool schema 和 API Base 路径拼接逻辑，使用 Authorization 头发送用户输入的 API Key
- [x] 2.2 实现基于 `fetch`、`ReadableStream` 和 `TextDecoder` 的 SSE 读取，覆盖跨 chunk 事件、CRLF、多行 data、`[DONE]`、HTTP 非成功和无可读响应流
- [x] 2.3 实现 assistant content 增量回调及按 `tool_calls.index` 累积 id、函数名和 arguments，按 index 顺序生成与非流式 message 等价的响应对象
- [x] 2.4 实现 GitHub REST 工具：URL 编码、默认 `main` 分支、可选 Token、recursive tree 路径文本、contents Base64 到 UTF-8 解码，以及 HTTP/内容类型错误处理

## 3. Agent 主循环与运行控制

- [x] 3.1 实现独立 messages 历史和最大轮次循环：模型响应无工具调用时返回最终回答，有工具调用时先回填 assistant 消息，再顺序执行并回填具有正确 tool_call_id 的 tool 消息
- [x] 3.2 对无效 arguments JSON、未知工具、模型/GitHub 失败和轮次上限执行 fail-fast，确保异常不会作为成功最终回答返回
- [x] 3.3 用 runId 与 AbortController 实现开始、停止、清空和重跑；运行中锁定配置并防止并发，停止后取消当前网络请求且不再推进工具或轮次

## 4. 执行过程可视化

- [x] 4.1 按轮次创建模型卡片和工具卡片，展示用户问题、模型中间正文、工具名称、累积参数、执行状态、耗时、结果字符数和最终回答
- [x] 4.2 用可折叠区域展示完整 JSON 参数与未截断工具结果；流式更新只修改对应文本节点，保留其他卡片的展开状态
- [x] 4.3 实现运行中、成功、失败和已停止的整体/局部状态，以及包含 HTTP 状态或 CORS/网络排查建议的错误展示
- [x] 4.4 确保所有模型、工具及错误动态文本通过 `textContent` 或文本节点渲染，轨迹与日志不包含 API Key、GitHub Token 或 Authorization 头

## 5. 实验文档同步

- [x] 5.1 更新 `实验手册.md` 实验 4，保留 CLI 默认步骤，新增“可选：网页观察执行过程”的直接打开路径、配置说明和开始/停止/展开结果操作
- [x] 5.2 将实验 4 观察点扩展为按轮次查看模型请求、工具参数、完整结果回填和流式最终回答，并注明浏览器直连受模型端点 CORS、GitHub 限流和默认分支影响

## 6. 验证

- [x] 6.1 通过 `file://` 打开页面，确认无服务端、构建和网络静态资源依赖；检查源码无硬编码密钥，刷新后密钥为空且 localStorage/sessionStorage 无密钥
- [x] 6.2 用可控的 fetch/流式响应测试拆分 SSE、多个工具 index、正文与工具调用并存、assistant/tool 消息顺序、无效 JSON、未知工具及最大轮次，核对与 CLI 协议一致
- [x] 6.3 测试目录树、含中文 UTF-8 文件内容、GitHub HTTP 错误、模型 HTTP 错误、CORS/网络失败、停止和重跑，确认状态准确且旧消息不泄漏到新运行
- [x] 6.4 用包含 HTML/脚本字符串的模型与工具响应确认只按纯文本展示；展开长结果并持续接收流式更新，确认内容完整且其他折叠状态不重置
- [x] 6.5 在允许浏览器跨域的 OpenAI 兼容端点上完成一次默认 GitHub 问题冒烟测试，观察目录树 → 文件内容 → 最终回答；确认原 Python CLI 未改动且手册命令与页面行为一致
