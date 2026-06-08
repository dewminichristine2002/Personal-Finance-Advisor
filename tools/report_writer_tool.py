"""
Tool 4 – Report Writer Tool  (Student 4 contribution)

Takes structured analysis data and writes a human-readable Markdown
financial report to disk.
"""

from __future__ import annotations

import json
import os
import math
import textwrap
from datetime import datetime
from typing import Any, Dict, Iterable, List

import crewai_bootstrap  # noqa: F401
from crewai.tools import tool

from config import OUTPUT_DIR
from observability.logger import AgentLogger
from state.global_state import GlobalState

_logger = AgentLogger("report_writer_tool")


def _format_currency(amount: float) -> str:
    """Format numeric values using Sri Lankan rupee notation."""
    return f"Rs. {amount:,.2f}"


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
        lines.append(f"| Monthly Income | {_format_currency(_coerce_total(budget.get('monthly_income', 0)))} |")
        lines.append(f"| Total Spent | {_format_currency(_coerce_total(budget.get('total_spent', 0)))} |")
        remaining = _coerce_total(budget.get("monthly_income", 0)) - _coerce_total(budget.get("total_spent", 0))
        lines.append(f"| Remaining | {_format_currency(remaining)} |")
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
            lines.append(
                f"| {key.title()} | {_format_currency(t)} | {_format_currency(a)} | {_format_currency(d)} |"
            )
        lines.append("")

    if summary:
        lines.append("## Spending by Category\n")
        lines.append("| Category | Amount | Transactions |")
        lines.append("|----------|--------|-------------|")
        for cat, info in sorted(summary.items()):
            if cat.startswith("_"):
                continue
            lines.append(
                f"| {str(cat).title()} | {_format_currency(_coerce_total(info))} | {_coerce_count(info)} |"
            )
        lines.append("")

    if recommendations:
        lines.append("## Recommendations\n")
        for i, rec in enumerate(recommendations, 1):
            lines.append(f"{i}. {rec}")
        lines.append("")

    lines.append("---\n*Report generated by the Personal Finance Advisor Multi-Agent System*\n")
    return "\n".join(lines)


def _escape_pdf_text(text: str) -> str:
    """Escape characters that are special inside PDF text streams."""
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


