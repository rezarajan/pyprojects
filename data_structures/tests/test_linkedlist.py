from data_structures.linkedlist import LinkedList, Strable  # adjust import if needed


class Item(Strable):
    def __init__(self, value: str):
        self.value = value

    def __str__(self) -> str:
        return self.value

    def __eq__(self, other) -> bool:
        return isinstance(other, Item) and self.value == other.value


def test_add_and_len():
    ll = LinkedList[Item]()
    assert ll.len() == 0

    ll.add(Item("A"))
    ll.add(Item("B"))
    assert ll.len() == 2
    assert str(ll) == "[Head] B -> A [Tail]"


def test_insert_at_head():
    ll = LinkedList[Item]()
    ll.add(Item("A"))
    ll.insert(Item("B"), 0)

    assert str(ll) == "[Head] B -> A [Tail]"

    node = ll.get(0)
    assert node is not None
    assert node.get_data().value == "B"


def test_insert_in_middle():
    ll = LinkedList[Item]()
    ll.add(Item("C"))
    ll.add(Item("A"))
    ll.insert(Item("B"), 1)

    assert str(ll) == "[Head] A -> B -> C [Tail]"


def test_search_found():
    ll = LinkedList[Item]()
    ll.add(Item("C"))
    ll.add(Item("B"))
    ll.add(Item("A"))

    result = ll.search(Item("B"))
    assert result is not None
    node, idx = result
    assert idx == 1
    assert node.get_data().value == "B"


def test_search_not_found():
    ll = LinkedList[Item]()
    ll.add(Item("A"))
    assert ll.search(Item("Z")) is None


def test_delete():
    ll = LinkedList[Item]()
    ll.add(Item("C"))
    ll.add(Item("B"))
    ll.add(Item("A"))

    removed = ll.delete(Item("B"))
    assert removed is not None
    assert removed.get_data().value == "B"
    assert str(ll) == "[Head] A -> C [Tail]"

    # deleting non-existent
    assert ll.delete(Item("Z")) is None
