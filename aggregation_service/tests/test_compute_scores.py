"""Tests for ComputeScores.compute_channel_scores_batch and compute_final_scores_batch."""
from unittest.mock import MagicMock
from services.similarity_service.compute_scores import ComputeScores


def _channel(name, scores):
    ch = MagicMock()
    ch.name = name
    ch.score_batch.return_value = scores
    return ch


# ---------------------------------------------------------------------------
# compute_channel_scores_batch
# ---------------------------------------------------------------------------

def test_combines_two_channels_into_row():
    ch1 = _channel("title", [0.8, 0.7])
    ch2 = _channel("semantic", [0.6, 0.5])
    scorer = ComputeScores(channels=[ch1, ch2])

    results = scorer.compute_channel_scores_batch([("a", "b"), ("c", "d")])

    assert results[0] == {"title": 0.8, "semantic": 0.6}
    assert results[1] == {"title": 0.7, "semantic": 0.5}


def test_all_zero_scores_returns_none():
    ch = _channel("title", [0.0, 0.8])
    scorer = ComputeScores(channels=[ch])

    results = scorer.compute_channel_scores_batch([("a", "b"), ("c", "d")])

    assert results[0] is None   # all zeros → None
    assert results[1] is not None


def test_empty_pairs_returns_empty():
    scorer = ComputeScores(channels=[_channel("title", [])])
    assert scorer.compute_channel_scores_batch([]) == []


def test_no_channels_all_zeros_returns_none():
    scorer = ComputeScores(channels=[])
    # row = {} → all() on empty is True → None
    results = scorer.compute_channel_scores_batch([("a", "b")])
    assert results[0] is None


def test_channel_score_batch_called_with_pairs():
    ch = _channel("title", [0.5])
    scorer = ComputeScores(channels=[ch])
    pairs = [("x", "y")]
    scorer.compute_channel_scores_batch(pairs)
    ch.score_batch.assert_called_once_with(pairs)


# ---------------------------------------------------------------------------
# compute_final_scores_batch
# ---------------------------------------------------------------------------

def test_final_scores_weighted_sum():
    scorer = ComputeScores(weights={"title": 0.7, "semantic": 0.3})
    channel_scores_batch = [{"title": 0.8, "semantic": 0.6}]
    results = scorer.compute_final_scores_batch(channel_scores_batch)
    expected = 0.8 * 0.7 + 0.6 * 0.3
    assert abs(results[0] - expected) < 1e-9


def test_final_scores_none_channel_scores_returns_zero():
    scorer = ComputeScores(weights={"title": 0.7})
    results = scorer.compute_final_scores_batch([None])
    assert results[0] == 0.0


def test_final_scores_mixed_none_and_valid():
    scorer = ComputeScores(weights={"title": 1.0})
    results = scorer.compute_final_scores_batch([None, {"title": 0.5}, None])
    assert results[0] == 0.0
    assert abs(results[1] - 0.5) < 1e-9
    assert results[2] == 0.0