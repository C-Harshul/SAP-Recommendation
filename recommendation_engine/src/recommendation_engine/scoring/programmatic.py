"""Programmatic ranking features (no LLM)."""

from __future__ import annotations

import math
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import yaml

from recommendation_engine.models.schemas import ExtractedIdea, IdeaCluster, Specificity


def load_weights(config_path: Path | None = None) -> dict[str, float]:
    base = Path(__file__).resolve().parents[1] / "config" / "ranking_weights.yaml"
    path = config_path or base
    with path.open() as f:
        data = yaml.safe_load(f)
    return data["weights"]


def log_scaled_source_count(distinct_sources: int) -> float:
    if distinct_sources <= 0:
        return 0.0
    return min(1.0, math.log1p(distinct_sources) / math.log1p(20))


def shannon_entropy_source_diversity(source_types: list[str]) -> float:
    if not source_types:
        return 0.0
    counts = Counter(source_types)
    total = sum(counts.values())
    entropy = -sum((c / total) * math.log2(c / total) for c in counts.values())
    max_entropy = math.log2(len(counts)) if len(counts) > 1 else 1.0
    return entropy / max_entropy if max_entropy > 0 else 0.0


def recency_score(timestamps: list[datetime], half_life_days: float = 30.0) -> float:
    if not timestamps:
        return 0.5
    now = datetime.now(UTC)
    ages = []
    for ts in timestamps:
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)
        age_days = max(0.0, (now - ts).total_seconds() / 86400)
        ages.append(age_days)
    avg_age = sum(ages) / len(ages)
    return math.exp(-0.693 * avg_age / half_life_days)


def specificity_fraction(ideas: list[ExtractedIdea]) -> float:
    if not ideas:
        return 0.0
    good = sum(
        1 for i in ideas if i.specificity in (Specificity.SPECIFIC, Specificity.ACTIONABLE)
    )
    return good / len(ideas)


def effort_score(feasibility: float) -> float:
    """Higher effort_score = more effort (inverse of feasibility)."""
    return round(1.0 - feasibility, 4)


def impact_score(
    *,
    source_count: float,
    signal_urgency: float,
    market_validation: float,
    sap_relevance: float,
    novelty: float,
) -> float:
    """Composite impact axis for storytelling (equal blend of impact drivers)."""
    return round(
        (source_count + signal_urgency + market_validation + sap_relevance + novelty) / 5,
        4,
    )


def final_weighted_score(subscores: dict[str, float], weights: dict[str, float]) -> float:
    return round(sum(subscores.get(k, 0.0) * weights.get(k, 0.0) for k in weights), 4)


def market_alignment_flag(cluster: IdeaCluster, trend_count: int) -> str:
    if cluster.source_count >= 2 and trend_count == 0:
        return "validated_by_users_no_market_signal"
    if trend_count >= 3 and cluster.source_count == 0:
        return "speculative_no_internal_demand"
    if trend_count >= 3:
        return "market_validated"
    return "mixed_signal"
