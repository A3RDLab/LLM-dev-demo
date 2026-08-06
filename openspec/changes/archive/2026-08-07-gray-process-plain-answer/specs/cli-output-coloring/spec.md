# Spec: cli-output-coloring

## ADDED Requirements

### Requirement: 过程信息统一灰色输出
所有 CLI demo 脚本在终端打印过程信息时，SHALL 使用灰色 ANSI 转义码（`\033[90m` 起始、`\033[0m` 结束）包裹。过程信息包括：思考流（reasoning content）、工具调用及其结果摘要、中间步骤标记（轮次标题、SQL 执行、检索结果、索引构建进度）、状态与降级提示、控制台日志输出。

#### Scenario: 思考过程以灰色显示
- **WHEN** 学员运行 `first_llm_app.py` 且模型输出思考内容
- **THEN** "正在思考..."提示与思考流文字以灰色显示，且思考流结束时颜色正确复位

#### Scenario: 工具调用轨迹以灰色显示
- **WHEN** 学员运行 `kb_agent.py`、`text2sql_demo.py`、`demo-agent-with-tools-arg.py` 或 `agent_harness_demo.py` 且模型发起工具调用
- **THEN** 工具调用行（如 `🔧 调用工具`）、SQL 执行与查询结果、轮次标题等中间步骤以灰色显示

#### Scenario: 不再存在青色或白色的过程着色
- **WHEN** 检查所有现役 CLI demo 脚本源码
- **THEN** 不存在用青色（`\033[36m`）或白色（`\033[37m`）着色输出的语句，archive/ 目录除外

### Requirement: 最终结果使用终端默认色
所有 CLI demo 脚本打印最终结果与回答时，MUST NOT 施加任何 ANSI 颜色转义码，使用终端默认前景色输出。最终结果包括：模型的最终回答正文、流式 JSON 输出、Pydantic 校验后的对象展示、`最终回答:` 内容。

#### Scenario: 流式回答以默认色输出
- **WHEN** 学员运行 `mini_rag_demo.py`、`kb_agent.py`、`text2sql_demo.py` 等脚本且模型流式生成最终回答
- **THEN** 回答正文逐字打印且不带任何 ANSI 颜色码，呈现终端默认前景色

#### Scenario: first_llm_app.py 回复去掉青色
- **WHEN** 学员运行 `first_llm_app.py` 且模型返回正文
- **THEN** "回复:"标记与回复正文以终端默认色输出，不再使用 `\033[36m`

### Requirement: 数据路径不泄漏 ANSI 转义码
着色 MUST 仅作用于终端打印的格式化层。累积进 `messages` 历史的文本、函数返回值（如流式累积的 content）、写入日志文件的内容 SHALL 为未着色的原始文本。

#### Scenario: messages 历史不含颜色码
- **WHEN** 任一 agent 脚本将流式累积的 content 或 tool_calls 追加进 `messages`
- **THEN** 追加的字符串中不含 `\033` 转义序列

#### Scenario: 日志文件不含颜色码
- **WHEN** `demo-agent-with-tools-arg.py` 运行并写入 `agent_debug.log`
- **THEN** 日志文件内容为纯文本，不含 ANSI 转义码（控制台输出可以是灰色）

### Requirement: 着色常量自包含于各脚本
每个需要着色的脚本 SHALL 在文件内自行定义 `GRAY`/`RESET` 常量，MUST NOT 引入公共工具模块或第三方着色库（rich/colorama）。

#### Scenario: 脚本独立复制运行
- **WHEN** 将任有着色改动的脚本单独复制到新环境（依赖已装）
- **THEN** 脚本可直接运行，着色正常，不因缺少仓库内其他模块而报错

### Requirement: 文档与实现一致
`实验手册.md` 中涉及输出观察点的描述 SHALL 与实际着色行为一致，统一描述为"灰色过程信息 + 默认色最终回答"。

#### Scenario: 手册观察点与实机输出一致
- **WHEN** 学员按实验手册运行实验 2/3/4/7/8/9 并核对观察点
- **THEN** 手册中关于输出样式的描述与终端实际显示的颜色语义一致
