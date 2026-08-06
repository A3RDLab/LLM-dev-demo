"""命令行入口：finance-doc-review <文件路径> [--json]"""

from __future__ import annotations

import argparse
import json
import sys

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .graph import review_file
from .schemas import Decision, Severity

console = Console()

_DECISION_STYLE = {
    Decision.PASS: ("✅ 通过", "green"),
    Decision.REVIEW_REQUIRED: ("⚠️ 需人工复核", "yellow"),
    Decision.REJECT: ("❌ 否决", "red"),
    Decision.ERROR: ("💥 流程异常", "magenta"),
}
_SEVERITY_STYLE = {Severity.CRITICAL: "red", Severity.WARNING: "yellow", Severity.INFO: "cyan"}


def _print_report(report) -> None:
    label, color = _DECISION_STYLE[report.decision]
    console.print(Panel(report.summary, title=f"审核结论 [{color}]{label}[/]", border_style=color))

    if report.extracted:
        fields = {
            k: v for k, v in report.extracted.model_dump().items() if v is not None
        }
        console.print(Panel(json.dumps(fields, ensure_ascii=False, indent=2),
                            title="LLM 抽取的结构化字段", border_style="blue"))

    table = Table(title="规则引擎校验明细", show_lines=True)
    for col in ("规则", "名称", "级别", "结论", "说明"):
        table.add_column(col)
    for f in report.rule_findings:
        style = _SEVERITY_STYLE[f.severity]
        table.add_row(
            f.rule_id, f.rule_name, f"[{style}]{f.severity.value}[/]",
            "[green]通过[/]" if f.passed else "[red]违规[/]", f.message,
        )
    console.print(table)

    if report.semantic_findings:
        sem = Table(title="LLM 语义审核发现", show_lines=True)
        for col in ("类别", "级别", "描述", "原文证据"):
            sem.add_column(col)
        for f in report.semantic_findings:
            style = _SEVERITY_STYLE[f.severity]
            sem.add_row(f.category, f"[{style}]{f.severity.value}[/]", f.description, f.evidence)
        console.print(sem)


def main() -> None:
    parser = argparse.ArgumentParser(description="金融资料审核：规则引擎 + LLM 混合审核")
    parser.add_argument("file", help="待审核的资料文件路径（文本文件）")
    parser.add_argument("--json", action="store_true", help="以 JSON 格式输出完整报告")
    args = parser.parse_args()

    report = review_file(args.file)
    if args.json:
        print(report.model_dump_json(indent=2))
    else:
        _print_report(report)
    sys.exit(0 if report.decision is Decision.PASS else 1)


if __name__ == "__main__":
    main()
