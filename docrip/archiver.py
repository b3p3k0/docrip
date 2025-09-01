"""
archiver.py
Functions to:
- Build the find(1) command that emits a NUL-separated list honoring max_file_size
- Select compressor command (zstd/pigz) with thread count
Note: tar will read the NUL-separated list via --null -T - and -C <mp>.
"""

from __future__ import annotations
import shlex
from pathlib import Path
from .types import Config


def build_find_cmd(mp: Path, max_mb: int) -> str:
    """
    Emit RELATIVE paths by 'cd' into the mountpoint.
    Include directories and symlinks always; include files under size limit (if >0).
    """
    if max_mb and max_mb > 0:
        return (
            f"cd {shlex.quote(str(mp))} && find . -xdev "
            r"\( -type d -print0 -o -type l -print0 -o \( -type f -size -%dM -print0 \) \)"
            % max_mb
        )
    else:
        return (
            f"cd {shlex.quote(str(mp))} && find . -xdev "
            r"\( -type d -print0 -o -type l -print0 -o -type f -print0 \)"
        )


def compressor_cmd(cfg: Config, threads: int) -> str:
    lvl = str(cfg.compression_level)
    if cfg.compressor == "zstd":
        return f"zstd -T{threads} -{lvl}"
    if cfg.compressor == "pigz":
        return f"pigz -p {threads} -{lvl}"
    raise ValueError("Unsupported compressor")
