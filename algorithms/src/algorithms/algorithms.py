"""
SEARCH ALGORITHMS
"""


# NOTE: these functions use the type parameter syntax (generics)
# see: https://docs.python.org/3/reference/compound_stmts.html#type-params


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
