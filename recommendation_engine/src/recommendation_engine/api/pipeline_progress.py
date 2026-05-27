"""Granular pipeline step tracking for the dashboard ranking tab."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

# LangGraph node order (workflow.py)
GRAPH_NODE_IDS = (
    "extract",
    "synthesize",
    "cluster",
    "match_trends",
    "rank",
    "writeup",
    "persist",
)

GRAPH_NODE_LABELS: dict[str, str] = {
    "extract": "Extract ideas",
    "synthesize": "Synthesize problems",
    "cluster": "Cluster ideas",
    "match_trends": "Match market trends",
    "rank": "Rank missions",
    "writeup": "Generate writeups",
    "persist": "Persist results",
}

PREP_STEPS: tuple[tuple[str, str], ...] = (
    ("validate", "Validate configuration"),
    ("load", "Load S3 & community data"),
    ("embed", "Embed market trends"),
)


class StepStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class PipelineStep:
    id: str
    label: str
    phase: str  # prep | graph
    status: StepStatus = StepStatus.PENDING
    detail: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "phase": self.phase,
            "status": self.status.value,
            "detail": self.detail,
        }


def _default_steps() -> list[PipelineStep]:
    steps: list[PipelineStep] = []
    for step_id, label in PREP_STEPS:
        steps.append(PipelineStep(id=step_id, label=label, phase="prep"))
    for node_id in GRAPH_NODE_IDS:
        steps.append(
            PipelineStep(
                id=node_id,
                label=GRAPH_NODE_LABELS[node_id],
                phase="graph",
            )
        )
    return steps


@dataclass
class PipelineProgressTracker:
    steps: list[PipelineStep] = field(default_factory=_default_steps)
    current_step_id: str | None = None
    progress_percent: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def reset(self) -> None:
        with self._lock:
            self.steps = _default_steps()
            self.current_step_id = None
            self.progress_percent = 0

    def _step_index(self, step_id: str) -> int:
        for i, s in enumerate(self.steps):
            if s.id == step_id:
                return i
        raise KeyError(step_id)

    def _recompute_percent(self) -> None:
        terminal = {
            StepStatus.COMPLETED,
            StepStatus.SKIPPED,
            StepStatus.FAILED,
        }
        done = sum(1 for s in self.steps if s.status in terminal)
        self.progress_percent = int(round(100 * done / len(self.steps)))

    def begin_step(self, step_id: str, *, detail: str | None = None) -> None:
        with self._lock:
            idx = self._step_index(step_id)
            self.steps[idx].status = StepStatus.RUNNING
            if detail:
                self.steps[idx].detail = detail
            self.current_step_id = step_id
            self._recompute_percent()

    def complete_step(self, step_id: str, *, detail: str | None = None) -> None:
        with self._lock:
            idx = self._step_index(step_id)
            self.steps[idx].status = StepStatus.COMPLETED
            if detail:
                self.steps[idx].detail = detail
            if self.current_step_id == step_id:
                self.current_step_id = None
            self._recompute_percent()

    def skip_step(self, step_id: str, *, detail: str | None = None) -> None:
        with self._lock:
            idx = self._step_index(step_id)
            self.steps[idx].status = StepStatus.SKIPPED
            if detail:
                self.steps[idx].detail = detail
            if self.current_step_id == step_id:
                self.current_step_id = None
            self._recompute_percent()

    def fail_step(self, step_id: str, *, detail: str | None = None) -> None:
        with self._lock:
            idx = self._step_index(step_id)
            self.steps[idx].status = StepStatus.FAILED
            if detail:
                self.steps[idx].detail = detail
            self.current_step_id = step_id
            self._recompute_percent()

    def fail_at_current(self, detail: str | None = None) -> None:
        with self._lock:
            if self.current_step_id:
                self.fail_step(self.current_step_id, detail=detail)

    def on_graph_node_started(self, node_id: str) -> None:
        self.begin_step(node_id)

    def on_graph_node_finished(self, node_id: str) -> None:
        self.complete_step(node_id)
        idx = self._step_index(node_id)
        if idx + 1 < len(self.steps):
            next_id = self.steps[idx + 1].id
            if next_id in GRAPH_NODE_IDS:
                self.begin_step(next_id)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "current_step_id": self.current_step_id,
                "progress_percent": self.progress_percent,
                "steps": [s.to_dict() for s in self.steps],
                "graph": {
                    "nodes": [
                        {"id": n, "label": GRAPH_NODE_LABELS[n]} for n in GRAPH_NODE_IDS
                    ],
                    "edges": [
                        {"from": GRAPH_NODE_IDS[i], "to": GRAPH_NODE_IDS[i + 1]}
                        for i in range(len(GRAPH_NODE_IDS) - 1)
                    ],
                },
            }


_progress = PipelineProgressTracker()


def get_progress_tracker() -> PipelineProgressTracker:
    return _progress
