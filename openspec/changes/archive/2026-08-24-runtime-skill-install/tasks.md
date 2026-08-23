# Tasks: runtime-skill-install

## 1. skill_installer.py（新模块）

- [x] 1.1 校验函数：frontmatter 解析（pyyaml）与规范检查（name 非空/≤64/小写-连字符/等于目录名；description 必填≤1024；SKILL.md ≤10MB）；错误信息面向学员可读
- [x] 1.2 zip 处理：zip-slip 防护（绝对路径/`..`/符号链接条目拒绝）；3 层深度内定位唯一 SKILL.md 为 skill 根；先解压临时目录校验、全部通过才移入 `skills/<name>/`（拒绝时零残留）
- [x] 1.3 目录型 source 支持（指向 skill 根或含它的上层目录均可），同样校验后拷贝
- [x] 1.4 `RefreshableSkillsMiddleware(SkillsMiddleware)`：覆写 `name` 返回父类名（同名替换）；`tools` 贡献 `install_skill`；成功路径重扫 sources（import deepagents 私有 `_list_skills_with_errors`，注释标注锁版本原因）并返回 `Command(update={"skills_metadata": ..., "skills_load_errors": ...})` + ToolMessage 摘要；失败路径返回纯文本错误说明

## 2. 主脚本与配置

- [x] 2.1 `agent_harness_demo.py`：`create_deep_agent` 接入 `middleware=[RefreshableSkillsMiddleware(...)]`（保留 `skills=["skills/"]` 参数）；`SYSTEM_PROMPT` 增加 install_skill 用法与 `skill_submissions/` 提交约定
- [x] 2.2 `.gitignore`：`skills/*` + `!skills/xlsx/`
- [x] 2.3 `requirements.txt`：`deepagents>=0.7,<0.8`；显式 `pyyaml>=6`
- [x] 2.4 示例素材：附件 zip 收进 `skill_submissions/annual-report-to-kb.zip`
- [x] 2.5 单元级冒烟：不调 LLM，直接 python 调用校验/解压函数，验证合法 zip 通过、zip-slip 样本被拒、坏 frontmatter 被拒、重复安装被拒（临时目录内模拟）

## 3. 实机验证（LLM 端到端）

- [x] 3.1 安装任务：`--task "用 install_skill 安装 skill_submissions/annual-report-to-kb.zip，然后 read_file 它的 SKILL.md，总结它的工作流程"`——确认安装成功、下一轮清单含新 skill、第 2 层披露正常
- [x] 3.2 端到端：安装后让 agent 按该 skill 用 `scripts/build_kb.py` 处理一份年报 PDF（`archive/PDF_RAG_demo/ICBC_2024_FYR.pdf`），确认产出 `knowledge_base/` 结构（index.md + 章节 md + assets/）；逐图看图识别为选做（recursion_limit 内抽查 2 张即可）
- [x] 3.3 负例回归：确认 xlsx 预置 skill 清单与默认销售任务不受影响（跑一次实验 2 负例任务即可，不必跑完整默认任务）

## 4. 文档同步

- [x] 4.1 `agent_harness_demo/README.md`：新增「提交你自己的 skill」章节（约定、命令、校验规则、卸载=删目录、安全提醒）
- [x] 4.2 `agent_harness_demo/实验指南.md`：新增「实验 6：给 agent 装一个新 skill」（安装 → 清单热刷新观察 → 用 annual-report-to-kb 切年报 → 与 wiki_kb_agent_demo --kb-dir 衔接的选做闭环）
- [x] 4.3 根 `实验手册.md` 实验 11：增补 install_skill 玩法段
- [x] 4.4 `AGENTS.md`：更新 agent_harness_demo 条目（install_skill 机制、skill_submissions/ 约定、skills/* gitignore 约定、deepagents<0.8 锁因）

## 5. 收尾

- [x] 5.1 openspec archive change `runtime-skill-install`（spec 同步落位 agent-skill-install）
- [x] 5.2 git commit
