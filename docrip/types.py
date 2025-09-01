"""
types.py
Dataclasses used across modules: Config, Volume, VolumeResult.

These are intentionally lightweight, serializable, and stable for logging.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Dict, Any

@dataclass
class Config:
    # server
    server_rsync_remote: str
    server_ssh_key: str
    server_port: int
    # archive
    compressor: str
    compression_level: int
    chunk_size_mb: int
    stream_direct: bool
    spool_dir: Path
    preserve_xattrs: bool
    # discovery
    include_fstypes: List[str]
    skip_fstypes: List[str]
    skip_if_encrypted: bool
    allow_lvm: bool
    allow_raid: bool
    min_partition_size_gb: int
    avoid_devices: List[str]
    # filters
    max_file_size_mb: int
    # runtime
    workers: int
    rsync_bwlimit_kbps: int
    log_level: str
    # naming
    date_fmt: str
    token_source: str
    pattern: str
    # integrity and output
    integrity_algo: str
    run_summary_dir: Path
    per_volume_json: bool

@dataclass
class Volume:
    path: str
    kname: str
    fstype: str
    size_bytes: int
    type: str
    uuid: Optional[str]
    encrypted: bool
    diskno: int
    partno: int
    model: Optional[str]
    skip_reason: Optional[str] = None

@dataclass
class VolumeResult:
    device: str
    fstype: str
    size_bytes: int
    name: str
    mountpoint: str
    status: str
    duration_sec: float
    error: Optional[str] = None
    extra: Optional[Dict[str, Any]] = None
