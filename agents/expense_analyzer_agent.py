"""
Agent 2 – Expense Analyzer Agent  (Student 2 contribution)

Takes the raw transaction list from the global state, categorises each
transaction, and builds a per-category spending summary.
"""

from __future__ import annotations

import crewai_bootstrap  # noqa: F401
from crewai import Agent

from config import LLM_STRING
from tools.expense_categorizer_tool import expense_categorizer_tool


def create_expense_analyzer_agent() -> Agent:
    """Factory that builds the Expense Analyzer Agent."""
    return Agent(
        role="Expense Analyzer",
        goal=(
            "Categorize every transaction into a meaningful spending category "
            "(food, transport, entertainment, utilities, shopping, health, "
            "housing, education, or other) and produce a per-category spending "
            "summary with totals and counts."
        ),
        backstory=(
            "You are a certified financial analyst with deep expertise in "
            "personal spending patterns. You classify transactions using both "
            "the tool's keyword engine and your own knowledge. You always "
            "present numbers accurately and never estimate amounts."
        ),
        tools=[expense_categorizer_tool],
        llm=LLM_STRING,
        verbose=True,
        allow_delegation=False,
        max_iter=3,
    )
