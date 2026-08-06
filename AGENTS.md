# AGENTS.md

This file provides guidance to Qoder (qoder.com) when working with code in this repository.

## 仓库性质

这是一个 **LLM 应用开发教学实验合集**，不是单一应用：每个 demo 是自包含脚本，按学习路线递进（基础调用 → 结构化输出 → Function Calling → LangGraph → Agent Harness → MCP → RAG → Text2SQL → 完整项目）。根目录 [实验手册.md](实验手册.md) 是面向学员的引导式手册，其中的命令均经实机验证——**修改 demo 的用法、参数或依赖后，必须同步更新实验手册与相关 README**，保持文档与代码一致。

## 环境与密钥约定

- 密钥一律走仓库根目录 `.env`（模板见 `.env.example`），**切勿硬编码 API Key**。关键变量：`API_KEY` / `API_BASE`（OpenAI 兼容端点）/ `MODEL` / `EMBED_MODEL` / `DASHSCOPE_API_KEY`。
- 所有脚本在启动时用 `load_dotenv()` 按相对路径显式加载根目录 `.env`（子目录脚本用 `Path(__file__).resolve().parent.parent / ".env"` 这类写法定位），新增脚本应保持此约定。
- 所有 demo 支持 `--model` / `--api_key` / `--base_url` 命令行参数覆盖默认值（默认平台为硅基流动）。切换平台示例：`--base_url https://dashscope.aliyuncs.com/compatible-mode/v1 --api_key $DASHSCOPE_API_KEY`。
- 企业专属实例的 Key 常有模型白名单，跑 demo 前先用 `curl $API_BASE/models` 探测可用模型。

## 依赖管理

根目录 `requirements.txt` 管理公共依赖；**子项目独立依赖不得混入根 requirements**，各自维护：

| 子项目 | 依赖位置 | 安装/运行 |
|---|---|---|
| `function_call_and_agent_demo/excel-process/` | 自己的 `requirements.txt` | `streamlit run app.py`（需本机有 Docker，llm-sandbox 基于容器） |
| `function_call_and_agent_demo/agent_harness_demo/` | 自己的 `requirements.txt`（deepagents） | `python agent_harness_demo.py` |
| `finance_doc_review/` | `pyproject.toml`（uv） | `uv venv .venv --python 3.12 && uv pip install -p .venv/bin/python -e .`，然后 `finance-doc-review samples/xxx.txt [--json]` |

版本约束用 `>=` 宽松策略，但 `mcp[cli]` 必须锁 `<2`：2.0 移除了 `mcp.server.fastmcp` 高层封装，MCP demo 依赖 1.x。

## 常用命令

```bash
# 根目录脚本（示例）
python first_llm_app.py
python structured_output_demo.py
python mini_rag_demo.py --query "..." --top_k 3     # --rebuild 强制重建向量索引
python text2sql_demo.py                              # 依赖根目录 Chinook.sqlite
python wiki_kb_agent_demo/kb_agent.py --once "问题"

# Function Calling / Agent
python function_call_and_agent_demo/demo-agent-with-tools-arg.py
python function_call_and_agent_demo/langgraph_demo/langgraph_agent_scaffold.py --query "..."
python function_call_and_agent_demo/mcp_server_demo.py     # MCP 服务端
python function_call_and_agent_demo/mcp_client_agent_demo.py  # MCP 客户端 agent

# Streamlit 应用
streamlit run AliyunQA_RAG_demo/chat.py              # 需本地 Redis 向量库
streamlit run function_call_and_agent_demo/excel-process/app.py
```

无统一测试框架/lint 配置。仅有的回归验证脚本：`excel-process/verify_sandbox_sharing.py`（修改沙箱相关代码后先跑它）和 `excel-process/test_*.py`（独立验证脚本）。`finance_doc_review` 的正确性靠三个样例文件断言：`loan_contract_ok.txt`→PASS、`loan_contract_bad.txt`→REJECT（fail-fast 短路）、`loan_ad_gray.txt`→REVIEW_REQUIRED；CLI 退出码 `0`=PASS。

## 架构要点（跨文件才能理解的大图景）

**Agent 教学线的递进关系**（勿打乱顺序或合并）：`demo-agent-with-tools-arg.py`（原生 function calling + 手写调用循环）→ `langgraph_demo/`（手搓 StateGraph vs `create_react_agent` 对比）→ `agent_harness_demo/`（DeepAgents 框架化 harness + Skills 渐进式披露）→ MCP demo。每一层刻意展示不同的抽象层级。

**过时写法统一归档而非删除**：各目录的 `archive/`（如手写 ReAct prompt 正则解析）附 README 说明归档原因与替代方案。不要"顺手清理"或恢复其中的写法。

**`finance_doc_review/` 是刻意为之的"现代范式"对照项目**：Pydantic v2 数据契约 + YAML 声明式规则引擎（`rules/credit_rules.yaml`）+ Pydantic AI 结构化抽取 + LangGraph 编排。分工原则是"规则引擎管确定性判断、LLM 只管语义抽取与发现"，critical 违规 fail-fast 短路跳过 LLM。它刻意避开本仓库旧代码的手写 messages 循环/JSON 字符串解析写法——扩展它时应延续这些范式。

**`agent_harness_demo/skills/xlsx/` 来自 anthropics/skills 官方仓库，完整未裁剪**：不要精简或改动它；`scripts/recalc.py` 的公式重算依赖 LibreOffice（`soffice` 在 PATH），脚本内部 `from office.soffice import ...` 要求以 `skills/xlsx/scripts/` 为工作目录调用。`execute_python` 工具无隔离地真实执行模型生成的代码，仅用于本地教学。

**`wiki_kb_agent_demo/` 的零 embedding 是设计决策而非遗漏**：wiki 式知识库（`index.md` 入口 + 链接互引）优先用导航式检索（`read_page`/`list_pages`/`grep_kb` 工具循环），不做切块向量化；仅当规模极大时才补 `search_wiki` 工具。入口页名由 `kb_agent.py` 的 `ENTRY_PAGE` 常量控制。

**`mini_rag_demo.py` 的索引缓存**：embedding 调用云端模型计费，索引缓存到根目录 `rag_index.npz` + `rag_index_meta.json`，语料未变不重建；换 embedding 模型或改语料需 `--rebuild`。

**`excel-process/` 的沙箱机制**（llm-sandbox/Docker）：跨会话共享文件需 `copy_to_runtime` 传完整文件路径 + `keep_template=True, commit_container=True`；每次上传会 commit 镜像，可定期 `docker image prune`。

## API 规范（如新增接口）

API 响应体必须是标准 JSON；错误响应必须包含顶层 `code`（数字错误码）与 `message`（错误描述）两个字段。
