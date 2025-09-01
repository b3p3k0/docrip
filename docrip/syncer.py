"""
syncer.py
Rsync directory (containing chunk files and manifests) to the remote server.
Uses --partial --inplace --append-verify --mkpath for resilient resume semantics.
"""

from __future__ import annotations
import shlex
from pathlib import Path
from .types import Config
from .util import run, ensure_dir


def rsync_dir(
    cfg: Config, local_dir: Path, date_str: str, token: str, dry: bool = False
) -> bool:
    dest = f"{cfg.server_rsync_remote}/{date_str}/{token}/"
    ensure_dir(local_dir)
    ssh_opt = f"-i {shlex.quote(cfg.server_ssh_key)} -p {cfg.server_port}"
    bw = f"--bwlimit={cfg.rsync_bwlimit_kbps}" if cfg.rsync_bwlimit_kbps > 0 else ""
    cmd = f'rsync -r {bw} --partial --inplace --append-verify --mkpath -e "ssh {ssh_opt}" {shlex.quote(str(local_dir))}/ {shlex.quote(dest)}'
    rc, _ = run(cmd, dry=dry)
    return rc == 0
