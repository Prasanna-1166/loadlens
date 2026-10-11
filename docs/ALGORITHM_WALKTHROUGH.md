# Algorithm Walkthrough — LoadLens

## Overview

LoadLens solves the **Workload Allocation Problem**: given an ordered list of tasks with positive integer durations and a fixed number of workers, find the contiguous partition that minimises the maximum worker workload.

This document explains the algorithm well enough for a technical interview.

---

## Problem Formulation

**Input:**
- `d[0..n-1]` — ordered task durations, all positive integers.
- `k` — number of workers (1 ≤ k ≤ n).

**Constraints:**
- Each task goes to exactly one worker.
- Task order is preserved (no sorting or reordering).
- Each worker receives a non-empty contiguous slice.

**Objective:** minimise `max(sum(d) for each worker's slice)`.

---

## Why Not Brute Force?

For n=1000 tasks and k=10 workers, the number of ways to choose 9 split points from 999 gaps is `C(999, 9) ≈ 2.8 × 10²⁶` — impossibly large.

LoadLens uses **Binary Search on the Answer** to solve this in O(n log R).

---

## Algorithm

### Step 1: Establish bounds for the answer

The answer (optimal capacity) must lie in `[lower, upper]`:

- **Lower bound:** `max(max(d), ⌈total/k⌉)`
  - No capacity below `max(d)` can work (one task alone exceeds it).
  - No capacity below `⌈total/k⌉` works (k workers together can't cover the total).
- **Upper bound:** `sum(d)` (one worker takes everything — always feasible).

### Step 2: Feasibility check — O(n)

For a candidate capacity `C`, greedily assign tasks left-to-right:

```python
def required_workers(durations, C):
    groups = 1
    running = 0
    for d in durations:
        if running + d > C:
            groups += 1
            running = d
        else:
            running += d
    return groups
```

A candidate `C` is **feasible** if `required_workers(d, C) ≤ k`.

### Step 3: Monotonicity (why binary search is valid)

All durations are positive integers. Increasing `C` can only *merge* adjacent groups (a group that needed a split at capacity C may not need it at C+1). It can never cause a new required split.

Therefore, as C increases from `lower` to `upper`:
- `required_workers(C)` is **monotonically non-increasing**.
- The feasibility predicate `required_workers(C) ≤ k` is **monotonically non-decreasing** (False then True, exactly one transition).

This is precisely the condition that makes binary search valid for finding the minimum feasible C.

### Step 4: Binary search — O(log R)

```python
low, high = lower_bound, upper_bound
while low < high:
    mid = (low + high) // 2
    if required_workers(durations, mid) <= k:
        high = mid          # mid is feasible, try smaller
    else:
        low = mid + 1       # mid is not feasible, need more room
# Answer is low == high
```

### Step 5: Group reconstruction — O(n)

Replay the greedy scan with `C = optimal_capacity` to produce the exact `k` groups.

If the greedy scan uses fewer than `k` groups (can happen when `optimal_capacity` is slightly larger than the minimum needed), subdivide the largest groups by inserting additional split points — preserving order and keeping each sub-group non-empty.

---

## Worked Example

**Input:** J1=7, J2=2, J3=5, J4=10, J5=8 — Total=32, Workers=3

**Bounds:**
- lower = max(10, ⌈32/3⌉) = max(10, 11) = **11**
- upper = **32**

**Binary search trace:**

| Step | low | high | mid | Workers needed | Feasible? | Action |
|------|-----|------|-----|---------------|-----------|--------|
| 1    | 11  | 32   | 21  | 2             | ✅ Yes    | high = 21 |
| 2    | 11  | 21   | 16  | 2             | ✅ Yes    | high = 16 |
| 3    | 11  | 16   | 13  | 4             | ❌ No     | low = 14  |
| 4    | 14  | 16   | 15  | 3             | ✅ Yes    | high = 15 |
| 5    | 14  | 15   | 14  | 3             | ✅ Yes    | high = 14 |
| —    | 14  | 14   | —   | converged     | ✅        | **answer = 14** |

**Verification — greedy with C=14:**
- W1: J1(7) + J2(2) + J3(5) = 14 ✅
- W2: J4(10) → next task J5(8) would make 18 > 14, so new group: W3: J5(8)
- Final: W1=14, W2=10, W3=8. Max = **14** ✅

---

## Complexity

| Phase | Time | Space |
|-------|------|-------|
| Feasibility check | O(n) | O(1) |
| Binary search | O(log R) iterations | O(log R) trace |
| Full solver | **O(n log R)** | O(n) |
| Reconstruction | O(n) | O(n) |

Where `R = upper - lower + 1 ≤ sum(d)`.

---

## Edge Cases

| Case | Handling |
|------|---------|
| k=1 | Trivially optimal = total. No binary search needed. |
| k=n | Each task alone. Optimal = max(d). |
| All equal durations | Perfectly balanced partition. Works correctly. |
| One huge task | Lower bound = max(d). That task must go to one worker. |
| Greedy uses < k groups | Reconstruction subdivides the largest groups safely. |

---

## Correctness Guarantee

The production solver is cross-validated against an independent exhaustive brute-force reference solver (enumerating all `C(n-1,k-1)` split placements) for small inputs (n ≤ 9) in the test suite, including 60 seeded random cases.
