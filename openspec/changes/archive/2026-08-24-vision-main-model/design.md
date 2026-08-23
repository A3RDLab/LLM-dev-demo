# Design: vision-main-model

## Context

`agent_harness_demo.py` 用 `ChatOpenAI(model=args.model, ...)` + `create_deep_agent` 构建 agent，当前默认值来自 `MODEL`/`API_BASE`/`API_KEY` 环境变量（硅基流动 + DeepSeek-V3，纯文本）。deepagents 0.7.4 的 `FilesystemMiddleware` 已实现多模态管线：`read_file` 按扩展名（`.png/.jpg/.jpeg/.webp/.gif/.heic/.heif`）把文件读为 base64，以 `ToolMessage(content_blocks=[{"type":"image","base64":...,"mime_type":...}])` 返回；`_scrub_unsupported_multimodal_content` 会按 model profile 清理模型不支持的 block（profile 缺省视为支持），`_move_media_results_after_tool_results` 保证消息顺序符合 OpenAI 类 provider 要求。即：**代码路径零改动，只要主模型是多模态的，`read_file` 图片就能被模型"看见"**。

百炼侧实测（2026-08-24，qwen3.8-max @ compatible-mode）：

- 图像输入（data URL base64）→ 准确描述工行年报信息图（数字识别正确）。
- function calling（带 system prompt）→ 单次、参数正确的 tool call，两次复测稳定；**无 system prompt 时出现幻觉示例调用与重复调用**，deepagents 场景恒有系统提示词，不受影响。
- `enable_thinking=False` 参数被端点接受（qwen3.5–3.8 默认开思考，关闭以保证 agent 循环响应速度与输出干净）。
- 企业专属实例"模型可见 ≠ 可调"：`/models` 列表 241 个模型，但旧 key 实调除 `qwen3.6-27b` 外全部 403；换 key 需实调验证，不能只看列表。

## Goals / Non-Goals

**Goals:**

- agent_harness_demo 开箱即用具备读图能力（默认 `qwen3.8-max` @ 百炼）。
- 销售分析默认任务行为不回归（xlsx skill、recalc 校验流程照旧）。
- 保留仓库约定：`--model/--api_key/--base_url` 可覆盖切回任意 OpenAI 兼容平台。
- 文档（README/实验指南/实验手册/AGENTS.md）与代码同步，给出可复制的读图实验命令。

**Non-Goals:**

- 不实现独立视觉模型的 `analyze_image` 工具（主模型多模态方案已覆盖；独立 VL 工具作为可能的后续演进记录于实验指南思考题）。
- 不改 deepagents 包、不给 `read_file` 打补丁。
- 不改 `skills/xlsx/`（官方仓库完整保留约定）。
- 不动其他 demo 的默认模型/端点。

## Decisions

1. **默认模型用字面量 `qwen3.8-max` 而非 `MODEL` 环境变量**：本机 `.env` 的 `MODEL=qwen3.6-27b`（其他通用 demo 在用），若继续读它会静默降级为较弱模型且无提示；读图是本 demo 的核心新能力，默认值必须明确。`--model` 参数仍可覆盖。
2. **默认 `--base_url` 读 `DASHSCOPE_BASE_URL`（兜底公共 dashscope 端点），默认 `--api_key` 优先 `DASHSCOPE_API_KEY` 再退 `API_KEY`**：本机 `.env` 已配企业专属端点，直接可用；公共端点兜底保证其他环境开箱即用；硅基流动用户显式传 `--base_url/--api_key` 切换（README 写明）。
3. **`enable_thinking=False` 经 `model_kwargs={"extra_body": {...}}` 传入**：langchain-openai 会把 `extra_body` 透传给 OpenAI SDK 再并入请求体。实测百炼端点接受；若其他平台报"不认识参数"，用户需 `--model` 切换时自行注意（README 注意事项标注），不为兼容所有平台做运行时探测——教学 demo 保持代码可读优先。
4. **SYSTEM_PROMPT 只加一条读图指引**：告诉模型图片可 `read_file` 直接获取图像内容、适合图表识别类任务。不重写整个提示词，改动最小化。
5. **实验素材取 2 张现有年报图表**（信息图 + 数据图表各一，从 `wiki_kb_agent_demo/knowledge_base/ICBC_2024_年报/assets/` 拷贝至 `data/`）：与后续 runtime-skill-install change 的 annual-report-to-kb 演示形成连续故事线，且不引入新外部文件。

## Risks / Trade-offs

- **默认平台变更**（硅基流动 → 百炼）：老用户若依赖旧默认，需显式传参切回；README/实验指南显著标注。属可接受的教学取舍——读图能力价值大于平台默认的稳定性。
- **多模态 token 成本**：每张图按 32×32 像素/token 估算消耗上下文；实验指南提醒大图/多图任务的成本，`recursion_limit=80` 不变。
- **非多模态模型 + 读图任务 = 静默失效**：`_scrub_unsupported_multimodal_content` 只在 model profile 声明不支持时替换为占位文本，纯文本模型收到 image block 可能报 4xx 或忽略；文档明确"读图任务必须多模态模型"。
- **qwen3.8-max 无 system prompt 时 function calling 不稳**（实测出现幻觉示例调用/重复调用）：deepagents 恒注入系统提示词，风险不触发；记录于此供后续调试参考。
