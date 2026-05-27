"""Runtime configuration."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Default Gemini Flash — 2.0-flash has much higher free-tier limits than 2.5-flash (~20/day)
DEFAULT_GEMINI_MODEL = "gemini-2.0-flash"


def _package_fixtures_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "fixtures"


def _default_pipeline_cache_dir() -> Path:
    """Prefer repo recommendation_engine/.eg_cache over site-packages/.venv paths."""
    module = Path(__file__).resolve()
    for base in module.parents:
        if (base / "pyproject.toml").is_file() and base.name == "recommendation_engine":
            return base / ".eg_cache"
        if (base / "recommendation_engine" / "pyproject.toml").is_file():
            return base / "recommendation_engine" / ".eg_cache"
    return Path.cwd() / ".eg_cache"


def _discover_env_files() -> tuple[str, ...]:
    """Load .env from cwd ancestors and package tree (works for editable installs)."""
    seen: set[str] = set()
    found: list[str] = []

    def add(path: Path) -> None:
        env = path / ".env"
        if not env.is_file():
            return
        key = str(env.resolve())
        if key not in seen:
            seen.add(key)
            found.append(key)

    for base in (Path.cwd(), *Path.cwd().parents):
        add(base)

    module = Path(__file__).resolve()
    for base in module.parents:
        add(base)
        if base.name == "recommendation_engine" and (base / "pyproject.toml").is_file():
            add(base.parent)
            break

    return tuple(found) if found else (".env",)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_discover_env_files(),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    llm_mode: str = Field(default="live", alias="EG_LLM_MODE")
    google_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GOOGLE_API_KEY", "GEMINI_API_KEY"),
    )
    databricks_host: str | None = Field(default=None, alias="DATABRICKS_HOST")
    databricks_token: str | None = Field(
        default=None,
        validation_alias=AliasChoices("DATABRICKS_TOKEN", "DATABRICKS_API_TOKEN"),
    )
    databricks_embedding_endpoint: str = Field(
        default="databricks-gte-large-en",
        alias="EG_DATABRICKS_EMBEDDING_ENDPOINT",
    )

    model_extract: str = Field(default=DEFAULT_GEMINI_MODEL, alias="EG_MODEL_EXTRACT")
    model_synthesize: str = Field(default=DEFAULT_GEMINI_MODEL, alias="EG_MODEL_SYNTHESIZE")
    model_cluster: str = Field(default=DEFAULT_GEMINI_MODEL, alias="EG_MODEL_CLUSTER")
    model_rank_qualitative: str = Field(
        default=DEFAULT_GEMINI_MODEL, alias="EG_MODEL_RANK_QUALITATIVE"
    )
    model_writeup: str = Field(default=DEFAULT_GEMINI_MODEL, alias="EG_MODEL_WRITEUP")
    model_trend_enrichment: str = Field(
        default=DEFAULT_GEMINI_MODEL, alias="EG_MODEL_TREND_ENRICHMENT"
    )

    gemini_embedding_model: str = Field(
        default="gemini-embedding-001",
        alias="EG_GEMINI_EMBEDDING_MODEL",
    )
    embedding_dim: int = Field(default=1024, alias="EG_EMBEDDING_DIM")
    # databricks = Foundation Model embed endpoint | gemini = Google embed | auto = Databricks then Gemini
    embedding_provider: str = Field(
        default="databricks",
        alias="EG_EMBEDDING_PROVIDER",
    )
    embedding_batch_size: int = Field(default=32, alias="EG_EMBED_BATCH_SIZE")
    embedding_request_delay_seconds: float = Field(
        default=0.5, alias="EG_EMBED_DELAY_SECONDS"
    )

    s3_bucket: str = Field(default="market-trend-exp2", alias="EG_S3_BUCKET")
    s3_bronze_prefix: str = Field(default="bronze", alias="EG_S3_BRONZE_PREFIX")
    s3_gold_trend_prefix: str = Field(default="gold/trend_signals", alias="EG_S3_GOLD_TREND_PREFIX")
    s3_pipeline_results_prefix: str = Field(
        default="bronze/gold/pipeline_runs",
        alias="EG_S3_PIPELINE_RESULTS_PREFIX",
    )
    pipeline_results_s3_enabled: bool = Field(
        default=True,
        alias="EG_PIPELINE_RESULTS_S3",
    )
    aws_region: str = Field(default="us-east-1", alias="AWS_REGION")
    aws_profile: str | None = Field(default=None, alias="AWS_PROFILE")
    aws_endpoint_url: str | None = Field(default=None, alias="AWS_ENDPOINT_URL")

    data_source: str = Field(default="s3", alias="EG_DATA_SOURCE")
    # interviews: always S3 in production | community: s3 | fixtures (mock JSON)
    community_source: str = Field(default="s3", alias="EG_COMMUNITY_SOURCE")
    allow_fixtures: bool = Field(default=False, alias="EG_ALLOW_FIXTURES")
    enrich_bronze_trends: bool = Field(default=True, alias="EG_ENRICH_BRONZE_TRENDS")
    trend_enrichment_batch_size: int = Field(default=8, alias="EG_TREND_ENRICHMENT_BATCH_SIZE")
    llm_request_delay_seconds: float = Field(default=4.0, alias="EG_LLM_REQUEST_DELAY_SECONDS")
    max_transcript_chars: int = Field(default=14000, alias="EG_MAX_TRANSCRIPT_CHARS")
    # Cap sources and batch LLM stages to stay under Gemini free-tier quotas
    llm_conserve: bool = Field(default=False, alias="EG_LLM_CONSERVE")
    llm_max_requests_per_run: int | None = Field(
        default=None, alias="EG_LLM_MAX_REQUESTS_PER_RUN"
    )
    extract_max_interviews: int = Field(default=8, alias="EG_EXTRACT_MAX_INTERVIEWS")
    extract_max_community_posts: int = Field(default=5, alias="EG_EXTRACT_MAX_COMMUNITY")
    llm_batch_cluster: bool = Field(default=True, alias="EG_LLM_BATCH_CLUSTER")
    llm_batch_rank: bool = Field(default=True, alias="EG_LLM_BATCH_RANK")
    llm_batch_synthesize: bool = Field(default=True, alias="EG_LLM_BATCH_SYNTHESIZE")

    lookback_days: int = Field(default=14, alias="EG_LOOKBACK_DAYS")
    max_market_records: int = Field(default=200, alias="EG_MAX_MARKET_RECORDS")
    require_user_signals: bool = Field(default=False, alias="EG_REQUIRE_USER_SIGNALS")
    fixtures_dir: Path = Field(
        default_factory=_package_fixtures_dir,
        alias="EG_FIXTURES_DIR",
    )

    @property
    def use_mock_community(self) -> bool:
        return self.community_source.lower() == "fixtures"

    database_url: str | None = Field(default=None, alias="DATABASE_URL")
    gmail_client_id: str | None = Field(default=None, alias="GMAIL_CLIENT_ID")
    gmail_client_secret: str | None = Field(default=None, alias="GMAIL_CLIENT_SECRET")
    gmail_refresh_token: str | None = Field(default=None, alias="GMAIL_REFRESH_TOKEN")
    gmail_sender_email: str | None = Field(default=None, alias="GMAIL_SENDER_EMAIL")
    newsletter_default_recipient: str = Field(
        default="harshulc2001@gmail.com",
        alias="EG_NEWSLETTER_DEFAULT_TO",
    )
    top_missions: int = Field(default=10, alias="EG_TOP_MISSIONS")
    cluster_cosine_threshold: float = Field(default=0.85, alias="EG_CLUSTER_COSINE_THRESHOLD")
    trend_retrieval_k: int = Field(default=5, alias="EG_TREND_RETRIEVAL_K")
    weights_version: str = Field(default="v1.0", alias="EG_WEIGHTS_VERSION")
    prompt_version: str = Field(default="v1.0", alias="EG_PROMPT_VERSION")
    git_sha: str = Field(default="dev", alias="EG_GIT_SHA")

    pipeline_cache_enabled: bool = Field(default=True, alias="EG_PIPELINE_CACHE")
    pipeline_force_rerun: bool = Field(default=False, alias="EG_PIPELINE_FORCE_RERUN")
    pipeline_cache_dir: Path = Field(
        default_factory=lambda: _default_pipeline_cache_dir(),
        alias="EG_PIPELINE_CACHE_DIR",
    )

    @property
    def use_s3(self) -> bool:
        return self.data_source.lower() == "s3"

    @property
    def use_live_llm(self) -> bool:
        return self.llm_mode.lower() == "live" and bool(self.google_api_key)

    @property
    def has_databricks_embeddings(self) -> bool:
        return bool(self.databricks_host and self.databricks_token)

    @property
    def use_databricks_embeddings(self) -> bool:
        provider = self.embedding_provider.lower()
        if provider == "gemini":
            return False
        if provider == "databricks":
            return self.has_databricks_embeddings
        # auto
        return self.has_databricks_embeddings


@lru_cache
def get_settings() -> Settings:
    return Settings()
