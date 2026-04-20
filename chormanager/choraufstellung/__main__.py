#!/usr/bin/env python3
"""Entry point for ChorAufstellung standalone app."""

import sys
import os

# Add the choraufstellung directory to path
choraufstellung_dir = os.path.dirname(os.path.abspath(__file__))
if choraufstellung_dir not in sys.path:
    sys.path.insert(0, choraufstellung_dir)

from main import main

if __name__ == "__main__":
    main()