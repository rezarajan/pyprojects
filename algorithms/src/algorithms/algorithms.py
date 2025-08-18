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
