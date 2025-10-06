from __future__ import annotations
from typing import Any, Callable, Generic, List, Optional, Protocol, TypeVar, cast

T = TypeVar("T")


# A protocol expressing that a type supports math comparisons
class SupportsMath(Protocol):
    # Arithmetic operations
    def __add__(self: T, other: T) -> T: ...
    def __sub__(self: T, other: T) -> T: ...
    def __mul__(self: T, other: T) -> T: ...
    def __truediv__(self: T, other: T) -> T: ...
    def __floordiv__(self: T, other: T) -> T: ...
    def __mod__(self: T, other: T) -> T: ...
    def __pow__(self: T, other: T, modulo: Any = ...) -> T: ...

    # Unary operations
    def __neg__(self: T) -> T: ...
    def __pos__(self: T) -> T: ...
    def __abs__(self: T) -> T: ...

    # Comparisons
    def __lt__(self, other: Any) -> bool: ...
    def __le__(self, other: Any) -> bool: ...
    def __gt__(self, other: Any) -> bool: ...
    def __ge__(self, other: Any) -> bool: ...
    def __eq__(self, other: Any) -> bool: ...
    def __ne__(self, other: Any) -> bool: ...


M = TypeVar("M", bound=SupportsMath)


# -----------------------------
# Node Base Classes
# -----------------------------
class NodeBase(Generic[T]):
    """Base class for nodes in linked lists."""

    def __init__(self, value: T):
        self.value: T = value


# -----------------------------
# Binary Tree Node
# -----------------------------
class BinaryTreeNode(NodeBase[M]):
    """A node in a binary tree, inheriting from NodeBase."""

    __slots__ = ("value", "left", "right")

    def __init__(
        self,
        value: M,
        left: Optional[BinaryTreeNode[M]] = None,
        right: Optional[BinaryTreeNode[M]] = None,
    ) -> None:
        super().__init__(value)
        self.left = left
        self.right = right

    def __repr__(self) -> str:
        return f"BinaryTreeNode({self.value!r})"


# -----------------------------
# Binary Tree
# -----------------------------
class BinaryTree(Generic[M]):
    """Binary tree wrapper class."""

    __slots__ = ("_root", "_size")

    def __init__(self, root: Optional[BinaryTreeNode[M]] = None) -> None:
        self._root = root
        self._size = 0 if root is None else self._compute_size(root)

    @property
    def root(self) -> Optional[BinaryTreeNode[M]]:
        return self._root

    @property
    def size(self) -> int:
        return self._size

    def is_empty(self) -> bool:
        return self._root is None

    def _compute_size(self, node: Optional[BinaryTreeNode[M]]) -> int:
        if node is None:
            return 0
        return 1 + self._compute_size(node.left) + self._compute_size(node.right)

    # -------------------------------
    # Insert (generic: first empty spot)
    # -------------------------------
    def insert(self, value: M) -> None:
        """Insert value anywhere in the tree (first empty spot found)."""
        new_node = BinaryTreeNode(value)
        if self._root is None:
            self._root = new_node
            self._size = 1
            return

        queue: List[BinaryTreeNode[M]] = [self._root]
        while queue:
            node = queue.pop(0)
            if node.left is None:
                node.left = new_node
                self._size += 1
                return
            else:
                queue.append(node.left)
            if node.right is None:
                node.right = new_node
                self._size += 1
                return
            else:
                queue.append(node.right)

    # -------------------------------
    # Traversals
    # -------------------------------
    def inorder(self, visit: Callable[[M], None]) -> None:
        def _inorder(node: Optional[BinaryTreeNode[M]]):
            if node:
                _inorder(node.left)
                visit(node.value)
                _inorder(node.right)

        _inorder(self._root)

    def preorder(self, visit: Callable[[M], None]) -> None:
        def _preorder(node: Optional[BinaryTreeNode[M]]):
            if node:
                visit(node.value)
                _preorder(node.left)
                _preorder(node.right)

        _preorder(self._root)

    def postorder(self, visit: Callable[[M], None]) -> None:
        def _postorder(node: Optional[BinaryTreeNode[M]]):
            if node:
                _postorder(node.left)
                _postorder(node.right)
                visit(node.value)

        _postorder(self._root)

    # -------------------------------
    # Utility
    # -------------------------------
    def to_list(self) -> List[M]:
        """Return all values of the tree in inorder as a list."""
        values: List[M] = []
        self.inorder(values.append)
        return values

    def height(self) -> int:
        """
        Returns the maximum height of the binary tree from an input node
        Time Complexity: O(n) since all nodes must be traversed to find the largest height (preorder traversal)
        Space Complexity: O(logn) avg./O(n) worst for recursion stack space, and O(1) for tail recursion optimization
        """
        max_height = 0

        def _preorder(node: Optional[BinaryTreeNode[M]], current_height: int):
            nonlocal max_height
            if node:
                current_height += 1
                _preorder(node.left, current_height)
                _preorder(node.right, current_height)
            if current_height > max_height:
                max_height = current_height

        _preorder(self._root, 0)
        return max_height

    def sum(self) -> M:
        """
        Finds the sum of all values binary search tree
        Time Complexity: O(n) since all nodes must be traversed
        Space Complexity: O(logn) avg./O(n) worst for recursion stack space, and O(1) for tail recursion optimization
        """
        _sum = cast(M, 0)

        def _add(val: M) -> None:
            nonlocal _sum
            _sum += val

        self.preorder(_add)
        return _sum

    def __repr__(self) -> str:
        return f"BinaryTree({self.to_list()})"

    def pretty_print(self) -> str:
        if not self._root:
            return "<empty>"

        def _display(
            node: Optional[BinaryTreeNode[M]],
        ) -> tuple[list[str], int, int, int]:
            if node is None:
                return [], 0, 0, 0

            line = f"┌{node.value}┐"
            width = len(line)

            if node.left is None and node.right is None:
                return [line], width, 1, width // 2

            left_lines, left_width, left_height, left_middle = _display(node.left)
            right_lines, right_width, right_height, right_middle = _display(node.right)

            height = max(left_height, right_height) + 2
            middle = left_width + width // 2 + 1 if node.left else width // 2

            left_lines += [" " * left_width] * (right_height - left_height)
            right_lines += [" " * right_width] * (left_height - right_height)

            lines = [" " * left_width + line + " " * right_width]
            for l, r in zip(left_lines, right_lines):
                lines.append(l + " " * width + r)
            return lines, left_width + width + right_width, height, middle

        lines, _, _, _ = _display(self._root)
        return "\n".join(lines)


