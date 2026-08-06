# LLM 应用开发教程实验合集

大模型应用开发的系列示例，覆盖从基础调用到 Agent 编排的完整学习路线。

> 📖 **新手请从[实验手册.md](实验手册.md)开始**——一步步引导式实验，全部命令经过实机验证。

## 环境准备

```bash
pip install -r requirements.txt

# 配置 API Key（复制模板并填入自己的 Key，.env 不会被提交）
cp .env.example .env
# 或直接 export：
export API_KEY=<硅基流动等 OpenAI 兼容平台的 Key>
export DASHSCOPE_API_KEY=<阿里云百炼 Key>
```

所有脚本支持 `--model` / `--api_key` / `--base_url` 参数切换模型与平台（默认硅基流动）。

## Demo 索引

### 基础调用
| Demo | 说明 |
|---|---|
| `first_llm_call.py` | 最简单的单次调用 |
| `first_llm_app.py` | 流式多轮对话，含推理模型思考过程展示 |
| `structured_output_demo.py` | **结构化输出**：json_schema 约束 + Pydantic 校验，信息抽取场景 |

### Agent / Function Calling（推荐学习顺序）
| Demo | 说明 |
|---|---|
| `function_call_and_agent_demo/demo-agent-with-tools-arg.py` | 入门：原生 function calling + 手写调用循环（GitHub 仓库分析场景） |
| `function_call_and_agent_demo/langgraph_demo/` | 进阶：LangGraph 图编排，手搓 StateGraph vs `create_react_agent` 对比 |
| `function_call_and_agent_demo/agent_harness_demo/` | 进阶：Agent Harness（DeepAgents）+ Agent Skills 渐进式披露，接入 anthropics/skills 现成 Skill |
| `function_call_and_agent_demo/mcp_server_demo.py` + `mcp_client_agent_demo.py` | MCP 协议：FastMCP 服务端 + Streamable HTTP 客户端 agent |
| `function_call_and_agent_demo/excel-process/` | Streamlit + 代码沙箱的 Excel 处理应用（独立依赖，见其 requirements.txt） |
| `function_call_and_agent_demo/archive/` | 已归档的历史写法（手写 ReAct prompt 等），附归档原因说明 |

### RAG
| Demo | 说明 |
|---|---|
| `mini_rag_demo.py` | **自包含 RAG 全链路**：HTML清洗→切块→embedding→余弦检索→生成（索引缓存，无需 Redis） |
| `AliyunQA_RAG_demo/` | 阿里云运维问答：Scrapy 采集 + Redis 向量库 + **向量召回 + rerank 精排**（Streamlit 界面） |
| `PDF_RAG_demo/` | PDF 文档 RAG（notebook，含表格/图片处理） |
| `wiki_kb_agent_demo/` | LLM Wiki 知识库接入 Agent：从 index.md 出发的自然语言导航式检索（read_page/list_pages/grep_kb 工具，零 embedding） |

### Text2SQL
| Demo | 说明 |
|---|---|
| `text2sql_demo.py` | schema 自动内省 + function calling 执行 SQL + 错误自修复（Chinook 示例库） |
| `vanna_demo.ipynb` | Vanna 框架 Text2SQL（对比路线） |

### 生产风格完整项目
| Demo | 说明 |
|---|---|
| `finance_doc_review/` | 金融文档审核：LangGraph 编排 + YAML 规则引擎 + Pydantic AI 结构化输出（独立 pyproject，见其 README） |

## 推荐学习路线

1. **基础**：`first_llm_call.py` → `first_llm_app.py` → `structured_output_demo.py`
2. **Agent**：`demo-agent-with-tools-arg.py` → `langgraph_demo` → `agent_harness_demo`（Agent Harness + Skills）→ MCP demo
3. **RAG**：`mini_rag_demo.py`（无依赖全链路）→ `AliyunQA_RAG_demo`（召回+重排）→ `PDF_RAG_demo`
4. **数据**：`text2sql_demo.py` → `excel-process`
5. **综合**：`finance_doc_review/`

## 注意事项

- **切勿在代码中硬编码 API Key**，一律使用环境变量（见 `.env.example`）
- 过时写法统一移入各目录的 `archive/`，其中的 README 说明了归档原因与替代方案
- 人工智能生成内容仅供参考
