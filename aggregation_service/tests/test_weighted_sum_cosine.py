"""Tests for aggregate (weighted sum) and cosine similarity."""
import numpy as np

from services.similarity_service.aggregation.weighted_sum import aggregate
from services.similarity_service.utils import cosine, parse_embedding

# ---------------------------------------------------------------------------
# aggregate
# ---------------------------------------------------------------------------

def test_aggregate_weighted_sum():
    scores = {"title": 0.8, "semantic": 0.6}
    weights = {"title": 0.7, "semantic": 0.3}
    expected = 0.8 * 0.7 + 0.6 * 0.3
    assert abs(aggregate(scores, weights) - expected) < 1e-9


def test_aggregate_missing_weight_treated_as_zero():
    scores = {"title": 0.8, "extra": 0.5}
    weights = {"title": 0.7}
    assert abs(aggregate(scores, weights) - 0.8 * 0.7) < 1e-9


def test_aggregate_empty_scores():
    assert aggregate({}, {"title": 0.7}) == 0.0


def test_aggregate_all_weights_zero():
    scores = {"title": 0.8, "semantic": 0.6}
    assert aggregate(scores, {}) == 0.0


def test_aggregate_single_channel():
    assert abs(aggregate({"title": 1.0}, {"title": 0.5}) - 0.5) < 1e-9


# ---------------------------------------------------------------------------
# parse_embedding
# ---------------------------------------------------------------------------

def test_parse_embedding_ndarray_passthrough():
    v = np.array([1.0, 2.0, 3.0])
    result = parse_embedding(v)
    assert isinstance(result, np.ndarray)
    assert list(result) == [1.0, 2.0, 3.0]


def test_parse_embedding_from_string():
    result = parse_embedding("[1.0, 0.0, 0.0]")
    assert isinstance(result, np.ndarray)
    assert abs(result[0] - 1.0) < 1e-6


def test_parse_embedding_from_list():
    result = parse_embedding([0.5, 0.5])
    assert isinstance(result, np.ndarray)


# ---------------------------------------------------------------------------
# cosine
# ---------------------------------------------------------------------------

def test_cosine_identical_vectors():
    v = np.array([1.0, 0.0, 0.0])
    assert abs(cosine(v, v) - 1.0) < 1e-6


def test_cosine_orthogonal_vectors():
    a = np.array([1.0, 0.0])
    b = np.array([0.0, 1.0])
    assert abs(cosine(a, b) - 0.0) < 1e-6


def test_cosine_opposite_vectors():
    a = np.array([1.0, 0.0])
    b = np.array([-1.0, 0.0])
    assert abs(cosine(a, b) - (-1.0)) < 1e-6


def test_cosine_none_a_returns_zero():
    assert cosine(None, np.array([1.0, 0.0])) == 0.0


def test_cosine_none_b_returns_zero():
    assert cosine(np.array([1.0, 0.0]), None) == 0.0


def test_cosine_both_none_returns_zero():
    assert cosine(None, None) == 0.0


def test_cosine_string_input_parsed():
    v = np.array([1.0, 0.0, 0.0])
    assert abs(cosine("[1.0, 0.0, 0.0]", v) - 1.0) < 1e-6


def test_cosine_symmetry():
    a = np.array([0.6, 0.8])
    b = np.array([0.8, 0.6])
    assert abs(cosine(a, b) - cosine(b, a)) < 1e-9
