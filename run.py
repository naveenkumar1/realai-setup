"""
Entry point — run from project root:
    python run.py --rent-roll data/... --financials data/...
"""
import sys
import os

# Ensure project root is on the path so 'src' package is found
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.main import main

if __name__ == '__main__':
    main()
