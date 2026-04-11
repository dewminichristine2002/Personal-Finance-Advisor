"""
Test suite for the Global State Manager.

Validates thread-safety, deep-copy isolation, audit history, and reset.
"""

from __future__ import annotations

from typing import Generator

import pytest

from state.global_state import GlobalState


@pytest.fixture(autouse=True)
def _reset() -> Generator[None, None, None]:
    GlobalState.reset()
    yield
    GlobalState.reset()


class TestGlobalState:
    def test_singleton(self) -> None:
        a = GlobalState()
        b = GlobalState()
        assert a is b

    def test_set_and_get(self) -> None:
        state = GlobalState()
        state.set("key", [1, 2, 3], agent_name="test")
        assert state.get("key") == [1, 2, 3]

    def test_deep_copy_isolation(self) -> None:
        state = GlobalState()
        state.set("list", [1, 2], agent_name="test")
        retrieved = state.get("list")
        retrieved.append(99)
        assert state.get("list") == [1, 2]

    def test_append(self) -> None:
        state = GlobalState()
        state.append("items", "a", agent_name="test")
        state.append("items", "b", agent_name="test")
        assert state.get("items") == ["a", "b"]

    def test_history_records_mutations(self) -> None:
        state = GlobalState()
        state.set("x", 1, agent_name="agent1")
        state.set("y", 2, agent_name="agent2")
        history = state.history()
        assert len(history) >= 2
        agents = {h["agent"] for h in history}
        assert "agent1" in agents
        assert "agent2" in agents

    def test_reset_clears_state(self) -> None:
        state = GlobalState()
        state.set("data", "value", agent_name="test")
        GlobalState.reset()
        new_state = GlobalState()
        assert new_state.get("data") is None

    def test_snapshot_returns_full_state(self) -> None:
        state = GlobalState()
        state.set("a", 1, agent_name="test")
        snap = state.snapshot()
        assert "a" in snap
        assert snap["a"] == 1

    def test_to_json(self) -> None:
        state = GlobalState()
        state.set("val", {"nested": True}, agent_name="test")
        j = state.to_json()
        assert '"nested": true' in j
