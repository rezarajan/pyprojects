from warnings import resetwarnings
from data_structures.linkedlist import LinkedList
import pytest
from algorithms import search_algorithms, merge_sort


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
    assert search_algorithms.linear_search(data, target) == expected


@pytest.mark.parametrize(
    "data, target, expected",
    [
        ([1, 2, 3, 4, 5], 2, 1),  # int search, found
        (["a", "b", "c", "d", "e"], "d", 3),  # str search, found
        ([], 42, None),  # empty list, not found
        ([1, 2, 3], 1, 0),  # first element
        ([1, 2, 3], 3, 2),  # last element
    ],
)
def test_binary_search(data, target, expected):
    assert search_algorithms.binary_search(data, target) == expected
    assert search_algorithms.recursive_binary_search(data, target) == expected
    assert search_algorithms.idx_binary_search(data, target) == expected


@pytest.mark.parametrize(
    "data, expected",
    [
        ([1, 2, 3, 4, 5], [1, 2, 3, 4, 5]),
        (["a", "d", "e", "b", "f"], ["a", "b", "d", "e", "f"]),
        ([], []),
        ([56, 80, -1, 10, -80, 1.5, 8, 12], [-80, -1, 1.5, 8, 10, 12, 56, 80]),
        ([1], [1]),
    ],
)
def test_merge_sort(data, expected):
    assert merge_sort.merge_sort(data) == expected


@pytest.mark.parametrize(
    "data, expected",
    [
        ([1, 2, 3, 4, 5], [1, 2, 3, 4, 5]),
        (["a", "d", "e", "b", "f"], ["a", "b", "d", "e", "f"]),
        ([], []),
        ([56, 80, -1, 10, -80, 1.5, 8, 12], [-80, -1, 1.5, 8, 10, 12, 56, 80]),
        ([1], [1]),
    ],
)
def test_merge_sort_linked_list(data, expected):
    _data = LinkedList()
    _expected = LinkedList()

    for d in data:
        _data.add(d)

    for e in expected[::-1]:
        _expected.add(e)

    result = merge_sort.merge_sort_linked_list(_data)
    assert str(result) == str(_expected)
