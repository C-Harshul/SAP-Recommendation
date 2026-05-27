from recommendation_engine.io.databricks_embeddings import _parse_embeddings_payload


def test_parse_openai_style_batch():
    payload = {
        "data": [
            {"embedding": [0.1, 0.2], "index": 1},
            {"embedding": [0.3, 0.4], "index": 0},
        ]
    }
    vectors = _parse_embeddings_payload(payload)
    assert len(vectors) == 2
    assert vectors[0] == [0.3, 0.4]
    assert vectors[1] == [0.1, 0.2]
