"""
INSERTION SORT ALGORITHM
"""

from __future__ import annotations

from typing import Protocol, TypeVar, runtime_checkable


"""
NOTE: Given an unsorted list, perform the following:
    - segment the list into an unsorted part and a sorted part
    - for each element in the unsorted part place it in the correct 
      position in the sorted part
"""


# The supported data types must include comparasons
@runtime_checkable
class Comparable(Protocol):
    def __lt__(self, other: "Comparable") -> bool: ...
    def __le__(self, other: "Comparable") -> bool: ...
    def __gt__(self, other: "Comparable") -> bool: ...
    def __ge__(self, other: "Comparable") -> bool: ...
    def __eq__(self, other: object) -> bool: ...
    def __str__(self) -> str: ...


T = TypeVar("T", bound=Comparable)


def insertion_sort(arr: list[T]) -> list[T]:
    """Insertion Sort
    Takes an input list of comparables and sorts it in ascending order
    Time Complexity: O(n^2) time in the worst case, O(n) in best case
    Space Complexity: O(1) since all operations are done in-place
    """

    for i in range(1, len(arr)):
        key = arr[i]
        j = i - 1
        while arr[j] > key and j >= 0:  # skips if already sorted
            arr[j + 1] = arr[j]  # move elements up one position
            j -= 1

        arr[j + 1] = key  # insert key at correct position

    return arr


def insertion_sort_alt(arr: list[T]) -> list[T]:
    """Insertion Sort Alternative Implementation
    Takes an input list of comparables and sorts it in ascending order
    Time Complexity: O(n^2) time in the worst case, O(n) in best case
    Space Complexity: O(1) since all operations are done in-place
    NOTE: Though the Big O notation is the same as before, this version
    may incur more operations in performing atomic swaps than the `insertion_sort`
    function.
    """

    for i in range(1, len(arr)):
        j = i - 1
        while arr[j] > arr[j + 1] and j >= 0:
            arr[j + 1], arr[j] = arr[j], arr[j + 1]
            j -= 1

    return arr
