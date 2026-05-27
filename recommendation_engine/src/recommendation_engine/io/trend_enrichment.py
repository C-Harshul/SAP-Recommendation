"""Gemini enrichment of bronze-derived trends (Stage 1 parity for dynamic runs)."""

from __future__ import annotations

import structlog

from recommendation_engine.config.settings import Settings, get_settings
from recommendation_engine.llm.client import LLMClient
from recommendation_engine.llm import prompts
from recommendation_engine.models.schemas import EnrichedTrendBatchLLM, Momentum, TrendSignal

log = structlog.get_logger()


def enrich_trends_with_llm(
    trends: list[TrendSignal],
    *,
    settings: Settings | None = None,
    llm: LLMClient | None = None,
) -> list[TrendSignal]:
    """Replace heuristic bronze summaries with Gemini-enriched trend signals."""
    if not trends:
        return []

    settings = settings or get_settings()
    llm = llm or LLMClient(settings)
    batch_size = max(1, settings.trend_enrichment_batch_size)
    enriched: list[TrendSignal] = []

    for start in range(0, len(trends), batch_size):
        batch = trends[start : start + batch_size]
        items_block = "\n\n".join(
            f"- trend_id: {t.trend_id}\n  theme: {t.theme}\n  summary: {t.summary}\n"
            f"  evidence_urls: {t.evidence_urls}\n  source_count: {t.source_count}"
            for t in batch
        )
        out = llm.structured(
            model=settings.model_trend_enrichment,
            system=prompts.TREND_ENRICH_SYSTEM,
            user=prompts.TREND_ENRICH_USER.format(items=items_block),
            output_schema=EnrichedTrendBatchLLM,
        )
        by_id = {item.trend_id: item for item in out.trends}
        for original in batch:
            item = by_id.get(original.trend_id)
            if not item:
                enriched.append(original)
                continue
            momentum = item.momentum.lower()
            if momentum not in {m.value for m in Momentum}:
                momentum = Momentum.STABLE.value
            enriched.append(
                original.model_copy(
                    update={
                        "theme": item.theme,
                        "summary": item.summary,
                        "momentum": momentum,
                        "novelty": item.novelty,
                        "evidence_urls": item.evidence_urls or original.evidence_urls,
                    }
                )
            )

    log.info("trends_enriched", input_count=len(trends), output_count=len(enriched))
    return enriched
