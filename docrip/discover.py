"""
discover.py
Device discovery and selection pipeline:
- Exclude boot/live media
- Assemble layers (handled in layers.py) then enumerate with lsblk (JSON)
- Encrypted-at-rest detection heuristics (blkid)
- Filter by filesystem allowlist/denylist and size threshold
- Assign (diskno, partno) for stable naming
"""

from __future__ import annotations
import json, re
from pathlib import Path
from typing import List, Dict, Any
from .types import Config, Volume
from .util import run
from .layers import pk_disk_of


def find_boot_devices() -> set[str]:
    """Identify and exclude the live-USB root device and common mountpoints."""
    exclude = set()
    rc, out = run(["findmnt", "-no", "SOURCE", "/"], capture=True)
    if rc == 0:
        src = out.strip()
        if src.startswith("/dev/"):
            exclude.add(src)
            m = re.match(r"^(/dev/[a-z]+)", src)
            if m:
                exclude.add(m.group(1))
    for mp in ("/cdrom", "/isodevice"):
        rc, out = run(["findmnt", "-no", "SOURCE", mp], capture=True)
        if rc == 0 and out.strip().startswith("/dev/"):
            exclude.add(out.strip())
    return exclude


def lsblk_json() -> Dict[str, Any]:
    rc, out = run(
        [
            "lsblk",
            "-b",
            "-J",
            "-o",
            "NAME,KNAME,PATH,TYPE,SIZE,FSTYPE,FSVER,LABEL,UUID,MOUNTPOINT,RM,RO,MODEL,TRAN",
        ],
        capture=True,
    )
    if rc != 0:
        raise RuntimeError(f"lsblk command failed (rc={rc}). This usually requires root access or proper block device permissions.")
    try:
        return json.loads(out)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"lsblk output is not valid JSON: {e}")


def blkid_export(dev: str) -> Dict[str, str]:
    rc, out = run(["blkid", "-o", "export", dev], capture=True)
    if rc != 0:
        return {}
    ans = {}
    for line in out.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            ans[k.strip()] = v.strip()
    return ans


def is_encrypted(dev: str, fstype: str) -> bool:
    """Heuristic: identify at-rest encryption we should not open."""
    if fstype == "crypto_LUKS":
        return True
    info = blkid_export(dev)
    t = info.get("TYPE", "").lower()
    label = info.get("LABEL", "").lower()
    if "crypto_luks" in t:
        return True
    if "bitlocker" in t or "bitlocker" in label or "fve" in label:
        return True
    if t == "apfs" and "encrypted" in info.get("APFS_FEATURES", "").lower():
        return True
    if "veracrypt" in label or "truecrypt" in label:
        return True
    return False


def _build_disk_index(blockdevices: List[Dict[str, Any]]) -> Dict[str, int]:
    disks = [f"/dev/{d['name']}" for d in blockdevices if d.get("type") == "disk"]
    return {dev: i for i, dev in enumerate(sorted(disks))}


def collect_volumes(cfg: Config) -> List[Volume]:
    """Return volumes with skip reasons annotated; mounting is handled later."""
    data = lsblk_json()
    exclude = find_boot_devices()
    disks_index = _build_disk_index(data.get("blockdevices", []))
    vols: List[Volume] = []

    def walk(node: Dict[str, Any]):
        path = node.get("path")
        if not path:
            return
        kname = node.get("kname") or node.get("name")
        fstype = (node.get("fstype") or "").lower()
        size = int(node.get("size") or 0)
        t = node.get("type")
        uuid = node.get("uuid")
        model = node.get("model")
        consider = {"part", "lvm", "raid0", "raid1", "raid10", "crypt", "rom"}
        if t in consider or (t == "disk" and fstype):
            enc = is_encrypted(path, fstype) if cfg.skip_if_encrypted else False
            parent_disk = pk_disk_of(path) or ("/dev/" + kname if t == "disk" else None)
            diskno = disks_index.get(parent_disk, 0)
            m = re.search(r"(\d+)$", kname or "")
            partno = int(m.group(1)) if m else 0
            vols.append(
                Volume(path, kname, fstype, size, t, uuid, enc, diskno, partno, model)
            )
        for ch in node.get("children") or []:
            walk(ch)

    for n in data.get("blockdevices", []):
        walk(n)

    # Apply filters and annotate skip reasons
    min_bytes = cfg.min_partition_size_gb * (1024**3)
    for v in vols:
        reason = None
        if v.path in exclude or Path(v.path).name in cfg.avoid_devices:
            reason = "boot/avoid"
        elif v.fstype in cfg.skip_fstypes:
            reason = f"skip_fstype:{v.fstype}"
        elif cfg.include_fstypes and (v.fstype not in cfg.include_fstypes):
            reason = f"unsupported_fstype:{v.fstype}"
        elif cfg.skip_if_encrypted and v.encrypted:
            reason = "encrypted"
        elif v.size_bytes < min_bytes:
            reason = f"too_small<{cfg.min_partition_size_gb}G"
        v.skip_reason = reason
    return vols


def print_plan(vols: List[Volume]) -> None:
    """Human-readable summary for --list."""
    print(
        f"{'DEVICE':<20} {'FS':<8} {'SIZE(GB)':>9} {'DISK':>4} {'PART':>4} {'STATUS':<20}"
    )
    for v in sorted(vols, key=lambda x: (x.diskno, x.partno, x.path)):
        gb = v.size_bytes / (1024**3)
        status = v.skip_reason or "process"
        print(
            f"{v.path:<20} {v.fstype or '-':<8} {gb:>9.1f} {v.diskno:>4} {v.partno:>4} {status:<20}"
        )
