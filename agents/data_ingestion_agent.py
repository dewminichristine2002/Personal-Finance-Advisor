"""
Agent 1 – Data Ingestion Agent  (Student 1 contribution)

Responsible for loading raw financial transaction data from CSV files,
validating the data integrity, and placing cleaned records into the
global state for downstream agents.
"""

from __future__ import annotations

import crewai_bootstrap  # noqa: F401
from crewai import Agent

from config import LLM_STRING
from tools.csv_reader_tool import csv_reader_tool


def create_data_ingestion_agent() -> Agent:
    """Factory that builds the Data Ingestion Agent with its tool and prompt."""
    return Agent(
        role="Data Ingestion Specialist",
        goal=(
            "Accurately read the provided CSV file of financial transactions, "
            "validate every row, and return a clean JSON summary of the data. "
            "Report any parsing errors encountered."
        ),
        backstory=(
            "You are a meticulous data engineer who specialises in ETL pipelines. "
            "Your job is to ingest raw financial data, verify its schema, and flag "
            "any corrupt or missing values before the data moves downstream. "
            "You never fabricate data – if something is missing you report it."
        ),
        tools=[csv_reader_tool],
        llm=LLM_STRING,
        verbose=True,
        allow_delegation=False,
        max_iter=3,
    )
