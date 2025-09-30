from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Protocol, Any, Generic, Callable, Optional, TypeVar, Iterator, List

T = TypeVar("T")


# A protocol expressing that a type supports euqality comparisons
class Comparable(Protocol):
    def __lt__(self, other: Any) -> bool: ...
    def __gt__(self, other: Any) -> bool: ...
    def __ge__(self, other: Any) -> bool: ...
    def __le__(self, other: Any) -> bool: ...
    def __eq__(self, other: Any) -> bool: ...


C = TypeVar("C", bound=Comparable)


# -----------------------------
# Node Base Classes
# -----------------------------
class NodeBase(Generic[T]):
    """Base class for nodes in linked lists."""

    def __init__(self, value: T):
        self.value: T = value


# -----------------------------
# Singly Linked List Node
# -----------------------------
class SLLNode(NodeBase[T]):
    """Singly-linked list node."""

    def __init__(self, value: T, next: Optional[SLLNode[T]] = None):
        super().__init__(value)
        self.next: Optional[SLLNode[T]] = next

    def __repr__(self) -> str:
        return f"SLLNode(value={self.value}, next={getattr(self.next, 'value', None)})"


# -----------------------------
# Doubly Linked List Node
# -----------------------------
class DLLNode(NodeBase[T]):
    """Doubly-linked list node."""

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
        return (
            f"DLLNode(value={self.value}, "
            f"prev={getattr(self.prev, 'value', None)}, "
            f"next={getattr(self.next, 'value', None)})"
        )


# -----------------------------
# Binary Tree Node
# -----------------------------
class BinaryTreeNode(NodeBase[C]):
    """A node in a binary tree, inheriting from NodeBase."""

    __slots__ = ("value", "left", "right")

    def __init__(
        self,
        value: C,
        left: Optional[BinaryTreeNode[C]] = None,
        right: Optional[BinaryTreeNode[C]] = None,
    ) -> None:
        super().__init__(value)
        self.left = left
        self.right = right

    def __repr__(self) -> str:
        return f"BinaryTreeNode({self.value!r})"


# -----------------------------
# Abstract Linked List Base
# -----------------------------
class LinkedListBase(ABC, Generic[T]):
    """Abstract base class for linked lists."""

    @property
    @abstractmethod
    def head(self) -> Optional[NodeBase[T]]:
        """Return the head node (first node)."""
        pass

    @abstractmethod
    def append(self, value: T) -> None:
        pass

    @abstractmethod
    def prepend(self, value: T) -> None:
        pass

    @abstractmethod
    def remove(self, value: T) -> bool:
        pass

    @abstractmethod
    def pop_left(self) -> T:
        pass

    @abstractmethod
    def clear(self) -> None:
        pass

    @abstractmethod
    def to_list(self) -> List[T]:
        pass

    @abstractmethod
    def __len__(self) -> int:
        pass

    @abstractmethod
    def __iter__(self) -> Iterator[T]:
        pass

    @abstractmethod
    def is_empty(self) -> bool:
        pass

    @abstractmethod
    def __repr__(self) -> str:
        pass


# -----------------------------
# Singly Linked List
# -----------------------------
class SinglyLinkedList(LinkedListBase[T]):
    """Singly-linked list implementation."""

    def __init__(self) -> None:
        self._head: Optional[SLLNode[T]] = None
        self._size: int = 0

    # Property to comply with LinkedListBase
    @property
    def head(self) -> Optional[SLLNode[T]]:
        return self._head

    @head.setter
    def head(self, node: Optional[SLLNode[T]]) -> None:
        self._head = node

    def __len__(self) -> int:
        return self._size

    def __iter__(self) -> Iterator[T]:
        current = self._head
        while current:
            yield current.value
            current = current.next

    def __repr__(self) -> str:
        values = " -> ".join(repr(v) for v in self)
        return f"SinglyLinkedList([{values}])"

    def is_empty(self) -> bool:
        return self._size == 0

    def append(self, value: T) -> None:
        new_node = SLLNode(value)
        if not self._head:
            self._head = new_node
        else:
            current = self._head
            while current.next:
                current = current.next
            current.next = new_node
        self._size += 1

    def prepend(self, value: T) -> None:
        self._head = SLLNode(value, next=self._head)
        self._size += 1

    def remove(self, value: T) -> bool:
        if not self._head:
            return False
        if self._head.value == value:
            self._head = self._head.next
            self._size -= 1
            return True
        prev = self._head
        curr = self._head.next
        while curr:
            if curr.value == value:
                prev.next = curr.next
                self._size -= 1
                return True
            prev, curr = curr, curr.next
        return False

    def pop_left(self) -> T:
        if not self._head:
            raise IndexError("pop from empty list")
        value = self._head.value
        self._head = self._head.next
        self._size -= 1
        return value

    def clear(self) -> None:
        self._head = None
        self._size = 0

    def to_list(self) -> List[T]:
        return list(iter(self))


