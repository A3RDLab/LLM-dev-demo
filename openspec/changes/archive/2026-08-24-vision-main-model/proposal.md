# Proposal: vision-main-model

## Why

`agent_harness_demo` 的主模型默认是纯文本的 DeepSeek-V3（硅基流动），agent 无法"看图"。而 skill 生态里的典型任务（如 annual-report-to-kb 的图表识别阶段：组织图→mermaid、数据图→JSON）恰恰需要视觉能力；deepagents 0.7.4 的 `read_file` 工具对 `.jpg/.png/.webp` 等图片已经自动返回 base64 多模态 content block（`middleware/filesystem.py` 的图像管线），管线是现成的，缺的只是一台多模态主模型。把默认模型换成百炼 `qwen3.8-max`（多模态旗舰，实测图像识别与 function calling 均正常）即可零新增工具地补齐读图能力。

## What Changes

- `agent_harness_demo.py`：默认 `--model` 由 `MODEL` 环境变量（硅基流动 DeepSeek-V3 兜底）改为字面量 `qwen3.8-max`；默认 `--base_url` 改为读 `DASHSCOPE_BASE_URL`（兜底 `https://dashscope.aliyuncs.com/compatible-mode/v1`）；默认 `--api_key` 改为优先读 `DASHSCOPE_API_KEY`。保留 `--model/--base_url/--api_key` 覆盖能力（切回硅基流动等其他平台不受影响，但读图任务需要多模态模型）。
- `agent_harness_demo.py`：`ChatOpenAI` 增加 `extra_body={"enable_thinking": False}`（qwen3.5–3.8 系列默认开思考，agent 工具循环需要快响应；实测端点接受该参数）。
- `agent_harness_demo.py`：`SYSTEM_PROMPT` 增加读图指引——图片文件可直接 `read_file` 获取图像内容，用于图表识别类任务。
- `agent_harness_demo/data/`：新增 1–2 张工行年报图表 jpeg（取自 `wiki_kb_agent_demo/knowledge_base/ICBC_2024_年报/assets/`）作读图实验素材。
- 文档同步（仓库强制约定）：`agent_harness_demo/README.md`、`agent_harness_demo/实验指南.md`（新增读图实验）、根 `实验手册.md` 实验 11、`AGENTS.md`（默认平台注记）。
- 不改动：`DEFAULT_TASK` 销售分析主线、`skills/xlsx/`、deepagents 包本身、其他 demo 的默认配置。

## Capabilities

### New Capabilities
- `agent-harness-vision`: agent_harness_demo 的多模态读图能力——主模型为多模态模型时，`read_file` 读取图片返回图像内容，agent 能描述/识别图表并按 skill 规范产出结构化结果。

### Modified Capabilities
（无——现有销售分析任务行为不变，仅默认模型与端点变更。）

## Impact

- **代码**：仅 `agent_harness_demo.py` 一处（默认参数、model_kwargs、系统提示词三小点）。
- **文档**：README/实验指南/实验手册实验 11/AGENTS.md 同步；默认平台由硅基流动改为百炼（DashScope），文档需写明切换方法。
- **约束**：读图依赖多模态主模型；若用 `--model` 切回纯文本模型，读图任务不可用（文档说明）。`enable_thinking=False` 为百炼端点参数，其他平台若不识别可能报错——实现时用 try 探测或文档标注（以实测为准）。
- **依赖**：无新增第三方依赖（`langchain-openai` 既有）。
- **密钥**：`.env` 中 `DASHSCOPE_API_KEY` 需具备 `qwen3.8-max` 调用权限（已实测可用；企业实例"模型可见≠可调"，换 key 时需先 `curl $API_BASE/models` + 实调验证）。
