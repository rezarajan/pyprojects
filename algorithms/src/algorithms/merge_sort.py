"""
MERGE SORT ALGORITHM
"""

from __future__ import annotations

from typing import Protocol, Tuple, TypeVar, runtime_checkable

from data_structures.linkedlist import LinkedList

"""
NOTE: Given an unsorted list, perform the following:
    - split the list until single elements are reached (base case)
    - merge each split list, sorting in the process, from bottom to top
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


def split(_l: list[T]) -> Tuple[list[T], list[T]]:
    """
    Splits a given list in two and returns each half

    Takes O(1) time
    """
    mid = len(_l) // 2
    return _l[:mid], _l[mid:]


def merge(seqs: Tuple[list[T], list[T]]) -> list[T]:
    """
    Takes as input a tuple containing two sequences and merges them
    in sorted order.

    Takes O(n) time.
    """
    _l, _r = seqs
    i: int = 0
    j: int = 0
    seq: list[T] = []  # resulted sorted sequence

    while i < len(_l) and j < len(_r):
        # Compare sequence values
        if _l[i] < _r[j]:
            seq.append(_l[i])
            i += 1
            continue

        seq.append(_r[j])
        j += 1

    # If one sequence is exhausted before the other
    # we must empty the remaining buffer
    if i < len(_l):
        seq.extend(_l[i:])
    if j < len(_r):
        seq.extend(_r[j:])

    return seq


def merge_sort(lst: list[T]) -> list[T]:
    """
    A recursive implementation of the merge_sort algorithm for the list type.

    Splitting Takes logn runs of O(1), so O(logn)
    Sorting Takes O(n)

    Overall Time: O(nlogn)
    """

    # Edge case - empty list as input
    if len(lst) == 0:
        return lst

    # Base case - at a single element list
    if len(lst) == 1:
        return lst

    # Split the list
    _l, _r = split(lst)

    # Recursively until the base case
    _l = merge_sort(_l)
    _r = merge_sort(_r)

    # Merge and sort the lists
    seq = merge((_l, _r))

    return seq


def merge_sort_linked_list(ll: LinkedList[T]) -> LinkedList[T]:
    """
    A recursive implementation of the merge sort algorithm for the linked list type.

    Splitting takes logn runs of O(n), so O(nlogn).
    Sorting takes O(n).

    Overall Time: O(nlogn)
    """

    def merge(llseq: Tuple[LinkedList[T], LinkedList[T]]) -> LinkedList[T]:
        """
        Takes as input a tuple containing two sequenced linked lists and merges them
        in sorted order.

        Takes O(n) time.
        """

        _l, _r = llseq
        merged = LinkedList[T]()
        cursor = merged.head  # sentinel

        left_head = _l.get_head()
        right_head = _r.get_head()

        while left_head or right_head:
            # Flush the remaining items to the merged list
            # once either tail is reached
            if left_head is None and right_head:
                cursor.set_next(right_head)
                right_head = right_head.get_next()

            if right_head is None and left_head:
                cursor.set_next(left_head)
                left_head = left_head.get_next()

            # Comparison
            if left_head and right_head:
                l_data = left_head.get_data()
                r_data = right_head.get_data()

                # Assign the lower value and increment the head
                if l_data < r_data:
                    cursor.set_next(left_head)
                    left_head = left_head.get_next()
                else:
                    cursor.set_next(right_head)
                    right_head = right_head.get_next()

            # Move cursor forward
            next = cursor.get_next()
            if next:
                cursor = next

        # Remove the sentinel and set head to real node
        cursor = merged.head.get_next()
        merged.set_head(cursor)

        return merged

    # Edge case - empty list as input
    if ll.get_head() is None:
        return ll

    # Base case - single element
    if ll.len() == 1:
        return ll

    # Split the list
    mid = ll.len() // 2
    _l, _r = ll.slice_at_index(mid)

    _l = merge_sort_linked_list(_l)
    _r = merge_sort_linked_list(_r)

    # Merge the lists
    merged = merge((_l, _r))
    return merged
