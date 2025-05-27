#!/usr/bin/env python3
"""
Agent Registry Entry Point

Provides a simple entry point to run the Agent Registry Service.
"""

import os
import sys

# Add the current directory to the python path to allow imports
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.main import main

if __name__ == "__main__":
    main()
