from typing import Iterable


def _summarize_set_elements(x: Iterable[str]) -> str:
    """
    Return a comma-delimited representation of the first 10 elements of Iterable[str].

    - If the set has fewer than 11 elements, return all elements.
    - Otherwise return the first 10 elements in lexicographic order followed by an ellipsis.
    """
    sorted_x = sorted(x)

    if len(sorted_x) <= 10:
        return "[" + ", ".join(sorted_x) + "]"

    return "[" + ", ".join(sorted_x[:10]) + ", ... ]"

