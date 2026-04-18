"""
Personal Finance Advisor - Multi-Agent System
=============================================

Entry point for the local 4-agent finance pipeline.

Run:
    python main.py
    python main.py --file path/to/data.csv
    python main.py --income 6000
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from config import DATA_DIR, OUTPUT_DIR, PIPELINE_MODE
from observability.logger import AgentLogger
from pipeline import run_pipeline
from state.global_state import GlobalState


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
    print("  Personal Finance Advisor - Multi-Agent System")
    print("=" * 60)
    print(f"  CSV File : {args.file}")
    print(f"  Income   : ${args.income:,.2f}")
    print(f"  Output   : {OUTPUT_DIR}")
    print(f"  Mode     : {PIPELINE_MODE}")
    print("=" * 60)

    start = logger.log_agent_start("Full pipeline execution")
    result = run_pipeline(args.file, args.income, mode=PIPELINE_MODE)
    logger.log_agent_end(start, str(result)[:500])

    print("\n" + "=" * 60)
    print("  Pipeline Complete!")
    print("=" * 60)
    print(f"\nFinal output:\n{result}")

    print("\n--- Global State Snapshot ---")
    print(json.dumps(state.snapshot(), indent=2, default=str)[:2000])

    print("\n--- Execution trace saved to: logs/agent_trace.jsonl ---")
    trace = AgentLogger.read_trace()
    print(f"Total trace events: {len(trace)}")


if __name__ == "__main__":
    main()
