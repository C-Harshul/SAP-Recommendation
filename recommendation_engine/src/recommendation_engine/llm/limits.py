"""Caps on LLM-heavy pipeline inputs."""

from __future__ import annotations

from recommendation_engine.config.settings import Settings


def extract_source_limits(settings: Settings) -> tuple[int, int]:
    max_interviews = settings.extract_max_interviews
    max_community = settings.extract_max_community_posts
    if settings.llm_conserve:
        max_interviews = min(max_interviews, 3)
        max_community = min(max_community, 2)
    return max_interviews, max_community


def writeup_limit(settings: Settings) -> int:
    top = settings.top_missions
    if settings.llm_conserve:
        return min(top, 5)
    return top
