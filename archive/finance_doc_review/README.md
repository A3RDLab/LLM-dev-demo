# 金融资料审核演示：规则引擎 + LLM

一个面向信贷资料审核的演示项目，展示 **"确定性规则引擎 + LLM 语义审核"** 的混合审核架构。
刻意避开本仓库旧代码中的实现方式（手写 messages 循环、JSON 字符串解析、Streamlit 单体应用），
全部采用当前主流范式：

| 层 | 技术 | 职责 |
|---|---|---|
| 数据契约 | Pydantic v2 | 所有输入输出强类型，schema 即文档 |
| 规则引擎 | 声明式 YAML + 纯 Python 求值器 | 硬性合规校验，零 LLM 成本、结论可解释可复现 |
| LLM Agent | Pydantic AI（结构化输出） | 只做信息抽取与语义发现，不下合规结论 |
| 流程编排 | LangGraph | 状态图驱动，fail-fast 短路，全链路可审计 |
| CLI | rich | 终端富文本报告 / `--json` 机器可读输出 |

## 架构

```
                 ┌──────────── extract (LLM 结构化抽取)
  资料文本 ──→ │                 │
                 │          rule_check (规则引擎, YAML 驱动)
                 │                 │
                 │     critical 违规? ──是──→ aggregate ──→ 审核报告(REJECT)
                 │                 │否                    （跳过 LLM，省成本）
                 └───────── semantic_review (LLM 语义审核)
                                   │
                              aggregate ──→ 审核报告(PASS / REVIEW_REQUIRED)
```

分工原则：

1. **规则引擎负责"能不能"**：利率上限、要件完整性、证件格式、还款计划勾稽……
   全部是确定性判断，写在 `rules/credit_rules.yaml`，合规人员可直接维护；
2. **LLM 负责"像不像"**：风险披露是否流于形式、条款是否含糊、宣传是否违规、
   文档内部是否自相矛盾——这类规则难以枚举的语义问题；
3. **fail-fast**：硬性违规直接否决，不再调用语义审核，控制 LLM 成本；
4. **LLM 抽取 → 规则校验** 的组合让"数值合规性"不依赖模型判断，杜绝幻觉误判。

## 目录结构

```
finance_doc_review/
├── rules/credit_rules.yaml          # 声明式规则集（required/threshold/regex/enum/sum_equals）
├── samples/
│   ├── loan_contract_ok.txt         # 合规合同     → 预期 PASS
│   ├── loan_contract_bad.txt        # 年化 18% 高利 → 预期 REJECT（fail-fast 短路）
│   └── loan_ad_gray.txt             # 绝对化宣传   → 预期 REVIEW_REQUIRED（语义发现）
├── src/finance_doc_review/
│   ├── schemas.py                   # Pydantic 数据契约
│   ├── rules_engine.py              # 规则引擎
│   ├── agents.py                    # 两个 Pydantic AI Agent
│   ├── graph.py                     # LangGraph 工作流
│   └── cli.py                       # 命令行入口
└── pyproject.toml
```

## 快速开始

```bash
cd finance_doc_review
uv venv .venv --python 3.12
uv pip install -p .venv/bin/python -e .
source .venv/bin/activate

cp .env.example .env   # 填入 OPENAI_API_KEY / OPENAI_API_BASE / REVIEW_MODEL

# 审核单个文件（rich 表格报告）
finance-doc-review samples/loan_contract_bad.txt

# 或 JSON 报告，便于接入下游系统
finance-doc-review samples/loan_ad_gray.txt --json
```

退出码：`0`=PASS，`1`=其他（REVIEW_REQUIRED / REJECT / ERROR），方便嵌入 CI 或批处理脚本。

## 规则集扩展

在 `rules/credit_rules.yaml` 追加即可，无需改代码。支持的规则类型：

- `required`：字段非空检查（`fields` 列表）
- `threshold`：数值比较（`op` + `value`，或 `ref_field` × `ref_multiplier` 相对阈值）
- `regex`：正则格式校验
- `enum`：取值白名单
- `sum_equals`：列表字段子项求和勾稽（如还款计划占比合计 100%）

每条规则携带 `severity`：`critical`（否决）、`warning`（转人工）、`info`（提示）。

## 演进方向

- 抽取层接入 PDF/扫描件（OCR 或视觉模型）后复用同一规则引擎；
- 语义审核改为多专家并行节点（宣传合规员 / 风险披露员），`langgraph` 的 fan-out/fan-in 天然支持；
- 规则命中统计回流，驱动 LPR 等参数自动更新；
- 报告落库 + 人工复核标注，形成评测集持续回归测试 prompt。
