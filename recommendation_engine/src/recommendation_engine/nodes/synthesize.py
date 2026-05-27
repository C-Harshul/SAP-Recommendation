"""Stage 3: Synthesize solutions for problem-only interviews using market trends."""

from __future__ import annotations

import uuid

import structlog

from recommendation_engine.config.settings import get_settings
from recommendation_engine.io.embeddings import EmbeddingClient, cosine_similarity
from recommendation_engine.llm.client import LLMClient
from recommendation_engine.llm import prompts
from recommendation_engine.models.schemas import (
    CandidateSolution,
    SolutionOrigin,
    SynthesizeBatchLLM,
    SynthesizeNodeOutput,
)
from recommendation_engine.models.state import RecommendationState

log = structlog.get_logger()


def _retrieve_trends(problem_text: str, trends: list, embedder: EmbeddingClient, k: int) -> list:
    if not trends:
        return []
    query = embedder.embed_query(problem_text)
    scored = []
    for t in trends:
        if t.embedding:
            sim = cosine_similarity(query, t.embedding)
        else:
            vec = embedder.embed_query(f"{t.theme} {t.summary}")
            t.embedding = vec
            sim = cosine_similarity(query, vec)
        scored.append((sim, t))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [t for _, t in scored[:k]]


def synthesize_node(state: RecommendationState) -> dict:
    settings = get_settings()
    llm = LLMClient(settings)
    embedder = EmbeddingClient(settings)
    trends = state.get("trend_signals", [])
    problems = state.get("extracted_problems", [])

    solutions: list[CandidateSolution] = []

    def _append_solutions(
        problem,
        related: list,
        sols: list,
        vectors: list[list[float]],
    ) -> None:
        for idx, sol in enumerate(sols):
            solutions.append(
                CandidateSolution(
                    solution_id=f"sol-{uuid.uuid4().hex[:10]}",
                    problem_id=problem.idea_id,
                    solution_text=sol.solution_text,
                    approach=sol.approach,
                    origin=SolutionOrigin.LLM_SYNTHESIZED,
                    inspired_by=[t.trend_id for t in related],
                    embedding=vectors[idx] if idx < len(vectors) else None,
                )
            )

    if settings.llm_batch_synthesize and len(problems) > 1:
        blocks: list[str] = []
        problem_trends: list[list] = []
        for pidx, problem in enumerate(problems):
            related = _retrieve_trends(
                problem.pain_point, trends, embedder, settings.trend_retrieval_k
            )
            problem_trends.append(related)
            trend_block = "\n".join(
                f"- [{t.trend_id}] {t.theme}: {t.summary} (momentum={t.momentum})"
                for t in related
            )
            quotes = "\n".join(q.quote for q in problem.evidence_quotes)
            blocks.append(
                f"### Problem {pidx}\n"
                f"Pain: {problem.pain_point}\n"
                f"Quotes:\n{quotes}\n"
                f"Trends:\n{trend_block or '(none)'}"
            )
        batch_out = llm.structured(
            model=settings.model_synthesize,
            system=prompts.SYNTHESIZE_BATCH_SYSTEM,
            user=prompts.SYNTHESIZE_BATCH_USER.format(problems_block="\n\n".join(blocks)),
            output_schema=SynthesizeBatchLLM,
            max_tokens=8192,
        )
        by_index = {item.problem_index: item for item in batch_out.problems}
        for pidx, problem in enumerate(problems):
            item = by_index.get(pidx)
            if not item:
                continue
            texts = [s.solution_text for s in item.solutions]
            vectors = embedder.embed(texts) if texts else []
            _append_solutions(problem, problem_trends[pidx], item.solutions, vectors)
    else:
        for problem in problems:
            related = _retrieve_trends(
                problem.pain_point, trends, embedder, settings.trend_retrieval_k
            )
            trend_block = "\n".join(
                f"- [{t.trend_id}] {t.theme}: {t.summary} (momentum={t.momentum})"
                for t in related
            )
            quotes = "\n".join(q.quote for q in problem.evidence_quotes)
            user = prompts.SYNTHESIZE_USER.format(
                pain_point=problem.pain_point,
                quotes=quotes,
                trends=trend_block or "(no trends retrieved)",
            )
            out = llm.structured(
                model=settings.model_synthesize,
                system=prompts.SYNTHESIZE_SYSTEM,
                user=user,
                output_schema=SynthesizeNodeOutput,
            )
            texts = [s.solution_text for s in out.solutions]
            vectors = embedder.embed(texts) if texts else []
            _append_solutions(problem, related, out.solutions, vectors)

    log.info("synthesize_complete", problems=len(problems), solutions=len(solutions))
    return {"candidate_solutions": solutions}
