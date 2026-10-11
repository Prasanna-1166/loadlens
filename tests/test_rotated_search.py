"""Tests for the rotated sorted-array binary search.

Covers:
- Valid rotations at various offsets
- Empty input
- Single element
- No rotation (offset=0)
- Rotation at boundary (offset=n-1)
- First and last element as targets
- Absent target
- Negative integers
- Invalid ordering (not a rotation of a sorted array)
- Duplicate values (rejected)
"""

from __future__ import annotations

import pytest

from loadlens.algorithms.rotated_search import (
    generate_rotated_array,
    rotated_binary_search,
    validate_rotated_array,
)
from loadlens.models import RotatedSearchResult


# ── Validation ────────────────────────────────────────────────────────────────

class TestValidateRotatedArray:
    def test_valid_unrotated(self):
        result = validate_rotated_array([1, 2, 3, 4, 5])
        assert result == [1, 2, 3, 4, 5]

    def test_valid_rotated(self):
        result = validate_rotated_array([4, 5, 6, 7, 0, 1, 2])
        assert result == [4, 5, 6, 7, 0, 1, 2]

    def test_empty_is_valid(self):
        assert validate_rotated_array([]) == []

    def test_single_element_valid(self):
        assert validate_rotated_array([42]) == [42]

    def test_duplicates_rejected(self):
        with pytest.raises(ValueError, match="duplicate"):
            validate_rotated_array([1, 2, 2, 3])

    def test_two_descents_rejected(self):
        with pytest.raises(ValueError, match="descent"):
            validate_rotated_array([3, 1, 5, 4])

    def test_negative_values_valid(self):
        result = validate_rotated_array([-3, -1, 0, 2, 4])
        assert result == [-3, -1, 0, 2, 4]

    def test_rotation_with_negatives(self):
        result = validate_rotated_array([0, 2, 4, -3, -1])
        assert result == [0, 2, 4, -3, -1]


# ── generate_rotated_array ────────────────────────────────────────────────────

class TestGenerateRotatedArray:
    def test_no_rotation(self):
        assert generate_rotated_array(5, 0) == [0, 1, 2, 3, 4]

    def test_full_rotation(self):
        arr = generate_rotated_array(5, 5)
        assert arr == [0, 1, 2, 3, 4]  # offset % n = 0

    def test_partial_rotation(self):
        assert generate_rotated_array(6, 3) == [3, 4, 5, 0, 1, 2]

    def test_single_element(self):
        assert generate_rotated_array(1, 0) == [0]

    def test_empty(self):
        assert generate_rotated_array(0, 0) == []


# ── rotated_binary_search ─────────────────────────────────────────────────────

class TestRotatedBinarySearch:
    def _found_at(self, arr, target) -> int:
        result = rotated_binary_search(arr, target)
        assert result.found is True
        return result.index

    def _not_found(self, arr, target) -> None:
        result = rotated_binary_search(arr, target)
        assert result.found is False
        assert result.index == -1

    def test_empty_array(self):
        self._not_found([], 5)

    def test_single_element_found(self):
        assert self._found_at([7], 7) == 0

    def test_single_element_not_found(self):
        self._not_found([7], 9)

    def test_unrotated_found(self):
        idx = self._found_at([1, 2, 3, 4, 5], 3)
        assert idx == 2

    def test_unrotated_not_found(self):
        self._not_found([1, 2, 3, 4, 5], 6)

    def test_rotated_find_target_in_left(self):
        arr = [4, 5, 6, 7, 0, 1, 2]
        idx = self._found_at(arr, 5)
        assert arr[idx] == 5

    def test_rotated_find_target_in_right(self):
        arr = [4, 5, 6, 7, 0, 1, 2]
        idx = self._found_at(arr, 1)
        assert arr[idx] == 1

    def test_first_element_target(self):
        arr = [4, 5, 6, 7, 0, 1, 2]
        idx = self._found_at(arr, 4)
        assert idx == 0

    def test_last_element_target(self):
        arr = [4, 5, 6, 7, 0, 1, 2]
        idx = self._found_at(arr, 2)
        assert idx == 6

    def test_absent_target(self):
        self._not_found([4, 5, 6, 7, 0, 1, 2], 3)

    def test_negative_values(self):
        arr = [-1, 0, 2, 4, -5, -3]
        idx = self._found_at(arr, -3)
        assert arr[idx] == -3

    def test_all_negative(self):
        arr = [-3, -1, -5]
        # -5, -3, -1 sorted; rotated at offset 2 → [-1, -5, -3] — invalid (2 descents)
        # Use a valid rotation: [-3, -1] rotated at 1 → [-1, -3] — 1 descent ok
        arr = [-1, -3]  # descent at 0: -1 > -3 ✓
        idx = self._found_at(arr, -3)
        assert arr[idx] == -3

    def test_rotation_at_boundary(self):
        """Last element as pivot (rotation offset = n-1)."""
        arr = generate_rotated_array(5, 4)  # [4, 0, 1, 2, 3]
        for val in arr:
            idx = self._found_at(arr, val)
            assert arr[idx] == val

    def test_trace_not_empty(self):
        result = rotated_binary_search([4, 5, 6, 7, 0, 1, 2], 5)
        assert len(result.trace) > 0

    def test_two_element_found_first(self):
        idx = self._found_at([2, 1], 2)
        assert idx == 0

    def test_two_element_found_second(self):
        idx = self._found_at([2, 1], 1)
        assert idx == 1
