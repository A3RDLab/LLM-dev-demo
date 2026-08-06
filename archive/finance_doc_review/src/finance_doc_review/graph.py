"""LangGraph 审核工作流编排。

流程（含 fail-fast 短路）：

    ┌─ ingest ─→ extract(LLM抽取) ─→ rule_check(规则引擎)
    │                                    │
    │              存在 critical 违规 ───┴─── 无 critical 违规
    │                    │                     │
    │                    ↓                     ↓
    │               aggregate ←── semantic_review(LLM语义审核)
    └────────────────────┘

设计要点：
- 硬性违规（critical 规则失败）时直接出报告，跳过语义审核，节省 LLM 调用成本；
- LLM 只负责"抽取"和"语义发现"两类工作，合规结论始终由确定性规则给出；
- 全图状态即审计日志，每个节点的输入输出都可回放。
"""

from __future__ import annotations

from pathlib import Path
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from .agents import get_extraction_agent, get_semantic_agent
from .rules_engine import DEFAULT_RULES_PATH, evaluate, load_rules
from .schemas import (
    Decision,
    LoanDocument,
    ReviewReport,
    RuleFinding,
    SemanticFinding,
    Severity,
)


class ReviewState(TypedDict, total=False):
    source_file: str
    document_text: str
    extracted: LoanDocument | None
    rule_findings: list[RuleFinding]
    semantic_findings: list[SemanticFinding]
    decision: Decision
    summary: str


def _node_extract(state: ReviewState) -> dict:
    agent = get_extraction_agent()
    result = agent.run_sync(state["document_text"])
    return {"extracted": result.output}


def _node_rule_check(state: ReviewState) -> dict:
    rules = load_rules(DEFAULT_RULES_PATH)
    findings = evaluate(state["extracted"], rules)
    return {"rule_findings": findings}


def _has_critical_violation(state: ReviewState) -> str:
    """存在 critical 级规则违规则短路，直接汇总，跳过语义审核。"""
    if any(
        not f.passed and f.severity is Severity.CRITICAL for f in state["rule_findings"]
    ):
        return "aggregate"
    return "semantic_review"


def _node_semantic_review(state: ReviewState) -> dict:
    agent = get_semantic_agent()
    # 把规则引擎结论一并交给语义审核员，避免重复审查已确认的硬性指标
    rule_summary = "\n".join(
        f"- [{f.rule_id}] {'通过' if f.passed else '违规'} {f.rule_name}：{f.message}"
        for f in state["rule_findings"]
    )
    prompt = (
        f"## 规则引擎已完成的校验结论\n{rule_summary}\n\n"
        f"## 待审核资料原文\n{state['document_text']}"
    )
    result = agent.run_sync(prompt)
    return {"semantic_findings": result.output}


def _node_aggregate(state: ReviewState) -> dict:
    rule_findings = state.get("rule_findings", [])
    semantic_findings = state.get("semantic_findings", [])

    critical_rules = [f for f in rule_findings if not f.passed and f.severity is Severity.CRITICAL]
    warnings = [f for f in rule_findings if not f.passed and f.severity is Severity.WARNING]
    semantic_issues = [f for f in semantic_findings if f.severity in (Severity.CRITICAL, Severity.WARNING)]

    if critical_rules:
        decision, reason = Decision.REJECT, f"{len(critical_rules)} 项硬性违规"
    elif warnings or semantic_issues:
        decision, reason = Decision.REVIEW_REQUIRED, (
            f"{len(warnings)} 项规则预警、{len(semantic_issues)} 项语义风险待人工复核"
        )
    else:
        decision, reason = Decision.PASS, "规则校验全部通过，语义审核未发现风险"

    summary = (
        f"资料《{Path(state['source_file']).name}》审核结论：{decision.value}。"
        f"{reason}。共执行 {len(rule_findings)} 条规则，语义审核发现 {len(semantic_findings)} 条。"
    )
    return {"decision": decision, "summary": summary}


def build_graph():
    """构建并编译审核工作流图。"""
    graph = StateGraph(ReviewState)
    graph.add_node("extract", _node_extract)
    graph.add_node("rule_check", _node_rule_check)
    graph.add_node("semantic_review", _node_semantic_review)
    graph.add_node("aggregate", _node_aggregate)

    graph.add_edge(START, "extract")
    graph.add_edge("extract", "rule_check")
    graph.add_conditional_edges(
        "rule_check", _has_critical_violation, ["aggregate", "semantic_review"]
    )
    graph.add_edge("semantic_review", "aggregate")
    graph.add_edge("aggregate", END)
    return graph.compile()


def review_file(file_path: str | Path) -> ReviewReport:
    """端到端审核单个文件，返回结构化报告。"""
    path = Path(file_path)
    text = path.read_text(encoding="utf-8")
    final_state = build_graph().invoke({"source_file": str(path), "document_text": text})
    return ReviewReport(
        source_file=str(path),
        decision=final_state.get("decision", Decision.ERROR),
        summary=final_state.get("summary", "流程异常，未生成结论"),
        rule_findings=final_state.get("rule_findings", []),
        semantic_findings=final_state.get("semantic_findings", []),
        extracted=final_state.get("extracted"),
    )
