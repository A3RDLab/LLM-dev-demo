# Agent Harness 演示 Demo（DeepAgents + 现成 Skill）

## 目标
在现有学习路线（手写 function calling → LangGraph 编排）之上，补上 **Agent Harness** 一环：演示 harness 的核心部件（规划、文件系统、子 agent、上下文管理）与 **Agent Skills 渐进式披露**机制，并接入一个现成的开源 Skill 跑通端到端任务。

## 新增目录：`function_call_and_agent_demo/agent_harness_demo/`

### 文件结构
```
agent_harness_demo/
├── agent_harness_demo.py      # 主脚本
├── skills/                    # 现成 Skill（从 anthropics/skills 拷贝轻依赖的一个）
│   └── <选定的现成 skill>/
│       ├── SKILL.md
│       └── references/...
├── data/                      # 任务输入数据（拷贝根目录 2023年8月-9月销售记录.xlsx）
├── requirements.txt           # deepagents、langchain-openai、openpyxl 等
└── README.md
```

### 主脚本要点（`agent_harness_demo.py`）
- `create_deep_agent(model=ChatOpenAI(...), backend=FilesystemBackend(root_dir=工作目录), skills=["skills/"])`
- 模型走仓库惯例：`--model/--api_key/--base_url` 参数，默认硅基流动，`.env` 读 Key
- 演示任务："读取 data/ 中的销售记录 Excel，按 Skill 规范分析并生成格式化报告文件"
- 打印完整消息轨迹，重点标注三个可观察点：
  1. 启动时系统提示词只含 Skill 的名称+描述（第一层）
  2. agent 主动调用 Skill 后完整 SKILL.md 进入上下文（第二层）
  3. 按需读取 references 参考文档（第三层）
- 附带展示 harness 内置部件：todo 规划、虚拟文件系统读写、子 agent 派发（若任务需要）

### README.md 内容
1. 什么是 Agent Harness：模型外的运行时外壳（系统提示、工具编排、上下文管理、错误恢复）
2. DeepAgents 核心部件对照表（planning / filesystem / subagents / skills）
3. Skill 开放标准与渐进式披露机制讲解
4. **跨 harness 对照**：同一份 SKILL.md 在 Claude Agent SDK 的写法（代码片段），说明格式通用但发现/加载/权限行为各家不同
5. **Pi 对比章节**：极简自扩展 harness 的内核设计，以及 OpenHands、goose、OpenAI Agents SDK 等同类项目速览
6. 快速开始与运行示例

### 根目录更新
- `README.md`：Demo 索引 Agent 表中 langgraph_demo 之后加一行：`agent_harness_demo/` | 进阶：Agent Harness（DeepAgents）+ Agent Skills 渐进式披露
- 推荐学习路线第 2 步追加 agent_harness_demo

## 现成 Skill 选定原则
从 [anthropics/skills](https://github.com/anthropics/skills) 挑选：优先文档/数据处理类（如 xlsx 相关），依赖仅限 openpyxl 等常见库；拷贝时保留 SKILL.md + 必要 references，README 注明出处与裁剪说明。

## 依赖处理
- 新建独立 `requirements.txt`（deepagents、langchain-openai、openpyxl）
- 根目录 `requirements.txt` 头部注释中补一行指向该文件

## 测试计划
1. `pip install -r agent_harness_demo/requirements.txt`
2. 用现有 `API_KEY`（硅基流动）运行主脚本，确认：Skill 被自动发现、三层披露过程在轨迹中可见、最终报告文件生成成功
3. 检查 README 中运行命令与实际参数一致

## 假设
- 使用你现有的硅基流动/百炼 Key，不引入 Anthropic API
- 现成 Skill 若含重型依赖（如 LibreOffice），改选轻量替代项并在 README 说明
- Skill 文件按仓库 .gitignore 惯例正常提交（无敏感内容）