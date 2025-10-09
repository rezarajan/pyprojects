import pytest
from unittest.mock import patch, MagicMock
from snippets import exponential_backoff


@patch("time.sleep", return_value=None)  # skip real sleeping
def test_successful_operation(mock_sleep):
    """Should return immediately when operation succeeds."""
    op = MagicMock(return_value="OK")

    result = exponential_backoff.exponential_backoff(op)

    assert result == "OK"
    op.assert_called_once()
    mock_sleep.assert_not_called()


@patch("time.sleep", return_value=None)
def test_eventual_success(mock_sleep):
    """Should retry until the operation succeeds."""
    op = MagicMock(side_effect=[ValueError("fail"), ValueError("fail"), "Success!"])

    result = exponential_backoff.exponential_backoff(op, max_retries=5)

    assert result == "Success!"
    assert op.call_count == 3
    assert mock_sleep.call_count == 2  # sleeps after first two failures


@patch("time.sleep", return_value=None)
def test_all_failures(mock_sleep):
    """Should raise after max_retries are exhausted."""
    op = MagicMock(side_effect=ValueError("fail"))

    with pytest.raises(ValueError):
        exponential_backoff.exponential_backoff(op, max_retries=3)

    assert op.call_count == 3
    assert mock_sleep.call_count == 2  # sleeps between retries


@patch("time.sleep", return_value=None)
def test_max_delay_cap(mock_sleep):
    """Ensure delay never exceeds max_delay."""
    with patch("random.uniform", return_value=1.0):  # remove jitter randomness
        op = MagicMock(side_effect=[Exception("x")] * 4)

        with pytest.raises(Exception):
            exponential_backoff.exponential_backoff(
                op, max_retries=4, base_delay=10, max_delay=15
            )

        # Extract delays passed to time.sleep
        delays = [args[0] for args, _ in mock_sleep.call_args_list]
        assert all(d <= 15 for d in delays)
