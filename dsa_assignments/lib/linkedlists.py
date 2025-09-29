from __future__ import annotations
from typing import Generic, Optional, TypeVar, Iterator, List

T = TypeVar("T")


class NodeBase(Generic[T]):
    """
    Base class for nodes in a linked list.

    Attributes:
        value (T): The value stored in the node.
    """

    def __init__(self, value: T):
        self.value: T = value


class SLLNode(NodeBase[T]):
    """
    Node for a singly linked list.

    Attributes:
        value (T): The value stored in the node (inherited from NodeBase).
        next (Optional[SLLNode[T]]): Reference to the next node in the list.
    """

    def __init__(self, value: T, next: Optional[SLLNode[T]] = None):
        super().__init__(value)
        self.next: Optional[SLLNode[T]] = next

    def __repr__(self) -> str:
        """Return a readable string representation showing the node value and next value."""
        next_val = self.next.value if self.next else None
        return f"SLLNode(value={self.value}, next={next_val})"


class DLLNode(NodeBase[T]):
    """
    Node for a doubly linked list.

    Attributes:
        value (T): The value stored in the node (inherited from NodeBase).
        prev (Optional[DLLNode[T]]): Reference to the previous node in the list.
        next (Optional[DLLNode[T]]): Reference to the next node in the list.
    """

    def __init__(
        self,
        value: T,
        prev: Optional[DLLNode[T]] = None,
        next: Optional[DLLNode[T]] = None,
    ):
        super().__init__(value)
        self.prev: Optional[DLLNode[T]] = prev
        self.next: Optional[DLLNode[T]] = next

    def __repr__(self) -> str:
        """Return a readable string representation showing the node value, prev value, and next value."""
        prev_val = self.prev.value if self.prev else None
        next_val = self.next.value if self.next else None
        return f"DLLNode(value={self.value}, prev={prev_val}, next={next_val})"


class SinglyLinkedList(Generic[T]):
    """
    Singly linked list implementation.

    Attributes:
        head (Optional[SLLNode[T]]): The first node in the list.
        _size (int): Number of elements in the list.
    """

    def __init__(self) -> None:
        """Initialize an empty singly linked list."""
        self.head: Optional[SLLNode[T]] = None
        self._size: int = 0

    def __len__(self) -> int:
        """Return the number of elements in the list."""
        return self._size

    def __iter__(self) -> Iterator[T]:
        """Iterate over the values of the linked list from head to tail."""
        current = self.head
        while current:
            yield current.value
            current = current.next

    def __repr__(self) -> str:
        """Return a readable string representation of the list."""
        values = " -> ".join(repr(v) for v in self)
        return f"SinglyLinkedList([{values}])"

    def is_empty(self) -> bool:
        """Return True if the list is empty, False otherwise."""
        return self._size == 0

    def append(self, value: T) -> None:
        """
        Append a value to the end of the list.

        Args:
            value (T): The value to append.
        """
        new_node = SLLNode(value)
        if not self.head:
            self.head = new_node
        else:
            current = self.head
            while current.next:
                current = current.next
            current.next = new_node
        self._size += 1

    def prepend(self, value: T) -> None:
        """
        Insert a value at the beginning of the list.

        Args:
            value (T): The value to prepend.
        """
        new_node = SLLNode(value, next=self.head)
        self.head = new_node
        self._size += 1

    def remove(self, value: T) -> bool:
        """
        Remove the first occurrence of the value in the list.

        Args:
            value (T): The value to remove.

        Returns:
            bool: True if a node was removed, False if the value was not found.
        """
        if not self.head:
            return False

        if self.head.value == value:
            self.head = self.head.next
            self._size -= 1
            return True

        prev = self.head
        curr = self.head.next
        while curr:
            if curr.value == value:
                prev.next = curr.next
                self._size -= 1
                return True
            prev, curr = curr, curr.next
        return False

    def pop_left(self) -> T:
        """
        Remove and return the value at the head of the list.

        Returns:
            T: The value of the removed node.

        Raises:
            IndexError: If the list is empty.
        """
        if not self.head:
            raise IndexError("pop from empty list")
        value = self.head.value
        self.head = self.head.next
        self._size -= 1
        return value

    def clear(self) -> None:
        """Remove all elements from the list."""
        self.head = None
        self._size = 0

    def to_list(self) -> List[T]:
        """
        Convert the linked list to a Python list.

        Returns:
            List[T]: List containing all the elements in order.
        """
        return list(iter(self))


