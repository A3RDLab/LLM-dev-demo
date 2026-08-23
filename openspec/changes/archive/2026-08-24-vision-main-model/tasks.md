# Tasks: vision-main-model

## 1. 代码改动（agent_harness_demo.py）

- [x] 1.1 默认参数：`--model` 默认值改为 `qwen3.8-max`；`--base_url` 默认改为 `os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")`；`--api_key` 取值顺序改为 `args → DASHSCOPE_API_KEY → API_KEY`，缺失时报错文案同步更新
- [x] 1.2 `ChatOpenAI(...)` 增加 `extra_body={"enable_thinking": False}`（实测 langchain-openai 1.4.1 支持直接传 `extra_body=` 字段，比嵌套 model_kwargs 更干净）
- [x] 1.3 `SYSTEM_PROMPT` 工作方式约定新增一条：图片文件（.jpg/.png 等）可直接 `read_file` 获取图像内容，用于图表识别/看图类任务
- [x] 1.4 文件头 docstring 的运行示例与说明同步（默认平台百炼、多模态）
- [x] 1.5 （实施中发现）`ChatOpenAI` 增加 `disable_streaming=True`：流式下模型消息以 `AIMessageChunk` 分片到达，`run()` 的观察点打印只认完整 `AIMessage`，切换新模型后工具调用头与模型回复全部不显示；另给 `ToolMessage` 分支加图像 block 的友好显示（`返回多模态内容：image(image/jpeg)`）
- [x] 1.6 （实施中发现）`ChatOpenAI` 增加 `timeout=300`：默认无超时，回归实测中遇到对端断连（TCP CLOSED）请求永久挂起

## 2. 实验素材

- [x] 2.1 拷贝 `p013_1.jpeg`（客户规模/贷款信息图）→ `data/icbc_p013_infographic.jpeg`；`p033_1.jpeg`（2023/2024 资产结构饼图）→ `data/icbc_p033_pie_asset_structure.jpeg`

## 3. 实机验证

- [x] 3.1 读图任务：信息图描述通过——轨迹含 `read_file` 工具头 + `返回多模态内容：image(image/jpeg)`，模型回复数字全部准确（对公客户 1,334.86 万户、个人客户 7.66 亿、网点 15,365、手机银行 5.88 亿、绿色贷款超 6 万亿、制造业/涉农 4.4 万亿、战新 3 万亿）
- [x] 3.2 结构化识别：双环饼图 → `output/chart.json`，JSON 合法、2023/2024 两个 series 各 6 条占比数据，agent 自行用 execute_python 完成校验
- [x] 3.3 默认任务回归：无参数跑通——`<<< 第 2 层` 读 SKILL.md 标记出现、`recalc.py` 返回 `status: success, 97 formulas, 0 errors`、`report.md` 与 `output/report.xlsx`（4 工作表、真实公式）产出，总销售额 5,456,735 元等数值正确（首次运行遇对端断连挂起，加 `timeout=300` 后重跑通过）

## 4. 文档同步（仓库强制约定）

- [x] 4.1 `agent_harness_demo/README.md`：默认平台百炼说明、新增「多模态读图」章节、切回其他平台命令、多模态依赖注意事项
- [x] 4.2 `agent_harness_demo/实验指南.md`：新增「实验 5：多模态读图」（5a 描述信息图 / 5b 饼图→JSON），准备阶段 Key 说明改为 DASHSCOPE_API_KEY，常见问题加"模型看不见图"条目
- [x] 4.3 根 `实验手册.md` 实验 11：负例对照后新增「多模态读图」玩法段
- [x] 4.4 `AGENTS.md`：新增「agent_harness_demo 默认平台为百炼 qwen3.8-max（多模态）」条目（含 disable_streaming / enable_thinking 注记）

## 5. 收尾

- [x] 5.1 openspec archive change `vision-main-model`
- [x] 5.2 git commit（用户新增要求：change 1 成功后先提交，再开始 change 2）
