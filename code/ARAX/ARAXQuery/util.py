import heapq
from typing import Iterable

def summarize_set_elements(x: Iterable[str],
                           max_elem: int = 10) -> str:
    """
    Return a comma-delimited representation of the first max_elem elements of Iterable[str].

    - If the iterable has fewer than max_elem + 1 elements, return all elements.
    - Otherwise return the first max_elem elements in lexicographic order followed by an ellipsis.
    """
    sorted_x = heapq.nsmallest(max_elem + 1, x)
    if len(sorted_x) <= max_elem:
        return "[" + ", ".join(sorted_x) + "]"
    return "[" + ", ".join(sorted_x[:max_elem]) + ", ... ]"

