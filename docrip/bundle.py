"""
bundle.py
Utilities that make the program work as a portable, bundled tool.

Responsibilities
- Determine the "bundle root": where the binary (or script) lives.
- Prefer a local ./bin directory (next to the binary) for helper tools.
- Provide DEFAULT_CONFIG_PATH that points to an adjacent `docrip.toml`.
"""
from __future__ import annotations
import os, sys
from pathlib import Path

def bundle_root() -> Path:
    """
    Return the directory that contains the program.
    - PyInstaller onefile: sys.executable points to the extracted binary; use parent.
    - Source run: Look for main.py or project root containing docrip.toml
    """
    # PyInstaller bundle
    if getattr(sys, "_MEIPASS", None):
        return Path(sys.executable).resolve().parent
    
    # Development mode - find project root
    current = Path(__file__).resolve()
    
    # Look for project root markers (main.py, docrip.toml, etc.)
    for parent in [current.parent.parent] + list(current.parents):
        if (parent / "main.py").exists() or (parent / "docrip.toml").exists():
            return parent
    
    # Fallback to package parent directory
    return current.parent.parent

BUNDLE_DIR: Path = bundle_root()
BIN_DIR: Path = (BUNDLE_DIR / "bin")
DEFAULT_CONFIG_PATH: str = str(BUNDLE_DIR / "docrip.toml")

def prepend_bin_to_path() -> None:
    """Prepend ./bin (next to the binary) to PATH so bundled helpers are preferred."""
    if BIN_DIR.is_dir():
        os.environ["PATH"] = str(BIN_DIR) + ":" + os.environ.get("PATH", "")
