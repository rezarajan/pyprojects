"""
A naiive implementation of a linked list data structure in Python.

Time Complexity:
Search: O(n)
Insert/Delete: O(1) for operation, but O(n) to find element
"""

from __future__ import annotations  # allows forward-referencing without quotes

from typing import Generic, TypeVar, Tuple, Optional


class Strable:
    def __str__(self) -> str: ...


# Ensures that the data types can be converted to string
T = TypeVar("T", bound=Strable)


class Node(Generic[T]):
    """
    A node is a container which contains data of type T
    and the next node it is linked to.
    """

    def __init__(self, data: T) -> None:
        self.data: T = data
        self.next: Optional[Node[T]] = None

    def __repr__(self) -> str:
        return f"[Node] {self.data}"

    def set_next(self, node: Optional[Node[T]]):
        self.next = node

    def get_data(self) -> T:
        return self.data

    def get_next(self) -> Optional[Node[T]]:
        return self.next


class LinkedList(Generic[T]):
    """
    LinkedList implements the linked list data structure,
    using the Node container with data type, T.

    It implements read, insert, delete, search.
    """

    def __init__(self) -> None:
        self.head: Optional[Node[T]] = None

    def __repr__(self) -> str:
        if self.head is None:
            return ""

        nodes: list[str] = []
        current = self.head
        while current is not None:
            nodes.append(str(current.get_data()))
            current = current.get_next()

        output = "[Head] " + " -> ".join(nodes) + " [Tail]"
        return output

    def len(self) -> int:
        """Returns the number of elements in the linked list"""
        if self.head is None:
            return 0

        len = 0
        current = self.head
        while current is not None:
            len += 1
            next = current.get_next()
            current = next
        return len

    def get(self, index) -> Optional[Node[T]]:
        """
        Returns the element at the index specified.
        If no element exists, returns None.
        NOTE: this does not check for index out-of-bounds.
        If the index is larger than the list, this will
        return None.
        """
        if self.head is None:
            return None

        current = self.head
        for _ in range(index):
            current = current.get_next()
            if current is None:
                break
        return current

    def add(self, data: T) -> None:
        """
        Inserts a new element to the head of the linked list.
        O(1) since no scanning is involved.
        """
        new_node = Node(data)
        new_node.set_next(self.head)
        self.head = new_node

    def insert(self, data: T, index: int) -> None:
        """
        Inserts an element into the linked list at the
        index specified.
        """
        new_node = Node(data)
        if index == 0:
            new_node.set_next(self.head)
            self.head = new_node
            return

        prior = self.get(index - 1)
        if prior is not None:
            new_node.set_next(prior.get_next())
            prior.set_next(new_node)

    def search(self, data: T) -> Optional[Tuple[Node[T], int]]:
        """
        Returns the first node, and the index of that node
        in the linked list which contains the value
        specified by data.
        O(n), since in the worst case it must scan the entire list
        """

        if self.head is None:
            return None

        # This is at most an O(n) operation
        counter = 0
        current = self.head
        while current is not None:
            # O(1) comparison
            if current.get_data() == data:
                return current, counter
            current = current.get_next()
            counter += 1

    def delete(self, data: T) -> Optional[Node[T]]:
        """
        Deletes a node with the specified data.
        Returns None if the data does not exist.
        O(n) since in the worst case the entire list must be
        scanned to find a match.
        """

        if self.head is None:
            return None

        prior = self.head
        current = prior.get_next()
        while current is not None:
            next = current.get_next()
            if current.get_data() == data:
                prior.set_next(next)
                return current
            prior = current
            current = next

        return None
