"""Pydantic AI Agent 层：LLM 只做两件事，且全部要求结构化输出。

1. extraction_agent —— 从原始资料文本中抽取结构化字段（output_type=LoanDocument），
   抽取结果交给确定性规则引擎评估，LLM 不下任何合规结论；
2. semantic_agent   —— 审核规则引擎覆盖不到的语义问题：风险披露缺失、条款歧义、
   前后矛盾、诱导性表述等，每条发现必须附原文证据（output_type=list[SemanticFinding]）。

模型通过 OpenAI 兼容网关接入（OPENAI_API_KEY / OPENAI_API_BASE / REVIEW_MODEL）。
"""

from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv
from pydantic_ai import Agent
from pydantic_ai.providers.openai import OpenAIProvider

from .schemas import LoanDocument, SemanticFinding

_EXTRACTION_PROMPT = """\
你是金融机构的资料录入专员，任务是从信贷资料文本中抽取结构化字段。
要求：
- 严格按给定 schema 输出，不要臆测或补全文档中没有的信息，未提及的字段一律为 null；
- 金额统一换算为元；利率统一换算为年化百分比数值（如 "月息1分" 即年化 12%）；
- 日期统一转换为 YYYY-MM-DD；
- 仅当文档明确列出分期还款安排时才填写 repayment_schedule。"""

_SEMANTIC_PROMPT = """\
你是资深金融合规审核员。规则引擎已完成数值与格式类硬性校验，你只需关注规则无法覆盖的语义问题：
1. risk_disclosure：风险提示/免责声明缺失或流于形式；
2. clause_ambiguity：条款表述含糊，可能引发争议（如"视情况调整""最终解释权"类表述）；
3. contradiction：文档内部前后数据或承诺相互矛盾；
4. compliance：涉嫌违反宣传规范的表述（如保本保收益、绝对化用语、诱导借贷）；
5. other：其他值得人工关注的异常。
要求：
- 每条发现必须给出逐字引用的原文证据（evidence），不得虚构；
- 文档本身没有问题的方面不要凑数输出，没有发现就返回空列表；
- severity 评估口径：critical=可能导致监管处罚或法律纠纷，warning=需要人工确认，info=提示性。"""


def _model_name() -> str:
    load_dotenv()
    return f"openai:{os.getenv('REVIEW_MODEL', 'deepseek-chat')}"


def _provider() -> OpenAIProvider:
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("缺少环境变量 OPENAI_API_KEY，请复制 .env.example 为 .env 并填写")
    return OpenAIProvider(api_key=api_key, base_url=os.getenv("OPENAI_API_BASE"))


@lru_cache
def get_extraction_agent() -> Agent:
    return Agent(
        _model_name(),
        provider=_provider(),
        output_type=LoanDocument,
        system_prompt=_EXTRACTION_PROMPT,
    )


@lru_cache
def get_semantic_agent() -> Agent:
    return Agent(
        _model_name(),
        provider=_provider(),
        output_type=list[SemanticFinding],
        system_prompt=_SEMANTIC_PROMPT,
    )
