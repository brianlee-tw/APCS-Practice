#!/usr/bin/env python3
"""Registered local semantic-output judges; never evaluate user-supplied code.

Checker selection is bound by TestAssetStore to the exact official source
identity; this module itself has no network, filesystem writes or subprocess.
"""
from __future__ import annotations

import re

CHECKER_EXACT = "EXACT"
CHECKER_CF_977C = "CF_977C_ANY_X"
CF_977C_SOURCE = "codeforces"
CF_977C_EXTERNAL_ID = "977C"
CF_977C_URL = "https://codeforces.com/problemset/problem/977/C"
MAX_VALUE = 10**9

_INTEGER = re.compile(r"(?:0|[1-9][0-9]*|-[1-9][0-9]*)\Z", re.ASCII)


def check_cf_977c(input_text: str, actual_output: str) -> bool:
    """Accept any legal x, or -1 only when the input admits no legal x.

    This is not equality with the sample's illustrative output.
    Malformed input or output fails closed; each output must be one integer.
    """
    try:
        raw = input_text.split()
        if len(raw) < 3:
            return False
        n, k = int(raw[0]), int(raw[1])
        if not (1 <= n <= 200_000 and 0 <= k <= n and len(raw) == n + 2):
            return False
        values = [int(token) for token in raw[2:]]
        if any(not 1 <= value <= MAX_VALUE for value in values):
            return False
        parts = actual_output.split()
        if len(parts) != 1 or not _INTEGER.fullmatch(parts[0]):
            return False
        x = int(parts[0])
        if x != -1:
            return 1 <= x <= MAX_VALUE and sum(v <= x for v in values) == k

        # For a negative answer, validate impossibility, including k=0
        # (minimum 1 can make it impossible) and duplicate boundary values.
        ordered = sorted(values)
        if k == 0:
            feasible = ordered[0] > 1
        elif k == n:
            feasible = True
        else:
            feasible = ordered[k - 1] < ordered[k]
        return not feasible
    except (ValueError, OverflowError, TypeError, IndexError):
        return False


def check_semantic_output(
    checker: str,
    input_text: str,
    actual_output: str,
) -> bool:
    if checker == CHECKER_CF_977C:
        return check_cf_977c(input_text, actual_output)
    # Never fall back to fixed-output comparison for an unrecognized checker.
    return False
