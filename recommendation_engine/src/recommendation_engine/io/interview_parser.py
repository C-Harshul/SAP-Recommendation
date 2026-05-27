"""Parse interview JSON from S3 — canonical schema or Experience Garage transcript blocks."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import PurePosixPath

from recommendation_engine.models.schemas import InterviewBronze


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _duration_minutes(raw: str | None) -> int | None:
    if not raw:
        return None
    match = re.search(r"(\d+)\s*min", str(raw), re.I)
    return int(match.group(1)) if match else None


def _blocks_to_transcript(blocks: list[dict]) -> str:
    lines: list[str] = []
    for block in blocks:
        block_name = block.get("name", "")
        if block_name:
            lines.append(f"[{block_name}]")
        for turn in block.get("turns", []):
            speaker = turn.get("speaker") or turn.get("speaker_code") or "unknown"
            text = (turn.get("text") or "").strip()
            if text:
                lines.append(f"{speaker}: {text}")
    return "\n\n".join(lines)


def parse_interview_document(item: dict, s3_key: str) -> InterviewBronze | None:
    """
    Support:
    - Plan schema: interview_id, participant_role, transcript, timestamp, ...
    - EG transcript export: metadata + blocks[].turns[]
    """
    interview_id = item.get("interview_id")
    transcript = item.get("transcript") or item.get("notes") or item.get("body") or ""

    if interview_id and transcript.strip():
        return InterviewBronze(
            interview_id=str(interview_id),
            participant_role=item.get("participant_role", "unknown"),
            timestamp=_parse_dt(item.get("timestamp")) or datetime.now(),
            transcript=transcript.strip(),
            tags=item.get("tags", []),
            interviewer=item.get("interviewer"),
            duration_minutes=item.get("duration_minutes"),
        )

    blocks = item.get("blocks")
    if not blocks:
        return None

    transcript_text = _blocks_to_transcript(blocks)
    if not transcript_text.strip():
        return None

    meta = item.get("metadata") or {}
    participant = meta.get("participant") or {}
    if isinstance(participant, dict):
        role = (
            participant.get("role")
            or participant.get("persona_type")
            or participant.get("name")
            or "unknown"
        )
    else:
        role = str(participant) if participant else "unknown"

    stem = PurePosixPath(s3_key).stem
    return InterviewBronze(
        interview_id=stem,
        participant_role=str(role),
        timestamp=_parse_dt(item.get("timestamp")) or datetime.now(),
        transcript=transcript_text,
        tags=item.get("tags", []) or ([participant.get("persona_type")] if isinstance(participant, dict) and participant.get("persona_type") else []),
        interviewer=meta.get("moderator"),
        duration_minutes=_duration_minutes(meta.get("duration")),
    )
