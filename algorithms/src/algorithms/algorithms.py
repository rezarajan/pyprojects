"""
SEARCH ALGORITHMS
"""

from __future__ import annotations
from typing import Protocol, Self


# NOTE: these functions use the type parameter syntax (generics)
# see: https://docs.python.org/3/reference/compound_stmts.html#type-params


# NOTE: the Comparable class here is used to specify if certain generics
# support comparison operations, which are necessary for most algorithms
class Comparable(Protocol):
    def __lt__(self, other: Self) -> bool: ...
    def __le__(self, other: Self) -> bool: ...
    def __gt__(self, other: Self) -> bool: ...
    def __ge__(self, other: Self) -> bool: ...


def linear_search[T](input: list[T], target: T) -> int | None:
    """
    Performs a linear search on the input list.
    Returns the index of the target if forund,
    otherwise returns None.
    """

    # We must iterate through the entire list, so this operation is O(n)
    for i in range(0, len(input)):  # Python keeps track of len(input), so this is O(1)
        if input[i] == target:  # this comparison is also O(1)
            return i
    return None

    # Overall, the longest operation in the linear search algorithm is O(n)
    # Therefore, linear search is an O(n) operation


def binary_search[T: Comparable](input: list[T], target: T) -> int | None:
    """
    Performs a binary search on the input list.
    The input list must be sorted. This search algorithm
    may produce unexpected results otherwise.
    Returns the index of the target if found,
    otherwise returns None.
    """

    first, last = 0, len(input) - 1

    # This while loop actually takes O(log(n)) time
    # because it halves the search space on each iteration
    while first <= last:
        midpoint = (first + last) // 2  # O(1)

        if input[midpoint] < target:  # O(1)
            first = midpoint + 1
        elif input[midpoint] > target:  # O(1)
            last = midpoint - 1
        else:
            return midpoint

    return None

    # Overall, the longest operation in the binary search algorithm in O(log(n))
    # Therefore, binary search is an O(log(n)) operation


def recursive_binary_search[T: Comparable](seq: list[T], target: T) -> int | None:
    """
    Performs a binary search on a sorted input list, `seq`.
    Returns the index of `target` if found,
    otherwise returns None.
    """
    # Exhaused the search space, no match
    if len(seq) == 0:  # O(1)
        return None

    # Compare the current mid to target
    midpoint = len(seq) // 2

    if seq[midpoint] == target:  # O(1)
        return midpoint

    # The following two comparisons use recursion, which
    # incurs up to O(log(n)) time complexity
    if seq[midpoint] > target:  # O(1)
        # Already in the left-slice coordinate system
        return recursive_binary_search(seq[:midpoint], target)

    if seq[midpoint] < target:  # O(1)
        res = recursive_binary_search(seq[midpoint + 1 :], target)
        if res is None:
            return None
        # result is relative to the right-slice; adjust to original indices
        return midpoint + 1 + res


def idx_binary_search[T: Comparable](seq: list[T], target: T) -> int | None:
    """
    Performs a binary search on a sorted input list, `seq`.
    Returns the index of `target` if found,
    otherwise returns None.
    """
    # NOTE: This function uses an inner unexported function to accomplish the search.
    # This version is also more efficient than passing slices, becuase in Python
    # slices are copies. For binary search with slices will incur O(n) extra work in allocations.
    # By comparison, this bounded indices approach only passes integers.

    def _search(lo: int, hi: int) -> int | None:
        # Reached the end of the search
        if lo > hi:
            return None
        mid = (lo + hi) // 2
        if seq[mid] == target:
            return mid
        if seq[mid] < target:
            return _search(mid + 1, hi)
        return _search(lo, mid)

    return _search(0, len(seq) - 1)
