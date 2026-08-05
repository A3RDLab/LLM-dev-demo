# Agent Harness 演示（DeepAgents + Agent Skills）

## 概述

**Agent Harness（智能体外壳）** 指模型之外的那层运行时：系统提示词设计、工具编排与派发、上下文管理（截断/压缩）、错误恢复、权限控制。同一个模型套上不同的 harness，能力表现天差地别——Claude Code、Cursor、Pi 都是 harness 的产物。

本 demo 用 [LangChain DeepAgents](https://docs.langchain.com/oss/python/deepagents/overview) 演示一个 Claude Code 式 harness 的核心部件，并接入一个**现成的开源 Skill**（[anthropics/skills](https://github.com/anthropics/skills) 官方仓库的 `xlsx` skill），观察 **Skill 三层渐进式披露（progressive disclosure）** 的全过程。

与前置 demo 的递进关系：`demo-agent-with-tools-arg.py`（手写调用循环）→ `langgraph_demo/`（手搓图编排）→ **本 demo（框架化的完整 harness）**。

📋 **分步实验指南见 [实验指南.md](实验指南.md)**：四个递进实验（端到端跑通 → Skill 路由负例 → 自定义数据源 → 与手写循环对照）+ 常见问题排查。

## 目录结构

```
agent_harness_demo/
├── agent_harness_demo.py   # 主脚本
├── 实验指南.md             # 分步实验手册（建议按此顺序上手）
├── skills/xlsx/            # 现成 Skill（来自 anthropics/skills，完整未裁剪，见下方说明）
│   ├── SKILL.md            # Skill 指令主体（frontmatter + 正文）
│   ├── LICENSE.txt
│   └── scripts/            # Skill 自带脚本：recalc.py 公式重算、LibreOffice 助手、OOXML 校验器
├── data/                   # 任务输入：销售记录 Excel（拷贝自仓库根目录）
├── output/                 # agent 生成的 Excel 产物（运行后出现）
└── requirements.txt
```

## DeepAgents 核心部件对照

`create_deep_agent()` 一行代码得到的 harness 包含：

| 部件 | 内置实现 | 本 demo 中的观察点 |
|---|---|---|
| 规划 | `write_todos` 工具，引导模型先列任务清单 | 复杂任务开始时模型会先写 todo |
| 文件系统 | `read_file` / `write_file` / `edit_file` / `ls` / `glob` / `grep` / `delete`，由 `FilesystemBackend` 支撑（本 demo 直接映射本目录） | agent 读 `data/` 数据、写 `report.md` 与 `output/` |
| 子代理 | `task` 工具，把子任务派发给独立上下文执行 | 本 demo 任务较简单，默认不触发；可通过 `--task` 给多步任务观察 |
| Skills | `SkillsMiddleware`：启动时注入元数据，按需加载正文与资源 | 见下节 |
| 上下文管理 | Summarization 中间件：上下文过长时自动摘要压缩 | 长任务中自动触发 |

自定义工具只需在 `tools=[...]` 中追加（本 demo 加了一个 `execute_python` 沙箱执行工具，让 agent 能真正跑 pandas 分析代码）。

## Skill 开放标准与渐进式披露

**Agent Skills** 是 Anthropic 2025 下半年发布的开放标准（见 [agentskills.io](https://agentskills.io)）：一个 Skill 就是一个文件夹，核心是带 YAML frontmatter 的 `SKILL.md`，可附 `scripts/`、`references/`、`assets/`。截至 2026 年中已被 Claude Code、Cursor、Gemini CLI 等 27+ 平台支持。

关键设计是**三层渐进式披露**——不把所有知识塞进提示词，而是按需加载：

| 层级 | 加载内容 | 时机 | 本 demo 观察点 |
|---|---|---|---|
| 1. 元数据 | frontmatter 的 `name` + `description` | agent 启动，注入系统提示词 | 启动提示词中只有 xlsx 的一句话描述 |
| 2. 指令 | 完整 `SKILL.md` 正文 | 模型判断任务匹配后 `read_file` 读取 | 轨迹中打印 `<<< 第 2 层` 标记 |
| 3. 资源 | `scripts/` / `references/` 附属文件 | 按正文指引，需要时才读 | 轨迹中打印 `<<< 第 3 层` 标记；agent 还会通过 subprocess 真正执行 `scripts/recalc.py` |

运行后观察终端输出的工具调用序列，三层加载过程一目了然。

## 跨 harness 对照：同一份 SKILL.md 在 Claude Agent SDK 的用法

Skill 是**格式标准**，同一份 `skills/xlsx/` 在不同 harness 里通用。Claude Agent SDK（Claude Code 同款引擎）的等价写法：

```python
from claude_agent_sdk import query, ClaudeAgentOptions

options = ClaudeAgentOptions(
    setting_sources=["project"],   # 自动发现项目下 .claude/skills/ 中的 Skill
)
async for message in query(prompt="分析 data/ 里的销售 Excel 并出报告", options=options):
    print(message)
```

但要注意：**格式通用 ≠ 行为通用**。各 harness 的 Skill 扫描路径、触发加载策略、脚本执行权限各自为政——DeepAgents 通过 backend 相对路径发现、由模型 `read_file` 加载；Claude Code 扫描 `.claude/skills/`；加载时机与权限模型也不一致。迁移 Skill 时格式免改，行为要按目标 harness 验证。

## 同类 harness 项目速览

| 项目 | 形态 | 特点 |
|---|---|---|
| [Pi](https://github.com/earendil-works/pi)（pi.dev） | 独立 coding agent CLI（TypeScript） | 极简内核 + 自扩展（extensions），理念是"为你自己而造的 harness"，适合研究工作流定制与最小 harness 设计 |
| DeepAgents（本 demo） | 嵌入式 Python 库 | 把 Claude Code 式 harness 打包成组件，嵌进你自己的应用，适合教学与产品集成 |
| OpenHands / goose / aider / crush | 独立 coding agent CLI | 各有侧重的成熟开源 coding agent |
| OpenAI Agents SDK | 嵌入式 Python 库 | handoffs/guardrails 设计优秀，但原生 Skills 尚在路线图中（见其 GitHub issue） |

**Pi 与 DeepAgents 的区别**：前者是"成品 harness 产品"（你在终端里用它干活），后者是"harness 积木库"（你在代码里组装自己的 agent）。同一思想（harness = 模型外的运行时外壳）的两种形态。

## 快速开始

```bash
pip install -r requirements.txt

# 配置 Key（复用仓库根目录 .env 的 API_KEY，或 export）
export API_KEY=<硅基流动等 OpenAI 兼容平台的 Key>
# Windows PowerShell：$env:API_KEY="<Key>"

# 默认任务：按 xlsx skill 规范分析销售数据，产出 report.md + output/report.xlsx
python agent_harness_demo.py

# 自定义任务与模型
python agent_harness_demo.py --task "分析各地区的销售分布" \
    --model qwen-max --base_url https://dashscope.aliyuncs.com/compatible-mode/v1 \
    --api_key $DASHSCOPE_API_KEY
```

## 现成 Skill 出处与完整性说明

`skills/xlsx/` 来自 [anthropics/skills](https://github.com/anthropics/skills)（Anthropic 官方 Skill 仓库，source-available 许可见其 `LICENSE.txt`），是支撑 Claude 文档能力的生产级 Skill。本 demo **完整保留了官方目录（SKILL.md + scripts/），未做任何裁剪**，Skill 全程可执行：

- `scripts/recalc.py`：用 LibreOffice 对产出的 Excel 做公式重算，返回 JSON 错误报告（`status` / `total_errors` / `error_summary`）；
- `scripts/office/`：LibreOffice 沙箱环境助手（`soffice.py`）与 OOXML schema 校验器（`validate.py` + `schemas/`）。

运行前提：公式重算依赖 **LibreOffice**（`soffice` 在 PATH 中可用，macOS 可用 `brew install --cask libreoffice` 安装）。agent 按系统提示词约定，在 `execute_python` 中通过 subprocess 以 `skills/xlsx/scripts/` 为工作目录调用这些脚本（脚本内部 `from office.soffice import ...` 的导入约定要求如此）。这正好演示了第 3 层披露的完整形态：附属资源不只是被"读"，还会被真正**执行**。

优雅降级另行安排：若目标环境缺 LibreOffice，可在系统提示词中约定"脚本不可用时跳过并在报告中说明"，体现 Skill 作为自然语言指令包的弹性；本 demo 默认环境完整，不走降级路径。

## 注意事项

- 本 demo 在 macOS 实测通过；Windows 用户请先阅读 [实验指南.md](实验指南.md) 的"Windows 用户注意"小节（主要是 LibreOffice 重算链的 PATH 适配，其余为跨平台纯 Python）
- 切勿在代码中硬编码 API Key
- `execute_python` 工具会真实执行模型生成的代码且无隔离，仅用于本地学习演示，勿在生产环境照搬；生产沙箱可参考 `excel-process/` 的做法
- 人工智能生成内容仅供参考
