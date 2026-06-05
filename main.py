#!/usr/bin/env python3
"""
RPD Document Parser - Main Entry Point

This script provides both CLI and API modes for parsing university curriculum documents.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.cli.main import main

if __name__ == "__main__":
    main()