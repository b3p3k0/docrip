"""
layers.py
Storage layers handling (read-only intent):
- Assemble md-RAID: mdadm --assemble --scan --readonly
- Activate LVM VGs: vgchange -ay
- Import ZFS pools (RO): zpool import -a -o readonly=on -N -f
- Helper: pk_disk_of (resolve parent disk of a node)
"""

from __future__ import annotations
from .util import run, which_quiet


def assemble_layers(allow_raid: bool, allow_lvm: bool, dry: bool = False) -> None:
    if allow_raid and which_quiet("mdadm"):
        run(["mdadm", "--assemble", "--scan", "--readonly"], dry=dry)
    if allow_lvm and which_quiet("vgchange"):
        run(["vgchange", "-ay"], dry=dry)
    if which_quiet("zpool"):
        run(["zpool", "import", "-a", "-o", "readonly=on", "-N", "-f"], dry=dry)


def pk_disk_of(dev: str) -> str | None:
    """Walk up PKNAME until reaching a 'disk' node; return /dev/<name>."""
    seen = set()
    cur = dev
    for _ in range(8):
        rc, out = run(["lsblk", "-no", "TYPE,PKNAME", cur], capture=True)
        if rc != 0:
            break
        tokens = (out.split() + ["", ""])[:2]
        t, pk = tokens[0], tokens[1]
        if t == "disk":
            rc2, out2 = run(["lsblk", "-no", "NAME", cur], capture=True)
            name = out2.strip()
            return f"/dev/{name}"
        if not pk or pk in seen:
            break
        seen.add(pk)
        cur = f"/dev/{pk}"
    return None
