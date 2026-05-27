"""Content and config fingerprints for pipeline cache invalidation."""

from __future__ import annotations

import hashlib
import json

from recommendation_engine.config.settings import Settings
from recommendation_engine.models.schemas import CommunityBronze, InterviewBronze, TrendSignal


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def interview_content_hash(interview: InterviewBronze) -> str:
    payload = json.dumps(
        {
            "id": interview.interview_id,
            "role": interview.participant_role,
            "transcript": interview.transcript,
            "tags": sorted(interview.tags),
        },
        sort_keys=True,
    )
    return _sha(payload)


def community_content_hash(post: CommunityBronze) -> str:
    payload = json.dumps(
        {
            "id": post.post_id,
            "role": post.author_role,
            "body": post.body,
            "upvotes": post.upvote_count,
            "tags": sorted(post.tags),
        },
        sort_keys=True,
    )
    return _sha(payload)


def trend_content_hash(trend: TrendSignal) -> str:
    payload = json.dumps(
        {
            "id": trend.trend_id,
            "theme": trend.theme,
            "summary": trend.summary,
            "momentum": str(trend.momentum),
            "urls": sorted(trend.evidence_urls),
        },
        sort_keys=True,
    )
    return _sha(payload)


def config_fingerprint(settings: Settings) -> str:
    """Bump when ranking/extraction logic or models change."""
    parts = {
        "prompt_version": settings.prompt_version,
        "weights_version": settings.weights_version,
        "git_sha": settings.git_sha,
        "cluster_threshold": settings.cluster_cosine_threshold,
        "trend_k": settings.trend_retrieval_k,
        "top_missions": settings.top_missions,
        "embedding_provider": settings.embedding_provider,
        "model_extract": settings.model_extract,
        "model_synthesize": settings.model_synthesize,
        "model_cluster": settings.model_cluster,
        "model_rank": settings.model_rank_qualitative,
        "model_writeup": settings.model_writeup,
        "lookback_days": settings.lookback_days,
        "max_market_records": settings.max_market_records,
        "community_source": settings.community_source,
        "data_source": settings.data_source,
    }
    return _sha(json.dumps(parts, sort_keys=True))


def input_fingerprint(
    interviews: list[InterviewBronze],
    community: list[CommunityBronze],
    trends: list[TrendSignal],
    settings: Settings,
) -> str:
    lines: list[str] = []
    for i in sorted(interviews, key=lambda x: x.interview_id):
        lines.append(f"interview:{i.interview_id}:{interview_content_hash(i)}")
    for p in sorted(community, key=lambda x: x.post_id):
        lines.append(f"community:{p.post_id}:{community_content_hash(p)}")
    for t in sorted(trends, key=lambda x: x.trend_id):
        lines.append(f"trend:{t.trend_id}:{trend_content_hash(t)}")
    lines.append(f"config:{config_fingerprint(settings)}")
    lines.append(f"bucket:{settings.s3_bucket}")
    lines.append(f"lookback:{settings.lookback_days}")
    return _sha("\n".join(lines))


def extract_stage_fingerprint(settings: Settings) -> str:
    """Invalidate per-source extract cache when extract model/prompt changes."""
    return _sha(
        json.dumps(
            {
                "prompt_version": settings.prompt_version,
                "model_extract": settings.model_extract,
                "max_transcript_chars": settings.max_transcript_chars,
            },
            sort_keys=True,
        )
    )
