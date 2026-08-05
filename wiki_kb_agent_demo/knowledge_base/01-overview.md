# LLM 应用开发概览

LLM 应用开发通常包含四个层次的能力：基础调用、结构化输出、Agent、RAG。

## 基础调用

最基础的用法是通过 OpenAI 兼容协议调用大模型，传入 `messages` 列表获得回复。
多轮对话的关键是把历史消息维护在 `messages` 中，每次请求都带上完整上下文。
流式输出（stream=True）可以逐 token 返回，改善长回复的交互体验。

## 结构化输出

让模型按 JSON Schema 输出结构化数据，配合 Pydantic 做校验，
适用于信息抽取、表单生成、函数参数构造等场景。
相比让模型"自由发挥再解析"，用 `response_format` 约束更可靠。

## Agent

Agent = LLM + 工具 + 调用循环。模型通过 function calling 决定调用哪个工具、
传什么参数，程序执行工具后把结果回填给模型，循环往复直到模型给出最终答案。
详见 [Agent 与 Function Calling](03-agent.md)。

## RAG

RAG（检索增强生成）在提问时先从外部知识库检索相关内容，拼入 prompt 再让模型作答，
用于解决模型知识过期和私域知识问答问题。详见 [RAG 检索增强生成](02-rag.md)。
