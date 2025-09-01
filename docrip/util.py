"""
util.py
Cross-cutting utilities:
- Process execution (list-of-args or bash -lc string) with dry-run support
- PATH helper (checked in bundle.py)
- Small helpers: clamp, time/host, JSON writing, token derivation
"""
from __future__ import annotations
import hashlib, json, os, re, shlex, shutil, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

def run(cmd, check=True, capture=False, env=None, dry=False):
    """
    Execute a command.
    - If cmd is a string, run via /bin/bash -lc (required for process substitution like tee >()).
    - Returns (rc, output_str).
    """
    if isinstance(cmd, str):
        cmd_list = ["/bin/bash", "-lc", cmd]
    else:
        cmd_list = cmd
    if dry:
        print("[dry-run]", cmd if isinstance(cmd, str) else " ".join(shlex.quote(c) for c in cmd_list))
        return 0, ""
    try:
        if capture:
            out = subprocess.check_output(cmd_list, stderr=subprocess.STDOUT, env=env)
            return 0, out.decode("utf-8", "replace")
        else:
            rc = subprocess.call(cmd_list, env=env)
            return rc, ""
    except subprocess.CalledProcessError as e:
        return e.returncode, e.output.decode("utf-8","replace") if e.output else ""

def which_or_warn(name: str) -> bool:
    """Check if command exists (either in PATH or in the bundled bin/ which is already prepended)."""
    p = shutil.which(name)
    if not p:
        print(f"[warn] missing utility: {name} (not found in PATH)")
    return bool(p)

def clamp(lo, x, hi): return max(lo, min(x, hi))
def utc_datestr(fmt):  return datetime.now(timezone.utc).strftime(fmt)
def ensure_dir(p: Path): p.mkdir(parents=True, exist_ok=True)

def write_json(path: Path, obj):
    ensure_dir(path.parent)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=True))
    tmp.replace(path)

def base36_digest5(s: str) -> str:
    """Deterministic 5-char base36 token from sha256(s)."""
    h = hashlib.sha256(s.encode("utf-8")).digest()
    n = int.from_bytes(h[:8], "big")
    chars = "0123456789abcdefghijklmnopqrstuvwxyz"
    out = []
    for _ in range(6):
        out.append(chars[n % 36]); n //= 36
    return "".join(out)[:5]

def host_identifier(prefer: str = "machine-id") -> str:
    """Return a stable identifier for the current machine (machine-id, DMI UUID, or hostname)."""
    if prefer == "machine-id":
        for p in (Path("/etc/machine-id"), Path("/sys/class/dmi/id/product_uuid")):
            try:
                s = p.read_text().strip()
                if s: return s
            except: pass
    return os.uname().nodename
