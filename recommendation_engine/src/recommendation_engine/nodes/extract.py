"""Stage 2: Extract quote-grounded ideas from interviews and community posts."""

from __future__ import annotations

import uuid

import structlog

from recommendation_engine.config.settings import get_settings
from recommendation_engine.io.embeddings import EmbeddingClient
from recommendation_engine.io.fingerprints import community_content_hash, interview_content_hash
from recommendation_engine.io.source_cache import get_cached_extract, save_cached_extract
from recommendation_engine.llm import prompts
from recommendation_engine.llm.client import LLMClient
from recommendation_engine.llm.limits import extract_source_limits
from recommendation_engine.models.schemas import EvidenceQuote, ExtractedIdea, ExtractNodeOutput
from recommendation_engine.models.state import RecommendationState

log = structlog.get_logger()


def _truncate_text(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    half = max_chars // 2
    return (
        text[:half]
        + "\n\n[... middle of transcript omitted for token limits — preserve quotes from shown sections ...]\n\n"
        + text[-half:]
    )


def _to_extracted(
    out: ExtractNodeOutput,
    *,
    source_type: str,
    source_id: str,
    embedder: EmbeddingClient,
) -> list[ExtractedIdea]:
    results: list[ExtractedIdea] = []
    texts = [f"{i.pain_point} {i.proposed_solution or ''}" for i in out.ideas]
    vectors = embedder.embed(texts) if texts else []

    for idx, item in enumerate(out.ideas):
        idea_id = f"{source_type}-{source_id}-{uuid.uuid4().hex[:8]}"
        quotes = [
            EvidenceQuote(quote=q, source_type=source_type, source_id=source_id)
            for q in item.evidence_quotes
        ]
        results.append(
            ExtractedIdea(
                idea_id=idea_id,
                source_type=source_type,
                source_id=source_id,
                pain_point=item.pain_point,
                proposed_solution=item.proposed_solution,
                evidence_quotes=quotes,
                sentiment=item.sentiment,
                specificity=item.specificity,
                embedding=vectors[idx] if idx < len(vectors) else None,
                is_problem_only=item.proposed_solution is None,
            )
        )
    return results


def _extract_source(
    *,
    source_type: str,
    source_id: str,
    content_hash: str,
    user_prompt: str,
    llm: LLMClient,
    embedder: EmbeddingClient,
    settings,
) -> tuple[list[ExtractedIdea], bool]:
    cached = get_cached_extract(
        source_type=source_type,
        source_id=source_id,
        content_hash=content_hash,
        settings=settings,
    )
    if cached is not None:
        return cached, True

    out = llm.structured(
        model=settings.model_extract,
        system=prompts.EXTRACT_SYSTEM,
        user=user_prompt,
        output_schema=ExtractNodeOutput,
        max_tokens=8192,
    )
    extracted = _to_extracted(
        out, source_type=source_type, source_id=source_id, embedder=embedder
    )
    save_cached_extract(
        source_type=source_type,
        source_id=source_id,
        content_hash=content_hash,
        ideas=extracted,
        settings=settings,
    )
    return extracted, False


def extract_node(state: RecommendationState) -> dict:
    settings = get_settings()
    llm = LLMClient(settings)
    embedder = EmbeddingClient(settings)

    ideas: list[ExtractedIdea] = []
    cache_hits = 0

    max_chars = settings.max_transcript_chars
    max_interviews, max_community = extract_source_limits(settings)
    interviews = list(state.get("interviews", []))[:max_interviews]
    posts = list(state.get("community_posts", []))[:max_community]
    if len(interviews) < len(state.get("interviews", [])) or len(posts) < len(
        state.get("community_posts", [])
    ):
        log.info(
            "extract_sources_capped",
            interviews=len(interviews),
            community=len(posts),
            max_interviews=max_interviews,
            max_community=max_community,
            conserve=settings.llm_conserve,
        )

    for interview in interviews:
        content_hash = interview_content_hash(interview)
        transcript = _truncate_text(interview.transcript, max_chars)
        if len(interview.transcript) > max_chars:
            log.info(
                "transcript_truncated",
                interview_id=interview.interview_id,
                original_chars=len(interview.transcript),
                sent_chars=len(transcript),
            )
        batch, from_cache = _extract_source(
            source_type="interview",
            source_id=interview.interview_id,
            content_hash=content_hash,
            user_prompt=prompts.EXTRACT_USER_INTERVIEW.format(
                role=interview.participant_role,
                interview_id=interview.interview_id,
                transcript=transcript,
            ),
            llm=llm,
            embedder=embedder,
            settings=settings,
        )
        ideas.extend(batch)
        if from_cache:
            cache_hits += 1

    for post in posts:
        content_hash = community_content_hash(post)
        batch, from_cache = _extract_source(
            source_type="community",
            source_id=post.post_id,
            content_hash=content_hash,
            user_prompt=prompts.EXTRACT_USER_COMMUNITY.format(
                role=post.author_role,
                post_id=post.post_id,
                upvotes=post.upvote_count,
                body=post.body,
            ),
            llm=llm,
            embedder=embedder,
            settings=settings,
        )
        ideas.extend(batch)
        if from_cache:
            cache_hits += 1

    problem_only = [i for i in ideas if i.is_problem_only]
    with_solution = [i for i in ideas if not i.is_problem_only]

    log.info(
        "extract_complete",
        total=len(ideas),
        problem_only=len(problem_only),
        with_solution=len(with_solution),
        source_cache_hits=cache_hits,
    )
    return {
        "extracted_ideas": with_solution,
        "extracted_problems": problem_only,
    }
