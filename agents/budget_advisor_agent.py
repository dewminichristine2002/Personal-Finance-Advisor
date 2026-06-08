"""
Agent 3 – Budget Advisor Agent  (Student 3 contribution)

Receives the spending summary and applies the 50/30/20 budgeting
framework to generate personalised budget recommendations.
"""

from __future__ import annotations

import crewai_bootstrap  # noqa: F401
from crewai import Agent

from config import LLM_STRING
from tools.budget_calculator_tool import budget_calculator_tool


def create_budget_advisor_agent() -> Agent:
    """Factory that builds the Budget Advisor Agent."""
    return Agent(
        role="Budget Advisor",
        goal=(
            "Apply the 50/30/20 budgeting rule to the user's spending data "
            "and monthly income. Identify areas of overspending and produce "
            "clear, actionable recommendations to improve financial health."
        ),
        backstory=(
            "You are a personal finance coach who has helped hundreds of "
            "clients take control of their budgets. You communicate advice "
            "in plain language, back every suggestion with numbers, and "
            "never suggest speculative investments. Your focus is practical "
            "budgeting, not financial products."
        ),
        tools=[budget_calculator_tool],
        llm=LLM_STRING,
        verbose=True,
        allow_delegation=False,
        max_iter=3,
    )
