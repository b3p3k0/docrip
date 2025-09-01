"""
mounter.py
Read-only mount recipes and umount helper.

We deliberately avoid fsck/journal replays and mount with nodev/nosuid/noexec where compatible.
APFS requires apfs-fuse; ZFS mounting is handled via zpool/zfs (not here).
"""

from __future__ import annotations
from pathlib import Path
import shutil
from .util import run
from .types import Volume


def mount_ro(v: Volume, mp: Path, dry: bool = False) -> bool:
    mp.mkdir(parents=True, exist_ok=True)
    fs = v.fstype
    if fs in ("ext2", "ext3", "ext4"):
        cmd = [
            "mount",
            "-t",
            "ext4",
            "-o",
            "ro,noload,nodev,nosuid,noexec",
            v.path,
            str(mp),
        ]
    elif fs == "xfs":
        cmd = [
            "mount",
            "-t",
            "xfs",
            "-o",
            "ro,norecovery,nodev,nosuid,noexec",
            v.path,
            str(mp),
        ]
    elif fs == "btrfs":
        cmd = ["mount", "-t", "btrfs", "-o", "ro,nodev,nosuid,noexec", v.path, str(mp)]
    elif fs == "ntfs":
        cmd = ["ntfs-3g", "-o", "ro,nodev,nosuid,noexec", v.path, str(mp)]
    elif fs == "vfat":
        cmd = [
            "mount",
            "-t",
            "vfat",
            "-o",
            "ro,uid=0,gid=0,umask=022,nodev,nosuid,noexec",
            v.path,
            str(mp),
        ]
    elif fs == "exfat":
        cmd = ["mount", "-t", "exfat", "-o", "ro,nodev,nosuid,noexec", v.path, str(mp)]
    elif fs == "hfs":
        cmd = ["mount", "-t", "hfs", "-o", "ro,nodev,nosuid,noexec", v.path, str(mp)]
    elif fs == "hfsplus":
        cmd = [
            "mount",
            "-t",
            "hfsplus",
            "-o",
            "ro,force,nodev,nosuid,noexec",
            v.path,
            str(mp),
        ]
    elif fs == "apfs":
        if shutil.which("apfs-fuse"):
            cmd = ["apfs-fuse", "--readonly", v.path, str(mp)]
        else:
            print(f"[skip] APFS but apfs-fuse missing: {v.path}")
            return False
    elif fs == "zfs":
        print(f"[info] ZFS handled via zpool/zfs; skip direct mount {v.path}")
        return False
    else:
        print(f"[skip] unsupported fstype: {fs} for {v.path}")
        return False
    rc, _ = run(cmd, dry=dry)
    if rc != 0:
        print(f"[error] mount failed: {v.path} -> {mp}")
        return False
    return True


def umount(mp: Path, dry: bool = False) -> None:
    if mp.exists():
        run(["umount", "-f", "--lazy", str(mp)], dry=dry)
        try:
            mp.rmdir()
        except:
            pass
