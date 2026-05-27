import json
from pathlib import Path

from recommendation_engine.io.interview_parser import parse_interview_document


def test_parse_blocks_transcript():
    raw = Path(__file__).resolve().parents[1] / "src/recommendation_engine/fixtures/sample_interview_blocks.json"
    if not raw.exists():
        item = {
            "metadata": {
                "moderator": "Research team",
                "participant": {"role": "Developer", "persona_type": "Power User"},
                "duration": "31 min",
            },
            "blocks": [
                {
                    "name": "Warm-up",
                    "turns": [
                        {"speaker": "participant", "text": "We need faster onboarding."},
                    ],
                }
            ],
        }
    else:
        item = json.loads(raw.read_text())
    result = parse_interview_document(item, "bronze/interviews/dt=2026-05-24/Interview1_Test.json")
    assert result is not None
    assert "onboarding" in result.transcript.lower()
    assert result.interview_id == "Interview1_Test"