class _SimplePdfCanvas:
    """Tiny PDF canvas for formatted text reports without third-party libraries."""

    PAGE_WIDTH = 612
    PAGE_HEIGHT = 792
    MARGIN_X = 48
    TOP_Y = 744
    BOTTOM_Y = 56

    def __init__(self) -> None:
        self.pages: list[list[str]] = []
        self.page_number = 0
        self.y = self.TOP_Y
        self._new_page()

    def _new_page(self) -> None:
        self.pages.append([])
        self.page_number += 1
        self.y = self.TOP_Y

    @property
    def _commands(self) -> list[str]:
        return self.pages[-1]

    def _ensure_space(self, height: float, repeat_header: bool = False) -> None:
        if self.y - height < self.BOTTOM_Y:
            self._draw_footer()
            self._new_page()
            if repeat_header:
                self._draw_page_header()

    def _append(self, command: str) -> None:
        self._commands.append(command)

    def draw_rect(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        *,
        fill: tuple[float, float, float] | None = None,
        stroke: tuple[float, float, float] | None = None,
        line_width: float = 1,
    ) -> None:
        if fill:
            self._append(f"{fill[0]:.3f} {fill[1]:.3f} {fill[2]:.3f} rg")
        if stroke:
            self._append(f"{stroke[0]:.3f} {stroke[1]:.3f} {stroke[2]:.3f} RG")
        self._append(f"{line_width:.2f} w")
        mode = "B" if fill and stroke else "f" if fill else "S"
        self._append(f"{x:.2f} {y:.2f} {width:.2f} {height:.2f} re {mode}")

    def draw_text(
        self,
        x: float,
        y: float,
        text: str,
        *,
        size: int = 11,
        font: str = "F1",
        color: tuple[float, float, float] = (0.12, 0.09, 0.20),
    ) -> None:
        escaped = _escape_pdf_text(text)
        self._append("BT")
        self._append(f"/{font} {size} Tf")
        self._append(f"{color[0]:.3f} {color[1]:.3f} {color[2]:.3f} rg")
        self._append(f"{x:.2f} {y:.2f} Td")
        self._append(f"({escaped}) Tj")
        self._append("ET")

    def draw_wrapped_text(
        self,
        x: float,
        y: float,
        text: str,
        *,
        width_chars: int,
        size: int = 11,
        font: str = "F1",
        color: tuple[float, float, float] = (0.12, 0.09, 0.20),
        line_gap: float = 15,
    ) -> float:
        lines = textwrap.wrap(
            text,
            width=width_chars,
            break_long_words=False,
            break_on_hyphens=False,
        ) or [text]
        current_y = y
        for line in lines:
            self.draw_text(x, current_y, line, size=size, font=font, color=color)
            current_y -= line_gap
        return current_y

    def _draw_page_header(self) -> None:
        header_y = self.PAGE_HEIGHT - 112
        self.draw_rect(
            self.MARGIN_X,
            header_y,
            self.PAGE_WIDTH - (self.MARGIN_X * 2),
            58,
            fill=(0.486, 0.227, 0.929),
        )
        self.draw_text(
            self.MARGIN_X + 16,
            header_y + 35,
            "Personal Finance Report",
            size=22,
            font="F2",
            color=(1, 1, 1),
        )
        self.draw_text(
            self.MARGIN_X + 16,
            header_y + 16,
            "Generated by the Personal Finance Advisor Multi-Agent System",
            size=10,
            font="F1",
            color=(0.988, 0.914, 0.596),
        )
        self.y = header_y - 18

    def _draw_footer(self) -> None:
        footer_y = 28
        self.draw_text(
            self.MARGIN_X,
            footer_y,
            "Local MAS report export",
            size=9,
            font="F1",
            color=(0.486, 0.424, 0.659),
        )
        self.draw_text(
            self.PAGE_WIDTH - self.MARGIN_X - 28,
            footer_y,
            str(self.page_number),
            size=9,
            font="F2",
            color=(0.486, 0.424, 0.659),
        )

    def draw_section_title(self, title: str) -> None:
        self._ensure_space(40)
        self.draw_text(
            self.MARGIN_X,
            self.y,
            title,
            size=15,
            font="F2",
            color=(0.851, 0.467, 0.024),
        )
        self.y -= 30

    def draw_subtitle(self, text: str) -> None:
        self._ensure_space(24)
        self.draw_text(
            self.MARGIN_X,
            self.y,
            text,
            size=11,
            font="F1",
            color=(0.486, 0.424, 0.659),
        )
        self.y -= 28

    def draw_table(self, headers: list[str], rows: list[list[str]], col_widths: list[float]) -> None:
        table_width = sum(col_widths)
        x = self.MARGIN_X
        header_height = 24
        self._ensure_space(header_height + 22, repeat_header=True)

        def draw_header() -> None:
            self.draw_rect(
                x,
                self.y - header_height + 4,
                table_width,
                header_height,
                fill=(0.929, 0.914, 0.996),
                stroke=(0.776, 0.706, 0.961),
            )
            cursor_x = x
            for idx, header in enumerate(headers):
                self.draw_text(
                    cursor_x + 8,
                    self.y - 13,
                    header,
                    size=10,
                    font="F2",
                    color=(0.357, 0.129, 0.714),
                )
                cursor_x += col_widths[idx]
                if idx < len(headers) - 1:
                    self._append(f"0.776 0.706 0.961 RG")
                    self._append(f"{cursor_x:.2f} {self.y - header_height + 4:.2f} m {cursor_x:.2f} {self.y + 4:.2f} l S")
            self.y -= header_height + 6

        draw_header()

        for row_index, row in enumerate(rows):
            wrapped_cells: list[list[str]] = []
            max_lines = 1
            for cell, width in zip(row, col_widths):
                width_chars = max(8, int(width / 6.4))
                wrapped = textwrap.wrap(
                    cell,
                    width=width_chars,
                    break_long_words=False,
                    break_on_hyphens=False,
                ) or [cell]
                wrapped_cells.append(wrapped)
                max_lines = max(max_lines, len(wrapped))

            row_height = 10 + (max_lines * 13)
            self._ensure_space(row_height + 8, repeat_header=True)
            if self.y < self.BOTTOM_Y + row_height + 8:
                self._draw_page_header()
                draw_header()

            fill = (0.988, 0.984, 1.0) if row_index % 2 == 0 else (0.969, 0.961, 0.996)
            self.draw_rect(
                x,
                self.y - row_height + 4,
                table_width,
                row_height,
                fill=fill,
                stroke=(0.902, 0.878, 0.973),
            )

            cursor_x = x
            for idx, cell_lines in enumerate(wrapped_cells):
                text_y = self.y - 13
                for line in cell_lines:
                    self.draw_text(
                        cursor_x + 8,
                        text_y,
                        line,
                        size=10,
                        font="F1",
                        color=(0.12, 0.09, 0.20),
                    )
                    text_y -= 12
                cursor_x += col_widths[idx]
                if idx < len(wrapped_cells) - 1:
                    self._append(f"0.902 0.878 0.973 RG")
                    self._append(f"{cursor_x:.2f} {self.y - row_height + 4:.2f} m {cursor_x:.2f} {self.y + 4:.2f} l S")

            self.y -= row_height + 4

        self.y -= 12

    def build(self) -> bytes:
        self._draw_footer()
        objects: dict[int, bytes] = {
            3: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
            4: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>",
        }
        page_numbers: list[int] = []
        next_object = 5

        for page_commands in self.pages:
            content_number = next_object
            page_number = next_object + 1
            next_object += 2
            stream = "\n".join(page_commands).encode("latin-1", errors="replace")
            objects[content_number] = (
                f"<< /Length {len(stream)} >>\nstream\n".encode("latin-1")
                + stream
                + b"\nendstream"
            )
            objects[page_number] = (
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {self.PAGE_WIDTH} {self.PAGE_HEIGHT}] "
                f"/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> "
                f"/Contents {content_number} 0 R >>"
            ).encode("latin-1")
            page_numbers.append(page_number)

        kids = " ".join(f"{page_number} 0 R" for page_number in page_numbers)
        objects[2] = f"<< /Type /Pages /Count {len(page_numbers)} /Kids [{kids}] >>".encode("latin-1")
        objects[1] = b"<< /Type /Catalog /Pages 2 0 R >>"

        pdf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets: dict[int, int] = {}
        for object_number in sorted(objects):
            offsets[object_number] = len(pdf)
            pdf.extend(f"{object_number} 0 obj\n".encode("latin-1"))
            pdf.extend(objects[object_number])
            pdf.extend(b"\nendobj\n")

        xref_start = len(pdf)
        pdf.extend(f"xref\n0 {max(objects) + 1}\n".encode("latin-1"))
        pdf.extend(b"0000000000 65535 f \n")
        for object_number in range(1, max(objects) + 1):
            offset = offsets[object_number]
            pdf.extend(f"{offset:010d} 00000 n \n".encode("latin-1"))

        pdf.extend(
            (
                f"trailer\n<< /Size {max(objects) + 1} /Root 1 0 R >>\n"
                f"startxref\n{xref_start}\n%%EOF"
            ).encode("latin-1")
        )
        return bytes(pdf)


