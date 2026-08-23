# Proposal: runtime-skill-install

## Why

agent_harness_demo 目前只认 `skills/` 下预置的 skill（xlsx）：deepagents 的 `SkillsMiddleware` 只在会话启动时扫描一次（`before_agent` 有 state 去重守卫，无官方 reload 机制），用户想在运行中给 agent 装一个新 skill（比如课堂上学员自己写的、或社区分享的 zip 包）必须手工解压到 `skills/` 再重启会话。"用户提交 skill、智能体自己安装"是 harness 可扩展性教学的高价值一环——而且 deepagents 的 skill 清单注入是每次模型调用从 state 重新渲染的（`modify_request` 读 `skills_metadata`），意味着只要装完 skill 更新 state，**下一轮模型调用即生效、无需重启**，这本身就是一个绝佳的"middleware 扩展官方组件"教学案例。

## What Changes

- 新增 `agent_harness_demo/skill_installer.py`：
  - `install_skill(source_path)` agent 工具：接受 zip 包或目录（backend 根目录内路径），完成"校验 → 落盘 → 热刷新"三步；
  - 校验规则（对齐 Agent Skills 规范与 deepagents 行为）：zip-slip 防护（拒绝绝对路径/`..`/符号链接条目）、SKILL.md 必须存在且 YAML frontmatter 合法（`name` 必填且为小写-连字符、≤64 字符、等于目录名；`description` 必填 ≤1024 字符）、SKILL.md ≤10MB；支持 zip 内 skill 不在根层级的常见布局（如 `.qoder/skills/<name>/SKILL.md`，自动定位唯一 SKILL.md）；
  - `RefreshableSkillsMiddleware(SkillsMiddleware)` 子类：贡献 `install_skill` 工具，安装成功后调用 deepagents 的扫描函数重扫 `skills/`，以 `Command(update={"skills_metadata": ...})` 热更新 state。
- `agent_harness_demo.py`：接入该 middleware（同名替换官方 SkillsMiddleware，保持 subagent 的 skills 继承路径）；`SYSTEM_PROMPT` 增加 install_skill 用法与提交约定。
- `agent_harness_demo/skill_submissions/annual-report-to-kb.zip`：示例 skill 包入库（用户提供，含 SKILL.md + pitfalls.md + scripts/build_kb.py）。
- `agent_harness_demo/.gitignore`：忽略 `skills/*` 但保留 `!skills/xlsx/`（运行时安装的 skill 不入库，官方 xlsx 除外）。
- `agent_harness_demo/requirements.txt`：`deepagents` 锁 `>=0.7,<0.8`（用了私有扫描函数，防破坏性升级，仿 `mcp[cli]<2` 先例）；显式声明 `pyyaml>=6`（frontmatter 解析）。
- 文档同步：README（「提交你自己的 skill」章节）、实验指南（新增实验 6）、实验手册实验 11 增补、AGENTS.md。

## Capabilities

### New Capabilities
- `agent-skill-install`: agent 运行时安装第三方 skill——用户把 zip/目录放进约定位置并在任务里说一句"安装 xxx"，agent 校验、解压到 `skills/`，skill 清单热刷新后立即可用（第 1/2/3 层披露照常工作）。

### Modified Capabilities
（无——现有 xlsx skill 与销售分析任务行为不变；安装新 skill 是增量能力。）

## Impact

- **代码**：新增 1 个模块（skill_installer.py，约 200 行），主脚本接线约 10 行。
- **文档**：README/实验指南/实验手册/AGENTS.md 同步；新增 skill_submissions/ 目录约定说明。
- **约束**：`install_skill` 校验失败要给出可读的错误（教学场景，让学员看懂为什么被拒）；同 skill 重复安装拒绝并提示；deepagents 私有 API `_list_skills_with_errors` 的使用以版本锁约束。
- **依赖**：无新增第三方包（pyyaml 为显式化声明，venv 中已随 deepagents 存在）。
- **安全**：zip-slip 防护必须有；`install_skill` 与 execute_python 同属"本地教学信任模型"——文档明示勿在生产照搬。
