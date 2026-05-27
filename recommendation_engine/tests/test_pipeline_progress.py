from recommendation_engine.api.pipeline_progress import PipelineProgressTracker


def test_progress_percent_advances():
    p = PipelineProgressTracker()
    p.reset()
    assert p.progress_percent == 0
    p.begin_step("validate")
    p.complete_step("validate")
    assert p.progress_percent == 10
    p.begin_step("load")
    p.complete_step("load")
    assert p.progress_percent == 20
