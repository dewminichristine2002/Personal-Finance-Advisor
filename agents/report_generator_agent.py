"""
Agent 4 – Report Generator Agent  (Student 4 contribution)

Collates all analysis outputs (categorised transactions, spending summary,
budget recommendations) and produces a polished Markdown financial report
saved to disk.
"""

from __future__ import annotations

import crewai_bootstrap  # noqa: F401
from crewai import Agent

from config import LLM_STRING
from tools.report_writer_tool import report_writer_tool


def create_report_generator_agent() -> Agent:
    """Factory that builds the Report Generator Agent."""
    return Agent(
        role="Financial Report Writer",
        goal=(
            "Take the complete analysis – spending summary, budget targets, "
            "and recommendations – and produce a clear, well-structured "
            "Markdown financial report that is saved to the output directory."
        ),
        backstory=(
            "You are a professional technical writer specialising in financial "
            "reports. You value clarity, accurate tables, and logical structure. "
            "Your reports always include an executive summary, detailed "
            "breakdowns, and a recommendations section. You never introduce "
            "information that was not provided by upstream agents."
        ),
        tools=[report_writer_tool],
        llm=LLM_STRING,
        verbose=True,
        allow_delegation=False,
        max_iter=3,
    )
