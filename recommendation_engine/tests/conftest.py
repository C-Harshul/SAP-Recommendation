"""Test-only mocks (production code does not use fixture/mock LLM paths)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from recommendation_engine.config.settings import Settings
from recommendation_engine.models.schemas import (
    ClusterCanonicalLLM,
    EnrichedTrendBatchLLM,
    EnrichedTrendItemLLM,
    ExtractNodeOutput,
    ExtractedIdeaLLM,
    MissionWriteupLLM,
    QualitativeScores,
    Specificity,
    SynthesizeNodeOutput,
    SynthesizedSolutionLLM,
)


@pytest.fixture
def fixtures_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "src" / "recommendation_engine" / "fixtures"


@pytest.fixture
def test_settings(fixtures_dir: Path, monkeypatch) -> Settings:
    monkeypatch.setenv("EG_ALLOW_FIXTURES", "1")
    monkeypatch.setenv("EG_DATA_SOURCE", "fixtures")
    monkeypatch.setenv("EG_EMBEDDING_PROVIDER", "gemini")
    return Settings(
        llm_mode="live",
        google_api_key="test-google-key",
        embedding_provider="gemini",
        allow_fixtures=True,
        enrich_bronze_trends=False,
        fixtures_dir=fixtures_dir,
    )


@pytest.fixture(autouse=True)
def patch_live_clients(monkeypatch, test_settings):
    """Avoid real API calls in unit tests."""
    monkeypatch.setenv("GOOGLE_API_KEY", "test-google-key")
    monkeypatch.setattr(
        "recommendation_engine.config.settings.get_settings",
        lambda: test_settings,
    )
    monkeypatch.setattr(
        "recommendation_engine.io.data_loader.get_settings",
        lambda: test_settings,
    )

    def _fake_structured(self, *, model, system, user, output_schema, max_tokens=4096):
        name = output_schema.__name__
        if name == "ExtractNodeOutput":
            return ExtractNodeOutput(
                ideas=[
                    ExtractedIdeaLLM(
                        pain_point="Onboarding pain from transcript.",
                        proposed_solution=None,
                        evidence_quotes=["three weeks figuring out APIs"],
                        specificity=Specificity.SPECIFIC,
                    )
                ]
            )
        if name == "SynthesizeNodeOutput":
            return SynthesizeNodeOutput(
                solutions=[
                    SynthesizedSolutionLLM(
                        solution_text="AI onboarding copilot.",
                        approach="4-week BTP prototype.",
                    )
                ]
            )
        if name == "ClusterCanonicalLLM":
            return ClusterCanonicalLLM(canonical_statement="Improve SAP developer onboarding.")
        if name == "QualitativeScores":
            return QualitativeScores(
                signal_urgency=0.7,
                market_validation=0.65,
                sap_relevance=0.8,
                feasibility=0.6,
                novelty=0.55,
                rationale="test",
            )
        if name == "MissionWriteupLLM":
            return MissionWriteupLLM(
                the_mission="Build onboarding copilot.",
                why_this_matters="Users cited onboarding pain.",
                industry_context="Agentic RAG trend.",
                suggested_approach="2-week spike.",
                risks_and_open_questions="Permissions.",
            )
        if name == "EnrichedTrendBatchLLM":
            return EnrichedTrendBatchLLM(
                trends=[
                    EnrichedTrendItemLLM(
                        trend_id="trend-1",
                        theme="Agentic RAG",
                        summary="Enterprise RAG with tools.",
                        momentum="rising",
                        novelty="emerging",
                        evidence_urls=["https://example.com"],
                    )
                ]
            )
        return output_schema.model_construct()

    def _fake_embed(self, texts):
        dim = test_settings.embedding_dim
        out = []
        for i, _ in enumerate(texts):
            vec = np.zeros(dim)
            vec[i % dim] = 1.0
            out.append(vec.tolist())
        return out

    def _fake_embed_query(self, text):
        return _fake_embed(self, [text])[0]

    monkeypatch.setattr(
        "recommendation_engine.llm.client.LLMClient.structured",
        _fake_structured,
    )
    monkeypatch.setattr(
        "recommendation_engine.io.embeddings.EmbeddingClient.embed",
        _fake_embed,
    )
    monkeypatch.setattr(
        "recommendation_engine.io.embeddings.EmbeddingClient.embed_query",
        _fake_embed_query,
    )
