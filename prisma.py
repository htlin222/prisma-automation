#!/usr/bin/env python
"""
Main entry point for PRISMA workflow automation.

This script provides a convenient way to run the PRISMA CLI.
"""

import sys
import os

# Add the project root directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.python.cli import main

if __name__ == "__main__":
    sys.exit(main())
