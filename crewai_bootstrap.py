"""
Local CrewAI bootstrap settings for workspace-safe storage.

CrewAI defaults to creating storage inside the user AppData directory. That is
fine on a normal laptop, but sandboxed test environments may block writes
there. This module redirects CrewAI storage into the project workspace while
keeping everything local, which also aligns well with the assignment's zero-
cost and privacy requirements.
"""

from __future__ import annotations

import os


BASE_DIR = os.path.dirname(__file__)
CREWAI_STORAGE_ROOT = os.path.join(BASE_DIR, ".crewai")

os.makedirs(CREWAI_STORAGE_ROOT, exist_ok=True)
os.environ.setdefault("CREWAI_STORAGE_DIR", CREWAI_STORAGE_ROOT)
os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
os.environ.setdefault("CREWAI_DISABLE_TRACKING", "true")
