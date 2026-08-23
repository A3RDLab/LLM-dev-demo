# Spec: agent-harness-vision

## Purpose

agent_harness_demo 的多模态读图能力：主模型为多模态模型（默认百炼 `qwen3.8-max`）时，内置 `read_file` 读取图片返回图像内容（base64 content block），agent 能直接"看图"并按任务要求产出描述或结构化结果，无需额外工具。

## Requirements

### Requirement: 多模态主模型默认配置

`agent_harness_demo.py` 的默认模型 SHALL 为 `qwen3.8-max`，默认端点 SHALL 取 `DASHSCOPE_BASE_URL` 环境变量（缺失时兜底 `https://dashscope.aliyuncs.com/compatible-mode/v1`），默认 Key SHALL 优先取 `DASHSCOPE_API_KEY`（缺失时退回 `API_KEY`）；`--model/--base_url/--api_key` 命令行参数 SHALL 保持可覆盖。

#### Scenario: 无参数启动即用百炼多模态模型

- **WHEN** 用户在已配置 `DASHSCOPE_API_KEY`（及可选 `DASHSCOPE_BASE_URL`）的环境下直接运行 `python agent_harness_demo.py`
- **THEN** agent 使用 `qwen3.8-max` 与百炼 OpenAI 兼容端点运行，无需任何命令行参数

#### Scenario: 显式切回其他平台

- **WHEN** 用户运行时传入 `--model <纯文本模型> --base_url <其他兼容端点> --api_key <key>`
- **THEN** agent 按传入参数运行（读图能力依赖多模态模型，文档已声明该限制）

### Requirement: 关闭思考模式

构建 `ChatOpenAI` 时 SHALL 通过 `extra_body` 传入 `enable_thinking: False`，以适配 qwen3.5–3.8 系列默认开启思考的行为，保证 agent 工具循环的响应速度与输出整洁。

#### Scenario: 思考模式关闭生效

- **WHEN** agent 向 `qwen3.8-max` 发起请求
- **THEN** 请求体携带 `enable_thinking=False`，模型不返回思考过程（实测端点接受该参数）

### Requirement: read_file 图像读取可用

主模型为多模态模型时，agent SHALL 能通过内置 `read_file` 工具读取 backend 根目录内的图片文件（`.jpg/.png/.webp` 等）并"看到"图像内容（deepagents 以 base64 image content block 返回，不经过任何转写文本的中间层）。

#### Scenario: 读取并描述年报图表

- **WHEN** 任务要求 agent 描述 `data/` 下某张年报图表 jpeg 的内容，agent 调用 `read_file` 读取该图片
- **THEN** 模型基于图像内容输出描述（含图中关键数字的识别），而非报错或只返回文件元信息

#### Scenario: 图表识别产出结构化结果

- **WHEN** 任务要求按给定规范（如数据图→JSON、组织图→mermaid）结构化图中信息
- **THEN** agent 能将 `read_file` 看到的图表转写为符合规范的结构化文本并写入产物文件

### Requirement: 默认任务无回归

本能力 SHALL NOT 改变 `DEFAULT_TASK`（销售数据分析）的行为路径：xlsx skill 渐进式披露、`execute_python` 分析、`output/report.xlsx` 公式重算校验流程保持原样。

#### Scenario: 原默认任务照常完成

- **WHEN** 用户无参数运行默认销售分析任务
- **THEN** 产出 `report.md` 与 `output/report.xlsx`，且经过 `scripts/recalc.py` 公式重算校验

### Requirement: 实验素材就位

`agent_harness_demo/data/` SHALL 包含至少一张来自工行年报的图表图片，供读图实验直接使用（不要求用户自备素材）。

#### Scenario: 读图实验开箱可跑

- **WHEN** 用户按实验指南运行读图示例命令
- **THEN** 命令引用的图片文件存在于 `data/` 目录
