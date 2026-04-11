"""
Personal Finance Advisor – Multi-Agent System
==============================================

Entry point that orchestrates 4 agents in a sequential pipeline:

  1. Data Ingestion Agent   → reads CSV transactions
  2. Expense Analyzer Agent → categorises spending
  3. Budget Advisor Agent   → generates 50/30/20 budget advice
  4. Report Generator Agent → writes Markdown report to disk

Run:
    python main.py                          # uses default sample data
    python main.py --file path/to/data.csv  # custom file
    python main.py --income 6000            # override monthly income
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from crewai import Crew, Process, Task

from agents import (
    create_data_ingestion_agent,
    create_expense_analyzer_agent,
    create_budget_advisor_agent,
    create_report_generator_agent,
)
from config import DATA_DIR, OUTPUT_DIR
from observability.logger import AgentLogger
from state.global_state import GlobalState


def build_crew(csv_path: str, monthly_income: float) -> Crew:
    """Construct the full CrewAI pipeline."""

    agent1 = create_data_ingestion_agent()
    agent2 = create_expense_analyzer_agent()
    agent3 = create_budget_advisor_agent()
    agent4 = create_report_generator_agent()

    task1 = Task(
        description=(
            f"Read the financial transactions CSV file located at '{csv_path}'. "
            "Validate the data and return all transactions as a clean JSON list. "
            "Report any rows that failed validation."
        ),
        expected_output=(
            "A JSON object with two keys: 'transactions' (list of validated "
            "transaction dicts with date, description, amount, category) and "
            "'errors' (list of error strings, possibly empty)."
        ),
        agent=agent1,
    )

    task2 = Task(
        description=(
            "Using the transaction data provided by the previous agent, "
            "categorize every transaction into a meaningful spending category "
            "and produce a per-category spending summary with totals and counts. "
            "Pass the raw transaction list from the previous task's output "
            "as the 'transactions_json' argument to your tool."
        ),
        expected_output=(
            "A JSON object with 'categorized_transactions' (list) and "
            "'spending_summary' (dict keyed by category with total and count)."
        ),
        agent=agent2,
        context=[task1],
    )

    task3 = Task(
        description=(
            f"The user's monthly income is ${monthly_income:,.2f}. "
            "Using the spending summary from the previous agent, apply the "
            "50/30/20 budgeting rule and generate budget recommendations. "
            "Pass the spending_summary JSON and the monthly_income number "
            "to your budget_calculator_tool."
        ),
        expected_output=(
            "A JSON object with 'budget' (targets, actuals, differences), "
            "'recommendations' (list of actionable advice strings)."
        ),
        agent=agent3,
        context=[task2],
    )

    task4 = Task(
        description=(
            "Combine all data from the previous agents – the spending summary "
            "and budget recommendations – into a single JSON string and pass it "
            "to the report_writer_tool to generate a Markdown financial report. "
            "The JSON should contain keys: 'budget', 'spending_summary', and "
            "'recommendations'."
        ),
        expected_output=(
            "A confirmation message stating the report was written successfully, "
            "including the file path and a brief preview of the report content."
        ),
        agent=agent4,
        context=[task2, task3],
    )

    return Crew(
        agents=[agent1, agent2, agent3, agent4],
        tasks=[task1, task2, task3, task4],
        process=Process.sequential,
        verbose=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Personal Finance Advisor MAS")
    parser.add_argument(
        "--file",
        default=os.path.join(DATA_DIR, "sample_transactions.csv"),
        help="Path to the transactions CSV file",
    )
    parser.add_argument(
        "--income",
        type=float,
        default=5000.0,
        help="Monthly income (default: 5000)",
    )
    args = parser.parse_args()

    if not os.path.isfile(args.file):
        print(f"ERROR: CSV file not found: {args.file}")
        sys.exit(1)

    logger = AgentLogger("orchestrator")
    logger.clear_trace()

    state = GlobalState()
    state.set("monthly_income", args.income, agent_name="orchestrator")

    print("=" * 60)
    print("  Personal Finance Advisor – Multi-Agent System")
    print("=" * 60)
    print(f"  CSV File : {args.file}")
    print(f"  Income   : ${args.income:,.2f}")
    print(f"  Output   : {OUTPUT_DIR}")
    print("=" * 60)

    start = logger.log_agent_start("Full pipeline execution")

    crew = build_crew(args.file, args.income)
    result = crew.kickoff()

    logger.log_agent_end(start, str(result)[:500])

    print("\n" + "=" * 60)
    print("  Pipeline Complete!")
    print("=" * 60)
    print(f"\nFinal output:\n{result}")

    print("\n--- Global State Snapshot ---")
    print(json.dumps(state.snapshot(), indent=2, default=str)[:2000])

    print(f"\n--- Execution trace saved to: logs/agent_trace.jsonl ---")
    trace = AgentLogger.read_trace()
    print(f"Total trace events: {len(trace)}")


if __name__ == "__main__":
    main()
