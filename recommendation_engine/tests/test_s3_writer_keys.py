from recommendation_engine.config.settings import Settings
from recommendation_engine.io.s3_writer import (
    latest_pointer_key,
    latest_ranked_missions_key,
    run_snapshot_key,
)


def test_pipeline_s3_keys():
    settings = Settings(EG_S3_BUCKET="market-trend-exp2")
    fp = "abc" * 16
    assert run_snapshot_key(fp, settings) == f"bronze/gold/pipeline_runs/runs/{fp}.json"
    assert latest_pointer_key(settings) == "bronze/gold/pipeline_runs/latest_run.json"
    assert (
        latest_ranked_missions_key(settings)
        == "bronze/gold/pipeline_runs/latest_ranked_missions.json"
    )
