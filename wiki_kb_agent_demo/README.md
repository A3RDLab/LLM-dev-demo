# LLM Wiki 导航 Agent Demo

把一个 **LLM wiki 风格的知识库**（以 `index.md` 为入口、页面间用 Markdown 链接互相引用的
一堆 Markdown 页面）接入智能体。

## 为什么不用 embedding？

LLM wiki 本身就是为"LLM 自主阅读"设计的：入口目录页 + 页面间链接构成导航结构。
正确的消费范式是让 Agent **像人翻 wiki 一样迭代查询**，而不是切块做向量检索：

| | Wiki 导航式（本 demo） | Embedding 检索式（传统 RAG） |
|---|---|---|
| 预处理 | **零**，copy 进来即用，永远最新 | 要建索引，换模型要重建 |
| 链接/目录结构 | ✅ 完整利用，顺着链接迭代深入 | ❌ 切块后结构丢失 |
| 可解释性 | 模型的探索路径全程可见 | 相似度黑盒 |
| 代价 | 多几轮工具调用（token/延迟略高） | 检索更快 |
| 适用 | 中小规模、结构良好的 wiki | 海量文档、目录不可信 |

> 知识库规模特别大时，才需要引入向量检索作为补充工具（工具层加一个 `search_wiki` 即可，其余不变）。

## 工作原理

```
你的 Wiki（index.md 入口 + 链接互引的 .md 页面）
      │  零预处理
      ▼
kb_agent.py（function calling 循环）
  LLM ──tool_calls──► read_page('index.md')   读目录页，理解结构
   ▲                  read_page(path)          顺链接迭代深入
   │                  list_pages(subdir)       目录之外浏览结构（兜底）
   │                  grep_kb(pattern)         全文关键词定位（兜底）
   └────tool 结果回填──┘
```

关键设计：
- **系统提示约定导航流程**：先读 `index.md` → 按问题选页面 → 顺链接深入 → 兜底 grep；
- **三个工具分工**：`read_page` 是主力（导航），`list_pages`/`grep_kb` 是目录失灵时的兜底；
- **零依赖、零索引**：直接读原始文件，知识库更新无需任何操作；
- 安全：`read_page` 解析真实路径并限制在知识库目录内，防路径穿越。

## 使用步骤

### 0. 放入你的知识库

把你的 LLM wiki 文件夹整体 copy 到 `knowledge_base/`（先删掉示例的 4 个 `.md`），
支持任意嵌套子目录。约定：入口目录页叫 `index.md`（没有的话模型会改用 `list_pages` 探索）。

### 1. 准备环境

依赖复用仓库根目录的 `requirements.txt`（openai / python-dotenv 已包含，**不再需要 numpy**）。

```bash
# 在仓库根目录配置 Key
cp .env.example .env   # 填入 API_KEY（对话用，如硅基流动）
```

### 2. 启动 Agent 对话

```bash
python kb_agent.py                            # 交互式
python kb_agent.py --once "什么是 RAG？"      # 单轮提问
# 可选参数：--model / --base-url 切换对话模型（默认硅基流动 DeepSeek-V3）
```

终端会实时打印模型每次调用的工具，可以完整看到它的"翻 wiki"路径。

## 常见问题

| 问题 | 处理 |
|---|---|
| 我的 wiki 入口页不叫 index.md | 改 `kb_agent.py` 里的 `ENTRY_PAGE` 常量即可 |
| 探索轮数不够 / 太多 | 调整 `MAX_TOOL_ROUNDS`（默认 10） |
| 知识库很大、导航太慢 | 加一个 embedding 版的 `search_wiki` 工具作为补充（可参考 `AliyunQA_RAG_demo/` 的召回实现） |
