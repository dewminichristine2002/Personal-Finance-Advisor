"""
Test suite for the observability / logging layer.

Validates that the AgentLogger correctly writes structured trace events
to the JSON-Lines log file.
"""

from __future__ import annotations

from typing import Generator

import pytest

from observability.logger import AgentLogger


@pytest.fixture(autouse=True)
def _clean_trace() -> Generator[None, None, None]:
    AgentLogger.clear_trace()
    yield
    AgentLogger.clear_trace()


class TestAgentLogger:
    def test_agent_start_and_end_logged(self) -> None:
        logger = AgentLogger("test_agent")
        start = logger.log_agent_start("test task")
        logger.log_agent_end(start, "done")
        records = AgentLogger.read_trace()
        events = [r["event"] for r in records]
        assert "AGENT_START" in events
        assert "AGENT_END" in events

    def test_tool_call_logged(self) -> None:
        logger = AgentLogger("test_agent")
        logger.log_tool_call("my_tool", {"arg": "val"}, "result")
        records = AgentLogger.read_trace()
        assert any(r["event"] == "TOOL_CALL" and r["tool"] == "my_tool" for r in records)

    def test_state_update_logged(self) -> None:
        logger = AgentLogger("test_agent")
        logger.log_state_update("some_key", "some_value")
        records = AgentLogger.read_trace()
        assert any(r["event"] == "STATE_UPDATE" for r in records)

    def test_clear_trace_removes_file(self) -> None:
        logger = AgentLogger("test_agent")
        logger.log_agent_start("task")
        AgentLogger.clear_trace()
        assert AgentLogger.read_trace() == []
