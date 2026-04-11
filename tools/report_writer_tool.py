"""
Tool 4 – Report Writer Tool  (Student 4 contribution)

Takes structured analysis data and writes a human-readable Markdown
financial report to disk.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Dict, Iterable, List

from crewai.tools import tool

from config import OUTPUT_DIR
from observability.logger import AgentLogger
from state.global_state import GlobalState

_logger = AgentLogger("report_writer_tool")


def _coerce_mapping(value: Any) -> Dict[str, Any]:
    """Return a dict-like object from common summary shapes."""
    if isinstance(value, dict):
        return value

    if isinstance(value, list):
        merged: Dict[str, Any] = {}
        for item in value:
            if not isinstance(item, dict):
                continue
            category = item.get("category") or item.get("name") or item.get("label")
            if category:
                merged[str(category)] = item
        return merged

    return {}


def _coerce_total(value: Any) -> float:
    """Extract a numeric total from dicts, numbers, or list-like structures."""
    if isinstance(value, dict):
        raw_total = value.get("total", value.get("amount", 0.0))
    elif isinstance(value, list):
        raw_total = 0.0
        for item in value:
            if isinstance(item, dict):
                raw_total += _coerce_total(item)
            else:
                try:
                    raw_total += float(item)
                except (TypeError, ValueError):
                    continue
    else:
        raw_total = value

    try:
        return float(raw_total)
    except (TypeError, ValueError):
        return 0.0


def _coerce_count(value: Any) -> int:
    """Extract a numeric transaction count from dicts or list-like structures."""
    if isinstance(value, dict):
        raw_count = value.get("count", value.get("transactions", 0))
        try:
            return int(raw_count)
        except (TypeError, ValueError):
            return 0

    if isinstance(value, list):
        return len(value)

    return 0


def _coerce_recommendations(value: Any) -> List[str]:
    """Normalize recommendations into a list of strings."""
    if isinstance(value, list):
        recommendations: List[str] = []
        for item in value:
            if isinstance(item, str):
                recommendations.append(item)
            elif isinstance(item, dict):
                recommendation = item.get("recommendation") or item.get("text") or item.get("message")
                if recommendation:
                    recommendations.append(str(recommendation))
            elif item is not None:
                recommendations.append(str(item))
        return recommendations

    if isinstance(value, str):
        return [value]

    return []


def _build_markdown(data: Dict[str, Any]) -> str:
    """Render a Markdown report from the combined analysis data."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        f"# Personal Finance Report",
        f"*Generated on {now}*\n",
        "---\n",
    ]

    budget = _coerce_mapping(data.get("budget", {}))
    summary = _coerce_mapping(data.get("spending_summary", {}))
    recommendations = _coerce_recommendations(data.get("recommendations", []))

    if budget:
        lines.append("## Budget Overview\n")
        lines.append(f"| Metric | Value |")
        lines.append(f"|--------|-------|")
        lines.append(f"| Monthly Income | ${_coerce_total(budget.get('monthly_income', 0)):,.2f} |")
        lines.append(f"| Total Spent | ${_coerce_total(budget.get('total_spent', 0)):,.2f} |")
        remaining = _coerce_total(budget.get("monthly_income", 0)) - _coerce_total(budget.get("total_spent", 0))
        lines.append(f"| Remaining | ${remaining:,.2f} |")
        lines.append("")

    if budget.get("targets"):
        lines.append("## 50/30/20 Budget Analysis\n")
        lines.append("| Category | Target | Actual | Difference |")
        lines.append("|----------|--------|--------|------------|")
        targets = _coerce_mapping(budget.get("targets", {}))
        actuals = _coerce_mapping(budget.get("actuals", {}))
        diffs = _coerce_mapping(budget.get("differences", {}))
        for key in ["needs", "wants", "savings"]:
            t = _coerce_total(targets.get(key, 0))
            a = _coerce_total(actuals.get(key, diffs.get(key, 0)))
            d = _coerce_total(diffs.get(key, 0))
            status = "+" if d >= 0 else ""
            lines.append(f"| {key.title()} | ${t:,.2f} | ${a:,.2f} | {status}${d:,.2f} |")
        lines.append("")

    if summary:
        lines.append("## Spending by Category\n")
        lines.append("| Category | Amount | Transactions |")
        lines.append("|----------|--------|-------------|")
        for cat, info in sorted(summary.items()):
            if cat.startswith("_"):
                continue
            lines.append(f"| {str(cat).title()} | ${_coerce_total(info):,.2f} | {_coerce_count(info)} |")
        lines.append("")

    if recommendations:
        lines.append("## Recommendations\n")
        for i, rec in enumerate(recommendations, 1):
            lines.append(f"{i}. {rec}")
        lines.append("")

    lines.append("---\n*Report generated by the Personal Finance Advisor Multi-Agent System*\n")
    return "\n".join(lines)


@tool("report_writer_tool")
def report_writer_tool(analysis_json: str) -> str:
    """Generate a Markdown financial report and save it to disk.

    Accepts the combined analysis output (budget, spending summary,
    recommendations) as a JSON string and writes a formatted Markdown
    report to the output directory.

    Args:
        analysis_json: JSON string containing keys 'budget',
            'spending_summary', and 'recommendations'.

    Returns:
        A confirmation message with the file path of the generated report.
    """
    state = GlobalState()

    try:
        data: Dict[str, Any] = json.loads(analysis_json)
    except json.JSONDecodeError as exc:
        error_msg = f"Invalid JSON input: {exc}"
        _logger.log_tool_call("report_writer_tool", {}, error_msg, success=False, error=error_msg)
        return error_msg

    markdown = _build_markdown(data)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"finance_report_{timestamp}.md"
    filepath = os.path.join(OUTPUT_DIR, filename)

    try:
        with open(filepath, "w", encoding="utf-8") as fh:
            fh.write(markdown)
    except OSError as exc:
        error_msg = f"Failed to write report: {exc}"
        _logger.log_tool_call("report_writer_tool", {"filepath": filepath}, error_msg, success=False, error=error_msg)
        return error_msg

    state.set("report_path", filepath, agent_name="ReportGeneratorAgent")
    _logger.log_tool_call(
        "report_writer_tool",
        {"filepath": filepath},
        f"Report written ({len(markdown)} chars)",
    )
    _logger.log_state_update("report_path", filepath)

    return f"Report successfully written to: {filepath}\n\nReport preview:\n{markdown[:1000]}"
