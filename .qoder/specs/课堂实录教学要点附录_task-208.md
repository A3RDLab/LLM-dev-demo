# 新增《课堂实录与教学要点》附录文档

## 目标与范围

- 新建 `课堂实录与教学要点.md`（仓库根目录），承载录音转写中的讲解与案例；**实验手册.md 本次保持原样不动**（用户要求先复盘再评估回填）。
- 所有写入内容已完成转写纠错甄别，并与代码实机核对（见下），不照抄转写原文。
- `README.md` 新手引导区补一行指向新文档。

## 已核对的事实基线（写入文档的依据）

- 实验 4 默认任务确为分析 `ai-shifu/ChatALL` 如何接入 OpenAI（[demo-agent-with-tools-arg.py](file:///Users/limingyu/Code/LI-Mingyu/LLM-dev-demo/function_call_and_agent_demo/demo-agent-with-tools-arg.py)），课堂结论"官方 API + OAuth 两种方式"。
- [first_llm_call.py](file:///Users/limingyu/Code/LI-Mingyu/LLM-dev-demo/first_llm_call.py) 系统提示词确为"你在回答博士生的提问。"，默认端点 DashScope。
- [text2sql_demo.py](file:///Users/limingyu/Code/LI-Mingyu/LLM-dev-demo/text2sql_demo.py) 默认问题与课堂一致；Chinook 为音乐商店示例库。
- MCP server 三工具：`get_weather` / `get_current_time` / `lottery`；LangGraph 工具为 `get_weather` + `celsius_to_fahrenheit`，系统提示词"你是一个助手，可以使用工具回答问题，请用中文回答。"。
- `first_llm_app.py` 确用 `temperature=0.7`。

## 新文档结构（课堂实录与教学要点.md）

1. **说明**：来源（2026-08-08 通号培训录音转写）、与实验手册 0~11 的对应关系、"转写有识别错误，已甄别，对照表见文末"。
2. **通用学习法**（课堂开场要点）：AI 辅助下命令不必死记；IDE 的 ask/agent/plan 模式区别；把 `.env` 内容粘贴给 AI 说"帮我配好实验环境"；实验用模型不需要很强（全部示例在 Qwen 27B/35B 级中档模型上跑通）；看不懂代码就让 AI 讲解。
3. **实验 0~11 逐节教学要点**，每节含"讲解要点 / 课堂案例 / 现场实录"三类内容（无则缺省）：
   - 实验 0：OpenAI 兼容 API 已成事实标准（模型厂商与智能体产品普遍支持）；`git clone` 起步。
   - 实验 1：chat completion 第一性原理（LLM 唯一功能 = token 进 token 出）；三角色；**通信"网格"案例**（地下通信管线网格被误读为网格计算，系统提示词补充业务语境后秒懂）；"博士生提问"提示词改变回答风格的实测对照；temperature 一句话带过。
   - 实验 2：**黑猫起名案例**（模型记住"程序员"身份，答"黑猫在程序员圈特别受欢迎，和终端背景色契合"）；多轮对话本质 = 不断 append messages；流式 + 灰色思考/默认色回答。
   - 实验 3：结构化输出的动机（对接数据库字段、省 token）；JSON Schema 即输出契约；Pydantic `model_json_schema()` 自动生成。
   - 实验 4：Function Calling 第一性原理（模型输出一段"调用表达"，另一段代码代为执行）；ERP 接口类比；ChatALL 案例全过程（get_repo_tree 侦察 → 多轮读文件 → 结论 API + OAuth）；tools 格式由 OpenAI 定义、各家对齐训练成事实标准；**DeepSeek-R1 案例**：官方未支持工具调用，云服务商在接口后注入 few-shot 提示使其可用——本质都是提示词。
   - 实验 5：LangGraph ≈ 代码版 Coze/Dify 工作流；模型节点与工具节点分离、轨迹清晰；`@tool` 一行装饰器 = 标准格式封装；**教学主张：公式计算/行业小模型/规则判断封装成工具，不提倡让 LLM 深度思考硬算**（准确率、速度、token 三重代价）；课堂轨迹：北京上海天气比较 → 触发摄氏度转华氏度，两次工具调用。
   - 实验 6：**20 个智能体 × 20 个系统 = 400 段对接代码**的动机算术；MCP 不是省掉对接代码，而是把它挪到 server 只写一遍、随外部系统同步演进；工具一句话描述先加载，也有渐进式披露意味；**现场翻车实录**：mcp SDK 版本不同导致参数名不兼容，做兼容处理后恢复——依赖版本要钉住（对手册中 `mcp[cli]<2` 的印证）；传输层为 Streamable HTTP。
   - 实验 7：**ECS 现场案例**——只敲"ECS"触发拒答，改问"ECS 无法连接怎么查"才命中；两点教训：跟 AI 说话要说清楚、RAG 是天然的幻觉抑制手段。
   - 实验 8：**工行海外布局案例**——index.md → 24/25 年报各自 index → 国际化经营页，逐级下钻导航，最后对比两年变化。
   - 实验 9：课堂追问**探索性数据分析（EDA）**：AI 自行脑爆分析视角（最大播放列表、收入高低点、热门艺术家、客户分布）并写代码验证——AI 让 EDA 从"费脑子试错"变成一句话。
   - 实验 10：动机链（SQL 不够复杂分析、真实业务数据大量在 Excel、业务系统几乎都能导出 Excel、跨系统拉通分析、互联网/快消个性化运营普遍依赖 Excel）；现场故意换题"销量 Top5 vs 销售额 Top5 对比"避免背题嫌疑；**Docker 报错即教学点**：AI 生成的代码必须在沙箱隔离环境运行；分析结论（销量高 = 低价高性价比，销售额高 = 高价旗舰；量大价低换市场份额而非利润）；读码指引：核心仍是 agent 循环，多出的代码大多是 Streamlit 界面，不必纠结。
   - 实验 11：Agent 演进总结线（基础调用 → 多轮 → 结构化输出 → function calling → 框架/MCP/数据分析 → Skill）；DeepAgents `create_deep_agents` + skills 参数；借用 Claude Code 官方 xlsx skill 获得专业能力。
4. **专题 A：AI 辅助编码的纪律**：现场反例（未询问就在 agent 模式让 AI 直接改代码，事后需 undo 回退）；正确姿势：先 ask 模式问 → plan 模式写清"为什么改、怎么改"→ plan 文件与代码一起 commit。
5. **专题 B：Skill 沉淀方法论**：PDF → 知识库 → Skill 的对话式开发全流程；开发习惯"先让 AI 干活：一把干对就不管，干错就指出差异，再让它自己把差异沉淀成 Skill（让它自己想，AI 可能比你懂得多）"；图片处理案例（奖项图需结构化描述：什么奖、第几名、谁颁发）；Skill 要补贴近自己业务的例子（如把股东会例子换成铁路信号流程图）；收尾范式：知识库/Skill 对话式开发 → coding agent 验证 → 导入自己的代码 agent 直接跑。
6. **附录：转写纠错对照表**：方根 call/方生 call/方审→Function Call；扣子 define→Coze/Dify；circle→SQL；Streamlet→Streamlit；mcb→MCP；pandantic/pandas（指 Pydantic 处）→Pydantic；R one/RY/阿万→DeepSeek-R1，V→DeepSeek-V3；future 提示→few-shot 提示；GRPU→GRPO；cloud code/clawcode→Claude Code；honey/hannes→Harness；千万 B/千万 3,6,27→Qwen3.6-27B 等 Qwen 中档模型；chatall→ChatALL（ai-shifu/ChatALL）；walker body/cute/openclaw 等无法确指的产品名一律不写入正文，用泛指。
7. **附录：待评估回填实验手册的候选清单**（服务用户"复盘后再评估"）：列出各实验中值得回填手册正文的要点（精简版），并附一条本次发现的文档与代码不一致项——实验手册 0.3 称"根目录脚本没有内置 load_dotenv()"，实际全部脚本均已内置 `load_dotenv()`（已核实），供复盘时决定是否修正手册。

## README 更新

- 在 `README.md` 开头新手引导引用（第 5 行附近）追加一行：课堂实录与教学要点见 `课堂实录与教学要点.md`。

## 验证方式

- 通读新文档，确认所有引用的文件路径、命令、工具名与代码一致；
- 确认实验手册.md 零改动；
- 确认纠错表未把存疑产品名当事实写入。

## 假设

- 新文档为中文、纯教学材料，不涉及代码与依赖变更；
- "千问 3,8 Max"等无法确指的助手模型版本号不写入文档，仅表述为"Qwen Max 级编码助手"或不提。