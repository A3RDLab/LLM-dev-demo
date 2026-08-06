"""声明式规则引擎。

从 YAML 加载规则集，对 LLM 抽取出的结构化字段做确定性评估。
设计原则：
- 规则可配置化：业务/合规人员编辑 YAML 即可增删规则，无需改代码；
- 结论可解释：每条 Finding 携带规则编号、严重级别与具体证据；
- 零幻觉：本层不调用任何模型，结果完全可复现。
"""

from __future__ import annotations

import operator
import re
from pathlib import Path
from typing import Any

import yaml

from .schemas import LoanDocument, RuleFinding, Severity

_OPS = {
    "<=": operator.le,
    ">=": operator.ge,
    "<": operator.lt,
    ">": operator.gt,
    "==": operator.eq,
}

DEFAULT_RULES_PATH = Path(__file__).resolve().parents[2] / "rules" / "credit_rules.yaml"


def load_rules(path: Path | str = DEFAULT_RULES_PATH) -> list[dict[str, Any]]:
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    rules = data.get("rules", [])
    if not rules:
        raise ValueError(f"规则文件 {path} 中没有可用规则")
    return rules


def _fmt(value: Any) -> str:
    """字段值的展示格式化。"""
    return "未填写" if value is None else str(value)


def _eval_rule(rule: dict[str, Any], doc: LoanDocument) -> RuleFinding:
    data = doc.model_dump()
    severity = Severity(rule.get("severity", "warning"))
    base = dict(rule_id=rule["id"], rule_name=rule["name"], severity=severity)
    rule_type = rule["type"]

    if rule_type == "required":
        missing = [f for f in rule["fields"] if data.get(f) in (None, "", [])]
        if not missing:
            return RuleFinding(**base, passed=True, message="必备要素齐全")
        return RuleFinding(
            **base, passed=False, message=f"{rule['message']}：缺失 {', '.join(missing)}"
        )

    if rule_type == "threshold":
        value = data.get(rule["field"])
        if value is None:
            return RuleFinding(**base, passed=False, message=f"字段 {rule['field']} 缺失，无法校验")
        # 比较目标可以是固定 value，也可以是另一字段乘以系数（如罚息 <= 利率*1.5）
        if "ref_field" in rule:
            ref = data.get(rule["ref_field"])
            if ref is None:
                return RuleFinding(**base, passed=False, message=f"参照字段 {rule['ref_field']} 缺失，无法校验")
            bound = ref * float(rule.get("ref_multiplier", 1.0))
        else:
            bound = float(rule["value"])
        passed = _OPS[rule["op"]](float(value), bound)
        # 浮点容差：<= / >= 比较时允许 1e-9 级误差，避免 8.6*1.5=12.899999... 误判
        if not passed and rule["op"] in ("<=", ">=") and abs(float(value) - bound) < 1e-9:
            passed = True
        detail = f"{rule['field']}={value}，要求 {rule['op']} {round(bound, 4)}"
        message = detail if passed else f"{rule['message']}（{detail}）"
        return RuleFinding(**base, passed=passed, message=message)

    if rule_type == "regex":
        value = data.get(rule["field"])
        if value is None:
            return RuleFinding(**base, passed=False, message=f"字段 {rule['field']} 缺失，无法校验")
        if re.fullmatch(rule["pattern"], str(value)):
            return RuleFinding(**base, passed=True, message=f"{rule['field']}={value} 格式合法")
        return RuleFinding(**base, passed=False, message=f"{rule['message']}：{_fmt(value)}")

    if rule_type == "enum":
        value = data.get(rule["field"])
        if value in rule["values"]:
            return RuleFinding(**base, passed=True, message=f"{rule['field']}={value} 取值合规")
        return RuleFinding(
            **base, passed=False, message=f"{rule['message']}：{_fmt(value)}（允许值：{rule['values']}）"
        )

    if rule_type == "sum_equals":
        items = data.get(rule["field"])
        if not items:
            return RuleFinding(**base, passed=False, message=f"字段 {rule['field']} 缺失，无法校验")
        total = sum(float(item[rule["sub_field"]]) for item in items)
        tolerance = float(rule.get("tolerance", 1e-6))
        if abs(total - float(rule["value"])) <= tolerance:
            return RuleFinding(**base, passed=True, message=f"合计 {total}，符合要求")
        return RuleFinding(**base, passed=False, message=f"{rule['message']}：合计 {total}")

    raise ValueError(f"不支持的规则类型: {rule_type}（规则 {rule['id']}）")


def evaluate(doc: LoanDocument, rules: list[dict[str, Any]]) -> list[RuleFinding]:
    """对抽取结果执行全部规则，返回每条规则的审核结论。"""
    return [_eval_rule(rule, doc) for rule in rules]
