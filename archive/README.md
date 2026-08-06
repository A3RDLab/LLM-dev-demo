# 归档目录（仓库根级）

本目录存放**暂不纳入教学主线**的历史内容与素材，仅作保留参考，不建议照抄或直接运行。

| 条目 | 归档原因 |
|---|---|
| `finance_doc_review/` | Pydantic AI + YAML 规则引擎 + LangGraph 的金融文档审阅完整项目。曾短暂提交进主线后移出；如需参考"现代范式"实现可阅读其 README 与源码（依赖用 uv 管理，见 `pyproject.toml`） |
| `vanna_demo.ipynb` | Vanna（训练式 Text2SQL）探索 notebook，未纳入实验手册主线 |
| `pdf_rag_demo_corpus/` | PDF_RAG_demo 的补充语料 PDF（电力行业报告、ESG 手册、故障指南）与一版更新过的 ICBC 年报，体积较大不进主线；`PDF_RAG_demo/` 目录内的原始 ICBC 年报仍为现役语料 |
| `first_langchain_app.py` | 实验 2 流式对话的 LangChain 版本，不在实验手册路线上（主线用 `first_llm_app.py`），移出主线保留参考 |
| `code_fim.py` | 代码补全（FIM）探索脚本：直读 `SILICONFLOW_API_KEY`、硬编码模型、无 CLI 参数，不符合仓库 `.env`/多平台约定，且不在实验手册路线上 |
| `demo-agent-with-aliyun-2phases.py` | 两阶段（R1 规划 + V3 执行）GitHub agent 探索：全仓库零引用，硬性要求 GITHUB_TOKEN 无匿名降级，无 load_dotenv，已被 `demo-agent-with-tools-arg.py` 路线替代 |
| `AI_Coding_demo/` | 早期 AI Coding 演示素材（销售数据表格分析等） |
| `deepseek_v3_tokenizer/` | DeepSeek V3 tokenizer 演示脚本与词表文件 |
| `first_llm_app.py.bak` | 历史备份文件 |

> 注：`function_call_and_agent_demo/archive/` 是该子目录自己的归档区（agent 教学线的过时写法），与本目录分工独立。
