#!/usr/bin/env python3
"""Command-line entry point kept for existing callers; the module is login_flow.py."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from login_flow import main  # noqa: E402

if __name__ == "__main__":
    main()
