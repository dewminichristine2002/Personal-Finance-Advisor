"""
AgentOps / LLMOps observability layer.

Records every agent invocation, tool call, input, output, and timing
information to both the console and a structured JSON-Lines log file.
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime
from typing import Any, Dict, Optional

from config import LOG_DIR


class AgentLogger:
    """Structured logger that traces agent executions and tool calls."""

    _LOG_FILE = os.path.join(LOG_DIR, "agent_trace.jsonl")

    def __init__(self, agent_name: str) -> None:
        self.agent_name = agent_name
        self._console = logging.getLogger(f"agent.{agent_name}")
        if not self._console.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(
                logging.Formatter(
                    "[%(asctime)s] %(name)s | %(levelname)s | %(message)s",
                    datefmt="%H:%M:%S",
                )
            )
            self._console.addHandler(handler)
            self._console.setLevel(logging.DEBUG)

    def _write_record(self, record: Dict[str, Any]) -> None:
        """Append a single JSON record to the trace file."""
        with open(self._LOG_FILE, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, default=str) + "\n")

    def log_agent_start(self, task_description: str) -> float:
        """Log the start of an agent's task execution. Returns a start timestamp."""
        start = time.time()
        record = {
            "event": "AGENT_START",
            "agent": self.agent_name,
            "task": task_description,
            "timestamp": datetime.now().isoformat(),
        }
        self._write_record(record)
        self._console.info("Starting task: %s", task_description[:120])
        return start

    def log_agent_end(self, start_time: float, output_preview: str) -> None:
        """Log the completion of an agent's task."""
        elapsed = round(time.time() - start_time, 2)
        record = {
            "event": "AGENT_END",
            "agent": self.agent_name,
            "elapsed_seconds": elapsed,
            "output_preview": output_preview[:500],
            "timestamp": datetime.now().isoformat(),
        }
        self._write_record(record)
        self._console.info("Completed in %.2fs", elapsed)

    def log_tool_call(
        self,
        tool_name: str,
        inputs: Dict[str, Any],
        output: Any,
        success: bool = True,
        error: Optional[str] = None,
    ) -> None:
        """Log a tool invocation with its inputs and outputs."""
        record = {
            "event": "TOOL_CALL",
            "agent": self.agent_name,
            "tool": tool_name,
            "inputs": {k: str(v)[:200] for k, v in inputs.items()},
            "output_preview": str(output)[:500],
            "success": success,
            "error": error,
            "timestamp": datetime.now().isoformat(),
        }
        self._write_record(record)
        status = "OK" if success else "FAIL"
        self._console.debug("Tool [%s] %s -> %s", tool_name, status, str(output)[:80])

    def log_state_update(self, key: str, value_preview: str) -> None:
        """Log a state mutation."""
        record = {
            "event": "STATE_UPDATE",
            "agent": self.agent_name,
            "key": key,
            "value_preview": value_preview[:300],
            "timestamp": datetime.now().isoformat(),
        }
        self._write_record(record)
        self._console.debug("State[%s] updated", key)

    @classmethod
    def read_trace(cls) -> list:
        """Read all trace records (useful for testing / reporting)."""
        records = []
        if os.path.exists(cls._LOG_FILE):
            with open(cls._LOG_FILE, "r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if line:
                        records.append(json.loads(line))
        return records

    @classmethod
    def clear_trace(cls) -> None:
        """Clear the trace file."""
        if os.path.exists(cls._LOG_FILE):
            os.remove(cls._LOG_FILE)
