#!/usr/bin/env python3
"""
main.py - Entry point for docrip that works in both development and bundled modes.
"""
import sys
import os
from pathlib import Path

# Add the project root to Python path for development mode
if __name__ == "__main__":
    # Get the directory containing this script
    script_dir = Path(__file__).resolve().parent
    
    # Add to Python path if not already there
    if str(script_dir) not in sys.path:
        sys.path.insert(0, str(script_dir))
    
    # Import and run the CLI
    try:
        from docrip.cli import main
        sys.exit(main())
    except ImportError as e:
        print(f"Error importing docrip modules: {e}")
        print("Make sure you're running from the project root directory.")
        sys.exit(1)