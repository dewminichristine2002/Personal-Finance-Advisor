"""
Global state manager for the Multi-Agent System.

Provides a thread-safe singleton that holds all shared data flowing between
agents.  Every mutation is timestamped and recorded so observability tooling
can reconstruct the full pipeline history.
"""

from __future__ import annotations

import threading
import copy
import json
from datetime import datetime
from typing import Any, Dict, List, Optional


class GlobalState:
    """Thread-safe global state shared across all agents in the pipeline."""

    _instance: Optional["GlobalState"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "GlobalState":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._state: Dict[str, Any] = {
            "raw_transactions": [],
            "categorized_transactions": [],
            "spending_summary": {},
            "budget_recommendations": {},
            "report_path": "",
            "errors": [],
        }
        self._history: List[Dict[str, Any]] = []

    def get(self, key: str) -> Any:
        """Retrieve a deep copy of a value so callers cannot mutate state directly."""
        with self._lock:
            return copy.deepcopy(self._state.get(key))

    def set(self, key: str, value: Any, agent_name: str = "system") -> None:
        """Set a value and record the change in the audit history."""
        with self._lock:
            self._history.append({
                "timestamp": datetime.now().isoformat(),
                "agent": agent_name,
                "action": "SET",
                "key": key,
                "value_preview": str(value)[:200],
            })
            self._state[key] = copy.deepcopy(value)

    def append(self, key: str, value: Any, agent_name: str = "system") -> None:
        """Append to a list-type value in the state."""
        with self._lock:
            if key not in self._state or not isinstance(self._state[key], list):
                self._state[key] = []
            self._state[key].append(copy.deepcopy(value))
            self._history.append({
                "timestamp": datetime.now().isoformat(),
                "agent": agent_name,
                "action": "APPEND",
                "key": key,
                "value_preview": str(value)[:200],
            })

    def snapshot(self) -> Dict[str, Any]:
        """Return a JSON-serialisable deep copy of the entire state."""
        with self._lock:
            return copy.deepcopy(self._state)

    def history(self) -> List[Dict[str, Any]]:
        """Return the full mutation history for observability."""
        with self._lock:
            return copy.deepcopy(self._history)

    def to_json(self) -> str:
        """Serialise the current state to a JSON string."""
        return json.dumps(self.snapshot(), indent=2, default=str)

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton (used primarily in testing)."""
        with cls._lock:
            cls._instance = None