# -----------------------------
# Doubly Linked List
# -----------------------------
class DoublyLinkedList(LinkedListBase[T]):
    """Doubly-linked list implementation."""

    def __init__(self) -> None:
        self._head: Optional[DLLNode[T]] = None
        self._tail: Optional[DLLNode[T]] = None
        self._size: int = 0

    # Property to comply with LinkedListBase
    @property
    def head(self) -> Optional[DLLNode[T]]:
        return self._head

    @head.setter
    def head(self, node: Optional[DLLNode[T]]) -> None:
        self._head = node

    @property
    def tail(self) -> Optional[DLLNode[T]]:
        return self._tail

    @tail.setter
    def tail(self, node: Optional[DLLNode[T]]) -> None:
        self._tail = node

    def __len__(self) -> int:
        return self._size

    def __iter__(self) -> Iterator[T]:
        current = self._head
        while current:
            yield current.value
            current = current.next

    def __repr__(self) -> str:
        if self.is_empty():
            return "DoublyLinkedList([])"
        values = " ⇄ ".join(repr(v) for v in self)
        return f"HEAD ⇄ {values} ⇄ TAIL"

    def is_empty(self) -> bool:
        return self._size == 0

    def append(self, value: T) -> None:
        new_node = DLLNode(value, prev=self._tail)
        if not self._head:
            self._head = new_node
        else:
            assert self._tail is not None
            self._tail.next = new_node
        self._tail = new_node
        self._size += 1

    def prepend(self, value: T) -> None:
        new_node = DLLNode(value, next=self._head)
        if self._head:
            self._head.prev = new_node
        else:
            self._tail = new_node
        self._head = new_node
        self._size += 1

    def remove(self, value: T) -> bool:
        current = self._head
        while current:
            if current.value == value:
                if current.prev:
                    current.prev.next = current.next
                else:
                    self._head = current.next
                if current.next:
                    current.next.prev = current.prev
                else:
                    self._tail = current.prev
                self._size -= 1
                return True
            current = current.next
        return False

    def pop_left(self) -> T:
        if not self._head:
            raise IndexError("pop from empty list")
        value = self._head.value
        self._head = self._head.next
        if self._head:
            self._head.prev = None
        else:
            self._tail = None
        self._size -= 1
        return value

    def pop(self) -> T:
        if not self._tail:
            raise IndexError("pop from empty list")
        value = self._tail.value
        self._tail = self._tail.prev
        if self._tail:
            self._tail.next = None
        else:
            self._head = None
        self._size -= 1
        return value

    def clear(self) -> None:
        self._head = None
        self._tail = None
        self._size = 0

    def to_list(self) -> List[T]:
        return list(iter(self))


class BinaryTree(Generic[C]):
    """Binary tree wrapper class."""

    __slots__ = ("_root", "_size")

    def __init__(self, root: Optional[BinaryTreeNode[C]] = None) -> None:
        self._root = root
        self._size = 0 if root is None else self._compute_size(root)

    @property
    def root(self) -> Optional[BinaryTreeNode[C]]:
        return self._root

    @property
    def size(self) -> int:
        return self._size

    def is_empty(self) -> bool:
        return self._root is None

    def _compute_size(self, node: Optional[BinaryTreeNode[C]]) -> int:
        if node is None:
            return 0
        return 1 + self._compute_size(node.left) + self._compute_size(node.right)

    # -------------------------------
    # Insert (simple binary search tree insert)
    # -------------------------------
    def insert(self, value: C) -> None:
        """Insert a value into the binary tree (BST style)."""

        def _insert(node: Optional[BinaryTreeNode[C]], value: C) -> BinaryTreeNode[C]:
            if node is None:
                return BinaryTreeNode(value)
            if value < node.value:
                node.left = _insert(node.left, value)
            else:
                node.right = _insert(node.right, value)
            return node

        self._root = _insert(self._root, value)
        self._size += 1

    # -------------------------------
    # Traversals
    # -------------------------------
    def inorder(self, visit: Callable[[C], None]) -> None:
        def _inorder(node: Optional[BinaryTreeNode[C]]):
            if node:
                _inorder(node.left)
                visit(node.value)
                _inorder(node.right)

        _inorder(self._root)

    def preorder(self, visit: Callable[[C], None]) -> None:
        def _preorder(node: Optional[BinaryTreeNode[C]]):
            if node:
                visit(node.value)
                _preorder(node.left)
                _preorder(node.right)

        _preorder(self._root)

    def postorder(self, visit: Callable[[C], None]) -> None:
        def _postorder(node: Optional[BinaryTreeNode[C]]):
            if node:
                _postorder(node.left)
                _postorder(node.right)
                visit(node.value)

        _postorder(self._root)

    # -------------------------------
    # Utility
    # -------------------------------
    def to_list(self) -> List[C]:
        """Return all values of the tree in inorder as a list."""
        values: List[C] = []
        self.inorder(values.append)
        return values

    def __repr__(self) -> str:
        return f"BinaryTree({self.to_list()})"

    def pretty_print(self) -> str:
        if not self._root:
            return "<empty>"

        def _display(
            node: Optional["BinaryTreeNode[C]"],
        ) -> tuple[list[str], int, int, int]:
            """
            Returns:
                lines: list of strings for this subtree
                width: total width
                height: total height
                middle: horizontal position of root
            """
            if node is None:
                return [], 0, 0, 0

            line = f"┌{node.value}┐"
            width = len(line)

            if node.left is None and node.right is None:
                return [line], width, 1, width // 2

            # Recursively display left and right
            left_lines, left_width, left_height, left_middle = _display(node.left)
            right_lines, right_width, right_height, right_middle = _display(node.right)

            # Compute new width and height
            height = max(left_height, right_height) + 2
            middle = left_width + width // 2 + 1 if node.left else width // 2

            # Pad left/right lines
            left_lines += [" " * left_width] * (right_height - left_height)
            right_lines += [" " * right_width] * (left_height - right_height)

            # Combine lines
            lines = [" " * left_width + line + " " * right_width]  # root line
            for l, r in zip(left_lines, right_lines):
                lines.append(l + " " * width + r)
            return lines, left_width + width + right_width, height, middle

        lines, _, _, _ = _display(self._root)
        return "\n".join(lines)
