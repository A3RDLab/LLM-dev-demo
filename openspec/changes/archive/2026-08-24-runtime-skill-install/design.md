# Design: runtime-skill-install

## Context

deepagents 0.7.4 的 SkillsMiddleware 机制（源码级调研结论，路径均指 site-packages/deepagents/）：

1. **扫描一次**：`before_agent`（skills.py:928-948）在 agent 图启动时扫描各 source 目录的一级子目录，凡含 `SKILL.md` 即解析 frontmatter 得 `SkillMetadata`；`if "skills_metadata" in state: return None`（skills.py:947）保证同会话/同 checkpoint thread 永不重扫，且全库无任何 refresh/reload 路径。
2. **每轮重渲染**：系统提示词里的 skill 清单由 `wrap_model_call → modify_request`（skills.py:900-926）在**每次模型调用**时从 `state["skills_metadata"]` 重新 format——state 一更新，下一轮立即生效，无需重建 graph。
3. **工具可更新 state**：deepagents 自己的文件工具直接返回 `Command(update={...})`（middleware/filesystem.py:2071-2078），LangGraph 会把 Command 的 update 合并进 agent state。`skills_metadata`/`skills_load_errors` 是 SkillsState 的字段，可经此路径写入。
4. **middleware 可替换官方组件**：`create_deep_agent(middleware=[...])` 中与栈内同名（`.name` 属性）的 middleware 原地替换（graph.py:201-235）；默认栈顺序 Skills → Filesystem → SubAgent → ... → 用户 middleware。主 agent 的 `skills` 参数同时被 general-purpose subagent 继承（graph.py:761-762）。

`FilesystemBackend.write` 自动 `mkdir(parents=True)`（backends/filesystem.py:505），agent 的 write_file 本可创建 skill 目录——缺的只是"校验 + 解压 + 刷新清单"这层编排。

## Goals / Non-Goals

**Goals:**

- 用户把 skill zip（或目录）放在 backend 视野内（推荐 `skill_submissions/`），在任务里用自然语言让 agent 安装；
- 安装后 skill 立即出现在第 1 层清单，agent 可按渐进式披露正常使用（读 SKILL.md → 用 scripts/）；
- 校验失败给出人话错误（frontmatter 缺字段、name 不合规、同名已装、zip 路径逃逸）；
- xlsx skill 与现有任务零影响；实现保持在 demo 目录内、代码可读可教学。

**Non-Goals:**

- 不做 skill 卸载/升级/版本管理（卸载 = 手工删目录，README 说明）；
- 不做 CLI `--install-skill` 预装入口（用户已选运行时工具方案）；
- 不做沙箱隔离与签名校验——与 `execute_python` 同属本地教学信任模型，文档明示；
- 不改 deepagents 包本体。

## Decisions

1. **子类同名替换而非并列新增 middleware**：`RefreshableSkillsMiddleware(SkillsMiddleware)` 覆写 `name` 返回父类名（"SkillsMiddleware"），`create_deep_agent(skills=["skills/"], middleware=[RefreshableSkillsMiddleware(...)])` 时它原地替换默认实例——主 agent 拿到 install_skill 工具与热刷新，subagent 的 skills 继承路径保持官方行为。若并列新增（不同名），会出现两个 SkillsMiddleware 各注入一段系统提示词（重复清单），故必须同名替换。
2. **install_skill 工具做在 middleware 内部**（`tools` 属性贡献），工具函数闭包持有 backend 与 sources；安装成功路径：校验 → 解压/拷贝到 `skills/<name>/`（真实文件系统操作，不经 backend.write 逐文件写——zip 里可能有几十个文件且含二进制）→ `_list_skills_with_errors` 重扫全部 sources → 返回 `Command(update={"skills_metadata": <新列表>, "skills_load_errors": <错误>})` + ToolMessage 摘要（装了什么、清单现在有几个 skill、下一步建议 read_file 读 SKILL.md）。校验失败返回纯文本 ToolMessage 说明原因，不改 state。
3. **私有 API `_list_skills_with_errors` 直接 import**：它是唯一能把 source 目录变成"与官方扫描完全一致"的 SkillMetadata 列表的函数（含 frontmatter 解析与校告警）。代价是私有——用 `deepagents>=0.7,<0.8` 版本锁兜底（仓库已有 `mcp[cli]<2` 同类先例），代码注释标注来源与锁版本原因。
4. **zip-slip 防护在解压前逐条目检查**：拒绝绝对路径、含 `..` 的相对路径、符号链接条目（`external_attr` 高 16 位 `S_ISLNK`）；解压到临时目录后先校验 SKILL.md，全部通过才 `shutil.move` 进 `skills/`——避免半装状态。
5. **支持"SKILL.md 不在 zip 根层级"**：实际生态里 zip 常打包成 `.qoder/skills/<name>/` 或 `<name>/` 前缀（本仓库的示例 zip 即是前者）。规则：在 zip 内定位 SKILL.md（限 3 层深度内、必须恰好一个），以它所在目录为 skill 根，只安装该子树。目录型 source 同理（指向 skill 根或其上层皆可）。
6. **校验规则对齐 deepagents 而非另立标准**：`name` 缺失/为空、`description` 缺失 → 拒绝（deepagents 会静默跳过，安装器必须显式报错，否则用户以为装好了）；`name` 与目录名不一致或含非法字符（非小写字母/数字/单连字符、>64 字符）→ 拒绝并给出改名建议；`description` >1024 → 拒绝（deepagents 是截断+告警，安装器从严，逼提交者自己收敛）；SKILL.md >10MB → 拒绝。同名目录已存在 → 拒绝，提示先删除。
7. **示例 zip 收进 `skill_submissions/`**（入库）：它是 change 1 读图能力的天然续篇（年报 PDF → 切分 → 看图识别），实验 6 用它做端到端演示；同时是校验逻辑的真实回归样本（嵌套布局 `.qoder/skills/annual-report-to-kb/`）。
8. **运行时安装的 skill 不入库**：`.gitignore` 加 `skills/*` + `!skills/xlsx/`。学员装的 skill 是本地运行时状态，混入 git 会污染教学仓库；xlsx 是官方预置内容必须保留。

## Risks / Trade-offs

- **deepagents 私有 API 漂移**：0.8 若改/删 `_list_skills_with_errors`，安装后刷新会 ImportError——版本锁拦在安装期；若未来升级，需同步适配（AGENTS.md 记注）。
- **Command 更新 state 与 checkpoint 的交互**：带 checkpointer 的会话中 skills_metadata 会被持久化（这正是官方"永不重扫"守卫的由来）；本 demo 未启用 checkpointer，每次运行全新 state，风险不触发。文档注明"启用 checkpointer 的生产用法需自行处理重扫语义"。
- **安全面**：install_skill 解压+落盘+执行 skill 脚本（配合 execute_python）都是真实副作用。教学仓库接受此信任模型（与 execute_python 一致），README/AGENTS.md 明示勿生产照搬；zip-slip 防御覆盖最常见的路径注入。
- **热刷新只影响主 agent**：subagent 的 skill 清单走自己的 SkillsMiddleware（构建时态）。demo 的任务形态（单 agent 主循环）不受影响，作为已知边界写进文档。
