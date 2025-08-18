import pytest
from algorithms import algorithms


# NOTE: test inputs can be parameterized using pytest
@pytest.mark.parametrize(
    "data, target, expected",
    [
        ([1, 2, 3, 4, 5], 2, 1),  # int search, found
        (["a", "b", "c", "d", "e"], "d", 3),  # str search, found
        ([10, 4, 2, 9, 100, 20], 6, None),  # int search, not found
        ([], 42, None),  # empty list, not found
        ([1, 2, 3], 1, 0),  # first element
        ([1, 2, 3], 3, 2),  # last element
    ],
)
def test_linear_search(data, target, expected):
    assert algorithms.linear_search(data, target) == expected
