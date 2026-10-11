"""Rotated sorted-array binary search for LoadLens Algorithm Lab.

This is a **separate educational demonstration** — the workload allocation
optimizer does NOT use or depend on this module in any way.

Problem statement
-----------------
Given a strictly increasing array that has been rotated at an unknown pivot,
locate a target value using binary search in O(log n) time.

Algorithm
---------
At every step, one half of the remaining array is guaranteed to be sorted:

- If `arr[low] <= arr[mid]`, the left half [low, mid] is sorted.
  - If target is in [arr[low], arr[mid]], search left; else search right.
- Otherwise, the right half [mid+1, high] is sorted.
  - If target is in [arr[mid+1], arr[high]], search right; else search left.

Edge cases handled
------------------
- Empty array → index=-1, not found.
- Single element → compare directly.
- No rotation (pivot=0) → treated correctly by the general algorithm.
- Rotation at boundary (pivot=n-1) → treated correctly.
- Target at first or last position.
- Target absent → index=-1.
- Negative integers → supported.
- Duplicates → rejected (makes the above half-selection ambiguous; a
  separate algorithm like Boyer–Moore or linear scan would be needed).
"""

from __future__ import annotations

from typing import List, Sequence

from loadlens.models import RotatedSearchResult


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def validate_rotated_array(arr: Sequence[int]) -> List[int]:
    """Validate that *arr* is a rotation of a strictly increasing array.

    Rules:
    - All elements must be integers.
    - No duplicates allowed (makes pivot detection ambiguous).
    - Must be a rotation of a sorted array: exactly one "descent" (arr[i] > arr[i+1]).

    Args:
        arr: Candidate array.

    Returns:
        Validated list[int].

    Raises:
        ValueError: With a user-readable message on any rule violation.
    """
    lst = list(arr)
    if not lst:
        return lst  # empty is allowed; search will return "not found"

    if len(set(lst)) != len(lst):
        raise ValueError(
            "The array contains duplicate values. "
            "Rotated binary search requires a strictly increasing (no-duplicate) array."
        )

    # Count descents: positions where arr[i] > arr[i+1]
    descents = sum(1 for i in range(len(lst) - 1) if lst[i] > lst[i + 1])
    if descents > 1:
        raise ValueError(
            f"The array has {descents} descents and is not a valid rotation of a "
            "strictly increasing array. At most one descent is allowed."
        )
    return lst


def generate_rotated_array(n: int, offset: int) -> List[int]:
    """Generate a sorted array of n consecutive integers rotated by *offset*.

    Args:
        n: Number of elements (>= 1).
        offset: Rotation offset in [0, n-1].

    Returns:
        Rotated list, e.g. [3,4,5,0,1,2] for n=6, offset=3.
    """
    if n <= 0:
        return []
    base = list(range(n))
    offset = offset % n
    return base[offset:] + base[:offset]


# ---------------------------------------------------------------------------
# Search algorithm
# ---------------------------------------------------------------------------


def rotated_binary_search(arr: Sequence[int], target: int) -> RotatedSearchResult:
    """Search for *target* in a rotated strictly increasing array.

    Args:
        arr: A rotation of a strictly increasing integer array (no duplicates).
             Must be pre-validated with validate_rotated_array.
        target: The integer to find.

    Returns:
        RotatedSearchResult with index (-1 if not found) and a full step trace.
    """
    lst = list(arr)
    trace: list[dict] = []

    if not lst:
        return RotatedSearchResult(array=lst, target=target, index=-1, found=False, trace=[])

    low, high = 0, len(lst) - 1

    while low <= high:
        mid = (low + high) // 2
        step: dict = {
            "low": low,
            "mid": mid,
            "high": high,
            "arr_low": lst[low],
            "arr_mid": lst[mid],
            "arr_high": lst[high],
        }

        if lst[mid] == target:
            step["decision"] = "found"
            step["half_chosen"] = "—"
            trace.append(step)
            return RotatedSearchResult(
                array=lst, target=target, index=mid, found=True, trace=trace
            )

        # Determine which half is sorted
        if lst[low] <= lst[mid]:
            # Left half [low, mid] is sorted
            if lst[low] <= target < lst[mid]:
                step["decision"] = "search left (left half sorted, target in range)"
                step["half_chosen"] = "left"
                trace.append(step)
                high = mid - 1
            else:
                step["decision"] = "search right (left half sorted, target not in range)"
                step["half_chosen"] = "right"
                trace.append(step)
                low = mid + 1
        else:
            # Right half [mid+1, high] is sorted
            if lst[mid] < target <= lst[high]:
                step["decision"] = "search right (right half sorted, target in range)"
                step["half_chosen"] = "right"
                trace.append(step)
                low = mid + 1
            else:
                step["decision"] = "search left (right half sorted, target not in range)"
                step["half_chosen"] = "left"
                trace.append(step)
                high = mid - 1

    trace.append({"low": low, "mid": -1, "high": high, "decision": "not found", "half_chosen": "—"})
    return RotatedSearchResult(array=lst, target=target, index=-1, found=False, trace=trace)