# -----------------------------
# Binary Search Tree
# -----------------------------
class BinarySearchTree(BinaryTree[M]):
    """Binary search tree derived from BinaryTree."""

    # -------------------------------
    # Insert override for BST
    # -------------------------------
    def insert(self, value: M) -> None:
        """Insert a value into the binary tree (BST style)."""

        def _insert(node: Optional[BinaryTreeNode[M]], value: M) -> BinaryTreeNode[M]:
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
    # Search
    # -------------------------------
    def find_max(self) -> Optional[M]:
        """
        Finds the maximum value in the binary search tree
        Time Complexity: Avg. O(logn) since DFS is used to traverse each level to the max value
                         O(n) worst case for an unbalanced BST
        Space Complexity: O(logn) for extra stack space, and O(1) for tail recursion optimization
        """
        node = self._root
        if node is None:
            return None
        while node.right:
            node = node.right
        return node.value

    def find_min(self) -> Optional[M]:
        """
        Finds the minimum value in the binary search tree
        Time Complexity: Avg. O(logn) since DFS is used to traverse each level to the min value
                         O(n) worst case for an unbalanced BST
        Space Complexity: O(logn) for extra stack space, and O(1) for tail recursion optimization
        """
        node = self._root
        if node is None:
            return None
        while node.left:
            node = node.left
        return node.value


class TrieNode(Generic[T]):
    """
    A simple trie node wrapper object
    Contains:
        children: a HashMap of character: TrieNodes
        count: the number of children in the TrieNode
        is_end: a flag to signify the end of a word
    """

    def __init__(self):
        self.children = {}
        self.count = 0  # number of words descending from this node (>= len(children))
        self.is_end = False

    def __repr__(self):
        return f"[TrieNode] Children {list(self.children.keys())}; Count {self.count}; End {self.is_end}"


class Trie(Generic[T]):
    def __init__(self):
        self.root = TrieNode()

    def insert(self, words: List[str]) -> None:
        """
        Updates the Trie with a given word list
        Takes O(c), where c is the total number of characters
        Space complexity: O(k), where k is the number of new characters added to the trie
        """
        for word in words:
            tn = self.root
            for ch in word:
                if not tn.children.get(ch):
                    tn.children[ch] = TrieNode()
                tn.count += 1
                tn = tn.children[ch]
            tn.count += 1  # include a count for the last set child
            tn.is_end = True

    def traverse(self, visit: Optional[Callable[[str, TrieNode], bool]] = None) -> None:
        """
        Traverses the trie and optionally calls `visit(prefix, node)` for each node.
        If `visit` is called and returns False then the traversal breaks.
        Takes O(n) time, where n is the number of nodes.
        """

        def _traverse(node: TrieNode, prefix: str) -> None:
            # Call visitor if provided
            res = True
            if visit:
                res = visit(prefix, node)

            # If visit returns False, exit here
            if not res:
                return

            # Recurse through all children
            for ch, child in node.children.items():
                _traverse(child, prefix + ch)

        _traverse(self.root, "")
