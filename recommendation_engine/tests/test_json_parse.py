import pytest

from recommendation_engine.llm.json_parse import parse_json_response


def test_parse_fenced_json():
    text = 'Here is data:\n```json\n{"ideas": []}\n```'
    assert parse_json_response(text) == {"ideas": []}


def test_repair_truncated_ideas_array():
    truncated = """{
  "ideas": [
    {
      "pain_point": "Onboarding is slow",
      "proposed_solution": null,
      "evidence_quotes": ["took three weeks"],
      "sentiment": "negative",
"""
    result = parse_json_response(truncated)
    assert len(result["ideas"]) == 1
    assert result["ideas"][0]["pain_point"] == "Onboarding is slow"


def test_salvage_multiple_complete_objects():
    text = """{"ideas": [
      {"pain_point": "a", "proposed_solution": null, "evidence_quotes": ["q1"], "sentiment": "neutral", "specificity": "vague"},
      {"pain_point": "b", "proposed_solution": "x", "evidence_quotes": ["q2"], "sentiment": "positive", "specificity": "specific"},
      {"pain_point": "incomplete", "proposed_solution": null, "evidence_quotes": ["q3"], "sentiment": "neutral",
    """
    result = parse_json_response(text)
    assert len(result["ideas"]) == 2
