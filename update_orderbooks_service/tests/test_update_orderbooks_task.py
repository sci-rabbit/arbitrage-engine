"""
Tests for update_orderbooks_task (Celery task).

Strategy: mock get_sync_rw_session and OrderbookSyncRepository,
call task.run() directly (bind=True — self is already bound to the task instance).
Retry behaviour is tested by patching update_orderbooks_task.retry.
"""
import pytest
from unittest.mock import MagicMock, patch

from tasks.orderbooks import update_orderbooks_task


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _patched_run(platform, batch, *, repo_side_effect=None):
    """Run the task synchronously with mocked DB layer."""
    with patch("tasks.orderbooks.get_sync_rw_session") as mock_ctx, \
         patch("tasks.orderbooks.OrderbookSyncRepository") as MockRepo:
        mock_ctx.return_value.__enter__.return_value = MagicMock()
        mock_ctx.return_value.__exit__.return_value = False
        if repo_side_effect is not None:
            MockRepo.return_value.update_orderbook.side_effect = repo_side_effect
        else:
            MockRepo.return_value.update_orderbook.return_value = MagicMock()
        update_orderbooks_task.run(platform, batch)
        return MockRepo.return_value


# ---------------------------------------------------------------------------
# Platform validation
# ---------------------------------------------------------------------------

def test_invalid_platform_raises_value_error():
    with pytest.raises(ValueError, match="Unsupported platform"):
        update_orderbooks_task.run("unknown_platform", {})


@pytest.mark.parametrize("platform", ["polymarket", "kalshi", "predict_fun"])
def test_valid_platforms_do_not_raise_on_empty_batch(platform):
    _patched_run(platform, {})  # should not raise


# ---------------------------------------------------------------------------
# Batch processing
# ---------------------------------------------------------------------------

def test_calls_update_orderbook_for_each_item():
    batch = {"mkt-1": {"yes": []}, "mkt-2": {"no": []}}
    repo = _patched_run("polymarket", batch)

    assert repo.update_orderbook.call_count == 2
    repo.update_orderbook.assert_any_call("mkt-1", {"yes": []})
    repo.update_orderbook.assert_any_call("mkt-2", {"no": []})


def test_market_not_found_logs_warning_and_continues():
    """update_orderbook returning falsy triggers a log.warning but does NOT raise."""
    batch = {"missing-mkt": {"data": 1}, "found-mkt": {"data": 2}}
    repo = _patched_run("kalshi", batch, repo_side_effect=[None, MagicMock()])
    assert repo.update_orderbook.call_count == 2


# ---------------------------------------------------------------------------
# Retry on exception
# ---------------------------------------------------------------------------

def test_exception_in_loop_triggers_retry():
    with patch("tasks.orderbooks.get_sync_rw_session") as mock_ctx, \
         patch("tasks.orderbooks.OrderbookSyncRepository") as MockRepo, \
         patch.object(update_orderbooks_task, "retry", side_effect=RuntimeError("retry triggered")) as mock_retry:
        mock_ctx.return_value.__enter__.return_value = MagicMock()
        mock_ctx.return_value.__exit__.return_value = False
        MockRepo.return_value.update_orderbook.side_effect = Exception("db error")

        with pytest.raises(RuntimeError, match="retry triggered"):
            update_orderbooks_task.run("polymarket", {"mkt-1": {}})

    mock_retry.assert_called_once()