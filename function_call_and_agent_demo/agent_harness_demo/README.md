# Agent Harness 演示（DeepAgents + Agent Skills）

## 概述

**Agent Harness（智能体外壳）** 指模型之外的那层运行时：系统提示词设计、工具编排与派发、上下文管理（截断/压缩）、错误恢复、权限控制。同一个模型套上不同的 harness，能力表现天差地别——Claude Code、Cursor、Pi 都是 harness 的产物。

本 demo 用 [LangChain DeepAgents](https://docs.langchain.com/oss/python/deepagents/overview) 演示一个 Claude Code 式 harness 的核心部件，并接入一个**现成的开源 Skill**（[anthropics/skills](https://github.com/anthropics/skills) 官方仓库的 `xlsx` skill），观察 **Skill 三层渐进式披露（progressive disclosure）** 的全过程。

主模型默认百炼 `qwen3.8-max`（**多模态**）：deepagents 内置的 `read_file` 读图片时返回图像 block，agent 能直接"看图"（年报图表识别、截图分析等），无需任何额外工具——见下文"多模态读图"。

与前置 demo 的递进关系：`demo-agent-with-tools-arg.py`（手写调用循环）→ `langgraph_demo/`（手搓图编排）→ **本 demo（框架化的完整 harness）**。

📋 **分步实验指南见 [实验指南.md](实验指南.md)**：六个递进实验（端到端跑通 → Skill 路由负例 → 自定义数据源 → 与手写循环对照 → 多模态读图 → 运行时安装 skill）+ 常见问题排查。

## 目录结构

```
agent_harness_demo/
├── agent_harness_demo.py   # 主脚本
├── skill_installer.py      # install_skill 工具 + skill 清单热刷新 middleware
├── 实验指南.md             # 分步实验手册（建议按此顺序上手）
├── skills/xlsx/            # 现成 Skill（来自 anthropics/skills，完整未裁剪，见下方说明）
│   ├── SKILL.md            # Skill 指令主体（frontmatter + 正文）
│   ├── LICENSE.txt
│   └── scripts/            # Skill 自带脚本：recalc.py 公式重算、LibreOffice 助手、OOXML 校验器
├── skill_submissions/      # 用户提交的 skill 包（zip/目录），agent 用 install_skill 安装
├── data/                   # 任务输入：销售记录 Excel + 年报图表 jpeg（读图实验素材）
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

# 配置 Key（复用仓库根目录 .env 的 DASHSCOPE_API_KEY；可选 DASHSCOPE_BASE_URL 指定专属端点）
# Windows PowerShell：$env:DASHSCOPE_API_KEY="<Key>"

# 默认任务（qwen3.8-max @ 百炼）：按 xlsx skill 规范分析销售数据，产出 report.md + output/report.xlsx
python agent_harness_demo.py

# 多模态读图：read_file 读图片返回图像本身，模型直接看图
python agent_harness_demo.py --task "用 read_file 读取 data/icbc_p013_infographic.jpeg，描述图表类型与关键数据"

# 切换其他平台（注意：读图任务需多模态模型，纯文本模型不行）
python agent_harness_demo.py --task "分析各地区的销售分布" \
    --model Pro/deepseek-ai/DeepSeek-V3 --base_url https://api.siliconflow.cn/v1/ \
    --api_key $API_KEY
```

## 多模态读图

deepagents 的文件系统工具链已内置多模态管线：`read_file` 对 `.jpg/.png/.webp` 等图片按 base64 读取，以图像 content block 返回，多模态主模型（如 `qwen3.8-max`）能直接"看到"图。轨迹中的表现：

```
[01] 🛠  调用工具 read_file({'file_path': 'data/icbc_p033_pie_asset_structure.jpeg'})
     ↳ 返回多模态内容：image(image/jpeg)，图像直接进入模型上下文
```

- 实测（2026-08）：`qwen3.8-max` 对年报信息图的数字识别、双环饼图→JSON 结构化均准确；
- `extra_body={"enable_thinking": False}`：qwen3.5–3.8 系列默认开思考，已关闭以保证工具循环响应速度（其他平台若不识别该参数，换模型时注意）；
- 成本提示：图像按约 32×32 像素/token 计费，大图/多图任务注意上下文与费用。

## 提交你自己的 skill（运行时安装）

deepagents 官方的 `SkillsMiddleware` 只在会话启动时扫描一次 `skills/`，本 demo 用 `skill_installer.py` 里的 `RefreshableSkillsMiddleware` 补上了"运行时安装"：agent 拿到一个 `install_skill` 工具，装完立即热刷新 skill 清单，**无需重启会话**（原理：清单是每次模型调用从 state 重新渲染的，装完更新 state 即生效）。

```bash
# 1. 把 skill 包放进 skill_submissions/（zip 或目录均可，zip 内允许 .qoder/skills/<name>/ 等嵌套布局）
cp my-skill.zip skill_submissions/

# 2. 任务里一句话让 agent 自己装
python agent_harness_demo.py --task "用 install_skill 安装 skill_submissions/my-skill.zip，然后按它的规范处理 ..."
```

`install_skill` 的校验（`skill_installer.py`）：zip-slip 防护（拒绝绝对路径/`..`/符号链接条目）；`SKILL.md` frontmatter 必须有 `name`（小写字母/数字/单连字符、≤64 字符、与目录名一致）和 `description`（≤1024 字符）；同名 skill 已存在时拒绝。所有错误信息面向提交者可读——对比 deepagents 原生行为：frontmatter 缺字段是**静默跳过**的，装完不报错但清单里没有，这正是安装器要显式报错的原因。

约定与边界：

- **卸载 = 删除目录**：`rm -rf skills/<name>/`（运行时安装的 skill 不进 git，`.gitignore` 只保留官方 `skills/xlsx/`）；
- `skill_installer.py` 使用了 deepagents 0.7.x 的私有扫描函数 `_list_skills_with_errors`，`requirements.txt` 已锁 `deepagents>=0.7,<0.8`（同类先例：根目录 `mcp[cli]<2`）；
- 热刷新只作用于主 agent 循环；启用 checkpointer 的生产用法需自行处理重扫语义；
- `install_skill` 与 `execute_python` 同属本地教学的信任模型（解压落盘 + 执行 skill 脚本都是真实副作用），勿在生产照搬。

示例包：`skill_submissions/annual-report-to-kb.zip`（年报 PDF → 层级化 Markdown 知识库，含目录解析/页码校验/表格重建/图表识别），配合多模态读图能力可端到端跑通"装 skill → 切年报 → 看图识别"，见实验指南实验 6。

## 现成 Skill 出处与完整性说明

`skills/xlsx/` 来自 [anthropics/skills](https://github.com/anthropics/skills)（Anthropic 官方 Skill 仓库，source-available 许可见其 `LICENSE.txt`），是支撑 Claude 文档能力的生产级 Skill。本 demo **完整保留了官方目录（SKILL.md + scripts/），未做任何裁剪**，Skill 全程可执行：

- `scripts/recalc.py`：用 LibreOffice 对产出的 Excel 做公式重算，返回 JSON 错误报告（`status` / `total_errors` / `error_summary`）；
- `scripts/office/`：LibreOffice 沙箱环境助手（`soffice.py`）与 OOXML schema 校验器（`validate.py` + `schemas/`）。

运行前提：公式重算依赖 **LibreOffice**（`soffice` 在 PATH 中可用，macOS 可用 `brew install --cask libreoffice` 安装）。agent 按系统提示词约定，在 `execute_python` 中通过 subprocess 以 `skills/xlsx/scripts/` 为工作目录调用这些脚本（脚本内部 `from office.soffice import ...` 的导入约定要求如此）。这正好演示了第 3 层披露的完整形态：附属资源不只是被"读"，还会被真正**执行**。

优雅降级另行安排：若目标环境缺 LibreOffice，可在系统提示词中约定"脚本不可用时跳过并在报告中说明"，体现 Skill 作为自然语言指令包的弹性；本 demo 默认环境完整，不走降级路径。

## 注意事项

- 本 demo 在 macOS 实测通过；Windows 已做代码适配（LibreOffice 路径自动探测、控制台 UTF-8 输出），操作步骤见 [实验指南.md](实验指南.md) 的"Windows 用户完整操作"小节（未实机验证）
- 默认平台为百炼（`qwen3.8-max`），Key 需有该模型调用权限——企业专属实例"模型可见 ≠ 可调"，换 Key 先 `curl $API_BASE/models` + 实调验证（见根目录 AGENTS.md）
- 读图依赖多模态主模型：`--model` 切到纯文本模型后，读图任务会失败或看不到图
- 切勿在代码中硬编码 API Key
- `execute_python` 工具会真实执行模型生成的代码且无隔离，仅用于本地学习演示，勿在生产环境照搬；生产沙箱可参考 `excel-process/` 的做法
- 人工智能生成内容仅供参考
