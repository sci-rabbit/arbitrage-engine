"""Tests for HardGateStage, ChannelScoreStage, FinalScoreStage, NLIGateStage."""
from unittest.mock import MagicMock, patch

from services.similarity_service.stages.channelscores_stage import ChannelScoreStage
from services.similarity_service.stages.dataclass import PairItem
from services.similarity_service.stages.finalscores_stage import FinalScoreStage
from services.similarity_service.stages.hardgates_stage import HardGateStage
from services.similarity_service.stages.nli_gate_stage import NLIGateStage


def _market(mid="m1"):
    m = MagicMock()
    m.platform_market_id = mid
    m.normalized_title = "test market"
    return m


def _item(a_id="a", b_id="b", ce_score=0.9, channel_scores=None):
    return PairItem(
        a=_market(a_id),
        b=_market(b_id),
        row={"min_distance": 0.3},
        ce_score=ce_score,
        channel_scores=channel_scores,
    )


# ---------------------------------------------------------------------------
# HardGateStage
# ---------------------------------------------------------------------------

def test_hard_gate_all_pass():
    with patch("services.similarity_service.stages.hardgates_stage.hard_gate_batch", return_value=[True, True]):
        stage = HardGateStage()
        passed, invalid = stage.process_batch([_item("a", "b"), _item("c", "d")])
    assert len(passed) == 2
    assert len(invalid) == 0


def test_hard_gate_all_fail():
    with patch("services.similarity_service.stages.hardgates_stage.hard_gate_batch", return_value=[False, False]):
        stage = HardGateStage()
        passed, invalid = stage.process_batch([_item("a", "b"), _item("c", "d")])
    assert len(passed) == 0
    assert len(invalid) == 2
    assert invalid[0]["a_market_id"] == "a"
    assert invalid[1]["a_market_id"] == "c"


def test_hard_gate_mixed():
    with patch("services.similarity_service.stages.hardgates_stage.hard_gate_batch", return_value=[True, False, True]):
        stage = HardGateStage()
        passed, invalid = stage.process_batch([_item("a", "b"), _item("c", "d"), _item("e", "f")])
    assert len(passed) == 2
    assert len(invalid) == 1
    assert invalid[0]["a_market_id"] == "c"


def test_hard_gate_tracks_counters():
    with patch("services.similarity_service.stages.hardgates_stage.hard_gate_batch", return_value=[True, False]):
        stage = HardGateStage()
        stage.process_batch([_item(), _item("c", "d")])
    assert stage.total == 2
    assert stage.failed == 1


# ---------------------------------------------------------------------------
# ChannelScoreStage
# ---------------------------------------------------------------------------

def test_channel_score_attaches_scores():
    scorer = MagicMock()
    scorer.compute_channel_scores_batch.return_value = [
        {"title": 0.8, "semantic": 0.7},
        {"title": 0.6, "semantic": 0.5},
    ]
    stage = ChannelScoreStage(scorer=scorer)
    passed, invalid = stage.process_batch([_item("a", "b"), _item("c", "d")])
    assert len(passed) == 2
    assert passed[0].channel_scores == {"title": 0.8, "semantic": 0.7}
    assert passed[1].channel_scores == {"title": 0.6, "semantic": 0.5}


def test_channel_score_rejects_none_scores():
    scorer = MagicMock()
    scorer.compute_channel_scores_batch.return_value = [None, {"title": 0.8}]
    stage = ChannelScoreStage(scorer=scorer)
    passed, invalid = stage.process_batch([_item("a", "b"), _item("c", "d")])
    assert len(passed) == 1
    assert len(invalid) == 1
    assert invalid[0]["a_market_id"] == "a"


def test_channel_score_tracks_counters():
    scorer = MagicMock()
    scorer.compute_channel_scores_batch.return_value = [None, {"title": 0.9}]
    stage = ChannelScoreStage(scorer=scorer)
    stage.process_batch([_item(), _item("c", "d")])
    assert stage.total == 2
    assert stage.failed == 1


# ---------------------------------------------------------------------------
# FinalScoreStage
# ---------------------------------------------------------------------------

def test_final_score_passes_above_threshold():
    stage = FinalScoreStage(threshold=0.7, weights={"title": 0.7, "semantic": 0.3})
    item = _item(channel_scores={"title": 0.9, "semantic": 0.8})
    passed, invalid = stage.process_batch([item])
    assert len(passed) == 1
    assert passed[0]["final_score"] >= 0.7


def test_final_score_rejects_below_threshold():
    stage = FinalScoreStage(threshold=0.7, weights={"title": 0.7, "semantic": 0.3})
    item = _item(channel_scores={"title": 0.2, "semantic": 0.2})
    passed, invalid = stage.process_batch([item])
    assert len(passed) == 0
    assert len(invalid) == 1
    assert invalid[0]["a_market_id"] == "a"


def test_final_score_result_has_expected_fields():
    stage = FinalScoreStage(threshold=0.0, weights={"title": 0.7, "semantic": 0.3})
    item = _item("a", "b", channel_scores={"title": 0.8, "semantic": 0.6})
    passed, _ = stage.process_batch([item])
    result = passed[0]
    for field in ("final_score", "channels", "min_distance", "cross_encoder", "a_id"):
        assert field in result


def test_final_score_tracks_counters():
    stage = FinalScoreStage(threshold=0.8, weights={"title": 0.7, "semantic": 0.3})
    items = [
        _item("a", "b", channel_scores={"title": 0.9, "semantic": 0.9}),
        _item("c", "d", channel_scores={"title": 0.1, "semantic": 0.1}),
    ]
    stage.process_batch(items)
    assert stage.total == 2
    assert stage.filtered == 1


# ---------------------------------------------------------------------------
# NLIGateStage
# ---------------------------------------------------------------------------

def test_nli_gate_empty_input():
    stage = NLIGateStage()
    passed, invalid = stage.process_batch([])
    assert passed == []
    assert invalid == []


def test_nli_gate_passes_low_entailment():
    with patch(
        "services.similarity_service.stages.nli_gate_stage.entailment_scores_batch",
        side_effect=[[0.1], [0.1]],  # fwd=0.1, bwd=0.1
    ):
        stage = NLIGateStage(threshold=0.5)
        passed, invalid = stage.process_batch([_item("a", "b")])
    assert len(passed) == 1
    assert len(invalid) == 0


def test_nli_gate_rejects_high_forward_entailment():
    with patch(
        "services.similarity_service.stages.nli_gate_stage.entailment_scores_batch",
        side_effect=[[0.9], [0.1]],  # fwd=0.9 ≥ threshold → reject
    ):
        stage = NLIGateStage(threshold=0.5)
        passed, invalid = stage.process_batch([_item("a", "b")])
    assert len(passed) == 0
    assert len(invalid) == 1


def test_nli_gate_rejects_high_backward_entailment():
    with patch(
        "services.similarity_service.stages.nli_gate_stage.entailment_scores_batch",
        side_effect=[[0.1], [0.8]],  # bwd=0.8 ≥ threshold → reject
    ):
        stage = NLIGateStage(threshold=0.5)
        passed, invalid = stage.process_batch([_item("a", "b")])
    assert len(passed) == 0
    assert len(invalid) == 1


def test_nli_gate_tracks_counters():
    with patch(
        "services.similarity_service.stages.nli_gate_stage.entailment_scores_batch",
        side_effect=[[0.9, 0.1], [0.1, 0.1]],
    ):
        stage = NLIGateStage(threshold=0.5)
        stage.process_batch([_item("a", "b"), _item("c", "d")])
    assert stage.total == 2
    assert stage.failed == 1