class DoublyLinkedList(Generic[T]):
    """
    Doubly linked list implementation.

    Attributes:
        head (Optional[DLLNode[T]]): First node in the list.
        tail (Optional[DLLNode[T]]): Last node in the list.
        _size (int): Number of elements in the list.
    """

    def __init__(self) -> None:
        """Initialize an empty doubly linked list."""
        self.head: Optional[DLLNode[T]] = None
        self.tail: Optional[DLLNode[T]] = None
        self._size: int = 0

    def __len__(self) -> int:
        """Return the number of elements in the list."""
        return self._size

    def __iter__(self) -> Iterator[T]:
        """Iterate over the values in the list from head to tail."""
        current = self.head
        while current:
            yield current.value
            current = current.next

    def __repr__(self) -> str:
        """Return a readable string showing the list values with arrows."""
        if self.is_empty():
            return "DoublyLinkedList([])"
        values = " ⇄ ".join(repr(v) for v in self)
        return f"HEAD ⇄ {values} ⇄ TAIL"

    def is_empty(self) -> bool:
        """Return True if the list is empty, False otherwise."""
        return self._size == 0

    def append(self, value: T) -> None:
        """
        Append a value to the end of the list.

        Args:
            value (T): The value to append.
        """
        new_node = DLLNode(value, prev=self.tail)
        if not self.head:
            self.head = new_node
        else:
            self.tail.next = new_node
        self.tail = new_node
        self._size += 1

    def prepend(self, value: T) -> None:
        """
        Insert a value at the beginning of the list.

        Args:
            value (T): The value to prepend.
        """
        new_node = DLLNode(value, next=self.head)
        if self.head:
            self.head.prev = new_node
        else:
            self.tail = new_node
        self.head = new_node
        self._size += 1

    def remove(self, value: T) -> bool:
        """
        Remove the first occurrence of a value from the list.

        Args:
            value (T): The value to remove.

        Returns:
            bool: True if a node was removed, False if value not found.
        """
        current = self.head
        while current:
            if current.value == value:
                if current.prev:
                    current.prev.next = current.next
                else:
                    self.head = current.next

                if current.next:
                    current.next.prev = current.prev
                else:
                    self.tail = current.prev

                self._size -= 1
                return True
            current = current.next
        return False

    def pop_left(self) -> T:
        """
        Remove and return the value at the head of the list.

        Returns:
            T: The value of the removed node.

        Raises:
            IndexError: If the list is empty.
        """
        if not self.head:
            raise IndexError("pop from empty list")
        value = self.head.value
        self.head = self.head.next
        if self.head:
            self.head.prev = None
        else:
            self.tail = None
        self._size -= 1
        return value

    def pop(self) -> T:
        """
        Remove and return the value at the tail of the list.

        Returns:
            T: The value of the removed node.

        Raises:
            IndexError: If the list is empty.
        """
        if not self.tail:
            raise IndexError("pop from empty list")
        value = self.tail.value
        self.tail = self.tail.prev
        if self.tail:
            self.tail.next = None
        else:
            self.head = None
        self._size -= 1
        return value

    def clear(self) -> None:
        """Remove all elements from the list."""
        self.head = None
        self.tail = None
        self._size = 0

    def to_list(self) -> List[T]:
        """
        Convert the linked list to a Python list.

        Returns:
            List[T]: List containing all the elements in order.
        """
        return list(iter(self))
