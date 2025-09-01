"""
config.py
Load and validate configuration from TOML (Python 3.11+ tomllib).
Search order:
  1) explicit --config path
  2) adjacent DEFAULT_CONFIG_PATH (bundle root / 'docrip.toml')
  3) /etc/docrip.toml
"""

from __future__ import annotations
import tomllib
from pathlib import Path
from typing import Any, Dict
from .types import Config
from .bundle import DEFAULT_CONFIG_PATH


def _gv(d: Dict[str, Any], path: list[str], default=None):
    cur = d
    for k in path:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


def _load_toml(path: Path) -> Dict[str, Any]:
    with open(path, "rb") as f:
        return tomllib.load(f)


def find_config(path_arg: str | None) -> Path:
    """Pick the best config path based on CLI arg and availability."""
    if path_arg:
        # User explicitly specified a config - it must exist
        p = Path(path_arg)
        if not p.exists():
            raise FileNotFoundError(f"Specified config file does not exist: {path_arg}")
        return p
    
    # Auto-discovery mode - try default locations
    # prefer adjacent to binary
    p = Path(DEFAULT_CONFIG_PATH)
    if p.exists():
        return p
    # fallback to /etc
    p = Path("/etc/docrip.toml")
    return p


def load_config(path: Path) -> Config:
    cfg = _load_toml(path)

    def gv(keys, default=None):
        return _gv(cfg, keys, default)

    return Config(
        server_rsync_remote=gv(["server", "rsync_remote"]),
        server_ssh_key=gv(["server", "ssh_key"]),
        server_port=int(gv(["server", "port"], 22)),
        compressor=gv(["archive", "compressor"], "zstd"),
        compression_level=int(gv(["archive", "compression_level"], 3)),
        chunk_size_mb=int(gv(["archive", "chunk_size_mb"], 4096)),
        stream_direct=bool(gv(["archive", "stream_direct"], False)),
        spool_dir=Path(gv(["archive", "spool_dir"], "/var/tmp/docrip")),
        preserve_xattrs=bool(gv(["archive", "preserve_xattrs"], True)),
        include_fstypes=gv(["discovery", "include_fstypes"], []),
        skip_fstypes=gv(["discovery", "skip_fstypes"], []),
        skip_if_encrypted=bool(gv(["discovery", "skip_if_encrypted"], True)),
        allow_lvm=bool(gv(["discovery", "allow_lvm"], True)),
        allow_raid=bool(gv(["discovery", "allow_raid"], True)),
        min_partition_size_gb=int(gv(["discovery", "min_partition_size_gb"], 256)),
        avoid_devices=gv(["discovery", "avoid_devices"], []),
        max_file_size_mb=int(gv(["filters", "max_file_size_mb"], 100)),
        workers=int(gv(["runtime", "workers"], 0)),
        rsync_bwlimit_kbps=int(gv(["runtime", "rsync_bwlimit_kbps"], 0)),
        log_level=gv(["runtime", "log_level"], "INFO"),
        date_fmt=gv(["naming", "date_fmt"], "%Y%m%d"),
        token_source=gv(["naming", "token_source"], "machine-id"),
        pattern=gv(["naming", "pattern"], "{date}_{token}_d{disk}_p{part}"),
        integrity_algo=gv(["integrity", "algorithm"], "sha256"),
        run_summary_dir=Path(gv(["output", "run_summary_dir"], "/var/log/docrip")),
        per_volume_json=bool(gv(["output", "per_volume_json"], True)),
    )
