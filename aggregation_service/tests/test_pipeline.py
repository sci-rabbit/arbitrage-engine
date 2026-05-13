"""Tests for SimilarityPipeline.run."""
from unittest.mock import MagicMock
from services.similarity_service.stages.pipeline import SimilarityPipeline
from services.similarity_service.stages.dataclass import PairItem


def _market(mid="m1"):
    m = MagicMock()
    m.platform_market_id = mid
    return m


def _item(a_id="a", b_id="b"):
    return PairItem(
        a=_market(a_id),
        b=_market(b_id),
        row={"min_distance": 0.3},
        ce_score=0.9,
    )


def _pass_stage(name="pass"):
    stage = MagicMock()
    stage.name = name
    stage.process_batch.side_effect = lambda items: (items, [])
    return stage


def _fail_stage(name="fail"):
    stage = MagicMock()
    stage.name = name
    stage.process_batch.side_effect = lambda items: (
        [],
        [{"a_market_id": it.a.platform_market_id, "b_market_id": it.b.platform_market_id} for it in items],
    )
    return stage


def test_no_stages_yields_all_items_as_valid():
    pipeline = SimilarityPipeline(stages=[])
    items = [_item("a", "b"), _item("c", "d")]
    results = list(pipeline.run(items))
    valid = [r for r in results if "valid_pairs" in r]
    assert len(valid) == 1
    assert len(valid[0]["valid_pairs"]) == 2


def test_pass_stage_yields_valid_result():
    pipeline = SimilarityPipeline(stages=[_pass_stage()])
    items = [_item()]
    results = list(pipeline.run(items))
    valid = [r for r in results if "valid_pairs" in r]
    assert len(valid) == 1
    assert valid[0]["valid_pairs"] == items


def test_fail_stage_yields_invalid_with_correct_ids():
    pipeline = SimilarityPipeline(stages=[_fail_stage("gate")])
    items = [_item("mkt-a", "mkt-b")]
    results = list(pipeline.run(items))
    invalid = [r for r in results if "invalid_pairs" in r]
    assert len(invalid) == 1
    assert invalid[0]["stage"] == "gate"
    assert invalid[0]["invalid_pairs"][0]["a_market_id"] == "mkt-a"


def test_empty_batch_skips_subsequent_stages():
    stage1 = _fail_stage()  # drains all items
    stage2 = MagicMock()
    stage2.name = "stage2"

    pipeline = SimilarityPipeline(stages=[stage1, stage2])
    list(pipeline.run([_item()]))

    stage2.process_batch.assert_not_called()


def test_pipeline_splits_into_batches():
    stage = _pass_stage()
    items = [_item(str(i), str(i + 100)) for i in range(7)]
    pipeline = SimilarityPipeline(stages=[stage], batch_size=3)
    list(pipeline.run(items))
    # ceil(7/3) = 3 batches
    assert stage.process_batch.call_count == 3


def test_mixed_stage_separates_passed_and_invalid():
    def mixed(items):
        passed = items[:1]
        invalid = [{"a_market_id": it.a.platform_market_id, "b_market_id": it.b.platform_market_id} for it in items[1:]]
        return passed, invalid

    stage = MagicMock()
    stage.name = "mixed"
    stage.process_batch.side_effect = mixed

    pipeline = SimilarityPipeline(stages=[stage])
    items = [_item("a", "b"), _item("c", "d"), _item("e", "f")]
    results = list(pipeline.run(items))

    invalid_batches = [r for r in results if "invalid_pairs" in r]
    valid_batches = [r for r in results if "valid_pairs" in r]
    assert len(invalid_batches) == 1
    assert len(invalid_batches[0]["invalid_pairs"]) == 2
    assert len(valid_batches) == 1


def test_empty_input_yields_nothing():
    pipeline = SimilarityPipeline(stages=[_pass_stage()])
    results = list(pipeline.run([]))
    assert results == []