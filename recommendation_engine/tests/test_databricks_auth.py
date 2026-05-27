from recommendation_engine.io.databricks_embeddings import (
    DatabricksEmbeddingAuthError,
    is_auth_or_scope_error,
)


def test_auth_scope_detection():
    exc = DatabricksEmbeddingAuthError("model-serving scope required")
    assert is_auth_or_scope_error(exc)


def test_403_message_detection():
    exc = Exception('Databricks embed HTTP 403: {"message":"model-serving"}')
    assert is_auth_or_scope_error(exc)
