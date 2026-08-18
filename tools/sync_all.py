#!/usr/bin/env python3
"""Backward-compatible wrapper for the v1 sync command."""

from apcs import main

if __name__ == "__main__":
    raise SystemExit(main(["sync"]))
