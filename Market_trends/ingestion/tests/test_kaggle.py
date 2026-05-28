"""Kaggle builder connector tests."""

from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from ingestion.connectors.builder.kaggle import KaggleConnector


def _inject_kaggle_mock(mock_api: MagicMock) -> None:
    mod = ModuleType("kaggle.api.kaggle_api_extended")
    mod.KaggleApi = MagicMock(return_value=mock_api)  # type: ignore[attr-defined]
    sys.modules["kaggle.api.kaggle_api_extended"] = mod


@pytest.fixture
def kaggle_connector(s3_setup: dict) -> KaggleConnector:
    conn = KaggleConnector(
        writer=s3_setup["writer"],
        state=s3_setup["state"],
        rate_limiters=s3_setup["limiters"],
        source_config={
            "tags": ["machine-learning"],
            "content_types": ["competition"],
        },
    )
    conn.source_id = "kaggle"
    conn.category = "builder"
    return conn


def test_fetch_competitions(kaggle_connector: KaggleConnector) -> None:
    mock_comp = SimpleNamespace(
        ref="titanic",
        title="Titanic",
        category="Getting Started",
        deadline="2030-01-01T00:00:00Z",
    )
    mock_api = MagicMock()
    mock_api.competitions_list.return_value = [mock_comp]
    mock_api.dataset_list.return_value = []
    mock_api.kernels_list.return_value = []

    _inject_kaggle_mock(mock_api)
    with patch.dict("os.environ", {"KAGGLE_USERNAME": "u", "KAGGLE_KEY": "k"}):
        items = list(kaggle_connector.fetch(since=None))

    assert len(items) == 1
    assert items[0]["external_id"] == "competition:titanic"
    assert items[0]["raw"]["content_type"] == "competition"


def test_run_idempotent_dedup(kaggle_connector: KaggleConnector, s3_setup: dict) -> None:
    mock_comp = SimpleNamespace(
        ref="titanic",
        title="Titanic",
        category="Getting Started",
        deadline="2030-01-01T00:00:00Z",
    )
    mock_api = MagicMock()
    mock_api.competitions_list.return_value = [mock_comp]
    mock_api.dataset_list.return_value = []
    mock_api.kernels_list.return_value = []

    _inject_kaggle_mock(mock_api)
    with patch.dict("os.environ", {"KAGGLE_USERNAME": "u", "KAGGLE_KEY": "k"}):
        r1 = kaggle_connector.run()
        r2 = kaggle_connector.run()

    assert r1.records_ingested == 1
    assert r2.records_ingested == 0
    cursor = s3_setup["state"].load("kaggle")
    assert "competition:titanic" in cursor.last_external_ids
