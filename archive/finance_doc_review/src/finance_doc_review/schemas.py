"""Pydantic v2 数据模型：LLM 抽取的结构化字段、规则/语义审核发现、最终报告。"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


# ---------- 信息抽取 ----------

class RepaymentItem(BaseModel):
    """单期还款计划。"""

    period: int = Field(description="期数，从 1 开始")
    percentage: float = Field(description="该期还款金额占本金的百分比（0-100）")


class LoanDocument(BaseModel):
    """从信贷类资料中抽取的结构化字段，未提及的字段保持 None。"""

    borrower: str | None = Field(default=None, description="借款人/机构名称")
    borrower_id: str | None = Field(default=None, description="借款人证件号（身份证/统一社会信用代码）")
    lender: str | None = Field(default=None, description="出借方/贷款机构名称")
    principal: float | None = Field(default=None, description="本金金额，单位：元")
    annual_rate: float | None = Field(default=None, description="年化利率，百分比数值，如 8.5 表示 8.5%")
    term_months: int | None = Field(default=None, description="借款期限，单位：月")
    late_fee_rate: float | None = Field(default=None, description="逾期罚息年化利率，百分比数值")
    signed_date: str | None = Field(default=None, description="签署日期，ISO 格式 YYYY-MM-DD")
    repayment_schedule: list[RepaymentItem] | None = Field(
        default=None, description="还款计划表，仅在文档明确给出分期安排时填写"
    )


# ---------- 审核发现 ----------

class Severity(str, Enum):
    CRITICAL = "critical"   # 硬性违规，直接否决
    WARNING = "warning"     # 风险点，需人工复核
    INFO = "info"           # 提示性信息


class RuleFinding(BaseModel):
    """确定性规则引擎的审核结论，可解释、可追溯。"""

    rule_id: str
    rule_name: str
    severity: Severity
    passed: bool
    message: str


class SemanticFinding(BaseModel):
    """LLM 语义层审核发现，覆盖规则无法表达的模糊/矛盾/披露问题。"""

    category: Literal["risk_disclosure", "clause_ambiguity", "contradiction", "compliance", "other"]
    severity: Severity
    description: str = Field(description="问题描述及整改建议")
    evidence: str = Field(description="原文证据片段，逐字引用")


# ---------- 最终报告 ----------

class Decision(str, Enum):
    PASS = "pass"                       # 通过
    REVIEW_REQUIRED = "review_required" # 需人工复核
    REJECT = "reject"                   # 否决
    ERROR = "error"                     # 流程异常


class ReviewReport(BaseModel):
    """整份资料的最终审核报告。"""

    source_file: str
    decision: Decision
    summary: str
    rule_findings: list[RuleFinding] = []
    semantic_findings: list[SemanticFinding] = []
    extracted: LoanDocument | None = None
