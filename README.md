# Personal Finance Advisor – Multi-Agent System

A locally-hosted Multi-Agent System (MAS) that analyses personal financial transactions and generates budgeting advice using the **50/30/20 rule**.

Built with **CrewAI** + **Ollama** (local LLM) — zero cloud costs, full data privacy.

## Architecture

```
User Input (CSV) ──► Data Ingestion Agent ──► Expense Analyzer Agent
                          │                         │
                     [csv_reader_tool]        [expense_categorizer_tool]
                          │                         │
                     ▼ Global State ◄───────────────┘
                          │
                     Budget Advisor Agent ──► Report Generator Agent
                          │                         │
                   [budget_calculator_tool]    [report_writer_tool]
                          │                         │
                     ▼ Global State ◄───────────────┘
                          │
                     ▼ Markdown Report (output/)
```

### Agents

| # | Agent | Responsibility | Tool |
|---|-------|---------------|------|
| 1 | Data Ingestion Specialist | Reads & validates CSV transaction files | `csv_reader_tool` |
| 2 | Expense Analyzer | Categorises transactions & builds spending summary | `expense_categorizer_tool` |
| 3 | Budget Advisor | Applies 50/30/20 rule & generates recommendations | `budget_calculator_tool` |
| 4 | Financial Report Writer | Produces a polished Markdown report | `report_writer_tool` |

## Prerequisites

### 1. Install Python 3.10+

Download from https://www.python.org/downloads/ and **check "Add Python to PATH"** during installation.

### 2. Install Ollama

Download from https://ollama.com/download and install. Then pull the model:

```bash
ollama pull qwen3.5:4b
```

Verify Ollama is running:

```bash
ollama list
```

## Setup

```bash
# Clone / navigate to the project
cd MultipleAgent

# Create a virtual environment
python -m venv venv

# Activate it (Windows)
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Running the System

### Option A: Terminal (CLI)

```bash
# Using default sample data (monthly income = $5000)
python main.py

# Custom CSV file and income
python main.py --file path/to/your/data.csv --income 6000
```

### Option B: Web UI (Streamlit)

```bash
streamlit run app.py
```

This opens a browser-based dashboard where you can:
- Upload a CSV file or use sample data
- Set your monthly income
- Watch agents process your data
- View spending charts, budget analysis, and recommendations
- Download the generated report

The generated report will be saved in the `output/` directory.
Execution traces are logged to `logs/agent_trace.jsonl`.

## Running Tests

```bash
pytest tests/ -v
```

## Project Structure

```
MultipleAgent/
├── main.py                  # CLI entry point
├── app.py                   # Streamlit web UI
├── config.py                # Configuration (model, paths)
├── requirements.txt         # Python dependencies
├── .env                     # Environment variables
├── agents/
│   ├── data_ingestion_agent.py
│   ├── expense_analyzer_agent.py
│   ├── budget_advisor_agent.py
│   └── report_generator_agent.py
├── tools/
│   ├── csv_reader_tool.py
│   ├── expense_categorizer_tool.py
│   ├── budget_calculator_tool.py
│   └── report_writer_tool.py
├── state/
│   └── global_state.py      # Thread-safe singleton state manager
├── observability/
│   └── logger.py            # Structured JSON-Lines tracing
├── tests/
│   ├── test_csv_reader.py
│   ├── test_expense_categorizer.py
│   ├── test_budget_calculator.py
│   ├── test_report_writer.py
│   ├── test_observability.py
│   └── test_global_state.py
├── data/
│   └── sample_transactions.csv
├── output/                   # Generated reports go here
└── logs/                     # Execution trace logs
```

## Tech Stack

- **LLM**: Ollama with `qwen3.5:4b` (local, zero-cost)
- **Orchestration**: CrewAI (sequential pipeline)
- **Language**: Python 3.10+
- **Testing**: pytest
