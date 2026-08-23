# Spec: agent-skill-install

## ADDED Requirements

### Requirement: install_skill 工具

agent SHALL 获得 `install_skill(source_path)` 工具：接受 backend 根目录内的 zip 包路径或 skill 目录路径，完成校验、落盘到 `skills/<name>/`、并热刷新 skill 清单；全程无需重启会话。

#### Scenario: 自然语言触发安装

- **WHEN** 用户任务中包含"安装 skill_submissions/xxx.zip"之类的指令，agent 调用 `install_skill({'source_path': 'skill_submissions/xxx.zip'})`
- **THEN** 工具返回安装摘要（skill 名、文件数、当前清单 skill 数），且 `skills/` 下出现 `<name>/SKILL.md`

#### Scenario: 安装后立即可用

- **WHEN** install_skill 成功返回后的下一轮模型调用
- **THEN** 系统提示词的 skill 清单包含新装 skill 的 name + description（state 热更新，无需重启），agent 可按第 2 层披露 read_file 其 SKILL.md 并执行其中规范

### Requirement: 安全校验

install_skill SHALL 在解压前完成安全校验并拒绝违规输入：zip 条目不得含绝对路径、`..` 路径段或符号链接；SKILL.md 必须存在（zip 内 3 层深度以内且恰好一个，以其所在目录为 skill 根）；校验全部通过才落盘，任一失败则不产生任何文件且返回可读的错误说明。

#### Scenario: zip-slip 攻击被拒

- **WHEN** zip 包内存在条目路径含 `../` 或以 `/` 开头
- **THEN** 安装被拒绝，返回错误说明，`skills/` 目录无任何新增

#### Scenario: 缺失 frontmatter 字段被拒

- **WHEN** SKILL.md 的 YAML frontmatter 缺 `name` 或 `description`
- **THEN** 安装被拒绝并明确指出缺失字段（对比：deepagents 扫描对此静默跳过）

#### Scenario: 嵌套布局自动定位

- **WHEN** zip 内 skill 不在根层级（如 `.qoder/skills/annual-report-to-kb/SKILL.md`）
- **THEN** install_skill 以 SKILL.md 所在目录为 skill 根，只安装该子树到 `skills/annual-report-to-kb/`

### Requirement: 命名与内容规范

install_skill SHALL 对 frontmatter 执行 Agent Skills 规范校验：`name` 非空、≤64 字符、仅小写字母/数字/单连字符且不以连字符开头结尾、与目录名一致；`description` 必填且 ≤1024 字符；SKILL.md ≤10MB；`skills/` 下同名目录已存在时拒绝安装并提示先删除。

#### Scenario: name 与目录名不一致

- **WHEN** frontmatter `name: my-skill` 但 SKILL.md 位于 `foo/` 目录
- **THEN** 安装被拒绝，错误信息给出"改名目录或改 name 字段"的建议

#### Scenario: 重复安装被拒

- **WHEN** `skills/annual-report-to-kb/` 已存在，再次安装同名 skill
- **THEN** 拒绝安装并提示先删除既有目录

### Requirement: 热刷新机制

`RefreshableSkillsMiddleware` SHALL 作为官方 `SkillsMiddleware` 的同名替换接入（保持 subagent 的 skills 继承路径），install_skill 成功后用 deepagents 的扫描逻辑重扫全部 sources，并以 `Command(update={"skills_metadata": ..., "skills_load_errors": ...})` 更新 state，使 skill 清单在下一次模型调用生效。

#### Scenario: 同名替换不产生重复清单

- **WHEN** agent 启动，系统提示词中 skill 清单只出现一次
- **THEN** 每个 skill 的 name+description 仅列一遍（无两段重复的 Skills 小节）

#### Scenario: 官方预置 skill 不受影响

- **WHEN** 安装任意新 skill 前后
- **THEN** `skills/xlsx` 始终在清单中且行为不变

### Requirement: 示例 skill 素材

仓库 SHALL 在 `agent_harness_demo/skill_submissions/` 提供示例 zip（annual-report-to-kb），供实验与校验逻辑回归直接使用。

#### Scenario: 示例 zip 开箱可装

- **WHEN** 用户按实验 6 命令让 agent 安装 `skill_submissions/annual-report-to-kb.zip`
- **THEN** 安装成功，后续可按该 skill 的规范处理年报 PDF（切分知识库 + 看图识别阶段衔接 agent-harness-vision 能力）