def _build_pdf_bytes_from_analysis(data: Dict[str, Any]) -> bytes:
    """Build a more polished PDF report directly from structured analysis data."""
    canvas = _SimplePdfCanvas()
    canvas._draw_page_header()
    canvas.draw_subtitle(f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    budget = data.get("budget", {})
    spending_summary = data.get("spending_summary", {})
    recommendations = data.get("recommendations", [])

    if budget:
        canvas.draw_section_title("Budget Overview")
        remaining = budget.get("monthly_income", 0) - budget.get("total_spent", 0)
        budget_rows = [
            ["Monthly Income", _format_currency(budget.get("monthly_income", 0))],
            ["Total Spent", _format_currency(budget.get("total_spent", 0))],
            ["Remaining", _format_currency(remaining)],
        ]
        canvas.draw_table(["Metric", "Value"], budget_rows, [230, 180])

    if budget.get("targets"):
        canvas.draw_section_title("50/30/20 Budget Analysis")
        targets = budget.get("targets", {})
        actuals = budget.get("actuals", {})
        diffs = budget.get("differences", {})
        rows = []
        for key in ["needs", "wants", "savings"]:
            diff = diffs.get(key, 0)
            rows.append(
                [
                    key.title(),
                    _format_currency(targets.get(key, 0)),
                    _format_currency(actuals.get(key, diff)),
                    _format_currency(diff),
                ]
            )
        canvas.draw_table(["Category", "Target", "Actual", "Difference"], rows, [130, 110, 110, 110])

    if spending_summary:
        canvas.draw_section_title("Spending by Category")
        rows = []
        for category, info in sorted(spending_summary.items()):
            if category.startswith("_"):
                continue
            rows.append(
                [
                    category.title(),
                    _format_currency(info.get("total", 0)),
                    str(info.get("count", 0)),
                ]
            )
        canvas.draw_table(["Category", "Amount", "Transactions"], rows, [220, 120, 120])

    if recommendations:
        canvas.draw_section_title("Recommendations")
        for idx, recommendation in enumerate(recommendations, start=1):
            wrapped = textwrap.wrap(
                f"{idx}. {recommendation}",
                width=82,
                break_long_words=False,
                break_on_hyphens=False,
            ) or [recommendation]
            needed_height = 12 + (len(wrapped) * 15)
            canvas._ensure_space(needed_height, repeat_header=True)
            if canvas.y < canvas.BOTTOM_Y + needed_height:
                canvas._draw_page_header()
            canvas.draw_wrapped_text(
                canvas.MARGIN_X,
                canvas.y,
                f"{idx}. {recommendation}",
                width_chars=82,
                size=11,
                font="F1",
                color=(0.12, 0.09, 0.20),
            )
            canvas.y -= needed_height - 4

    return canvas.build()


def _build_pdf_bytes_from_markdown(markdown: str) -> bytes:
    """Backward-compatible wrapper for tests and existing call sites."""
    return _build_pdf_bytes_from_analysis(
        {
            "budget": {},
            "spending_summary": {},
            "recommendations": _markdown_to_text_lines(markdown),
        }
    )


def _markdown_to_text_lines(markdown: str) -> list[str]:
    """Convert markdown report text into plain lines."""
    plain_lines: list[str] = []
    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        if not line or line == "---":
            continue
        if line.startswith("#"):
            plain_lines.append(line.lstrip("#").strip())
            continue
        if line.startswith("*") and line.endswith("*"):
            plain_lines.append(line.strip("*"))
            continue
        if line.startswith("|") and line.endswith("|"):
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if set("".join(cells)) <= {"-"}:
                continue
            plain_lines.append(" | ".join(cells))
            continue
        plain_lines.append(line)
    return plain_lines


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
