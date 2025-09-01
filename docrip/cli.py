#!/usr/bin/env python3
"""
cli.py
Command-line interface for docrip.
Parses arguments, loads config, and invokes the orchestrator.
"""
from __future__ import annotations
import argparse, sys
from pathlib import Path
from .bundle import DEFAULT_CONFIG_PATH
from .config import find_config, load_config
from .orchestrator import run_plan

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="docrip: discover, mount RO, archive->chunk->rsync (bundled)")
    ap.add_argument("--config", default=None, help=f"path to docrip.toml (default: {DEFAULT_CONFIG_PATH} then /etc/docrip.toml)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--workers", type=int, default=None, help="override concurrency")
    ap.add_argument("--only", help="comma-separated /dev paths to include")
    ap.add_argument("--exclude-dev", help="comma-separated base device names to skip (e.g., sda,nvme0n1)")
    args = ap.parse_args(argv)

    cfg_path = find_config(args.config)
    cfg = load_config(cfg_path)

    # extend avoid list from CLI once
    if args.exclude_dev:
        cfg.avoid_devices.extend([x for x in args.exclude_dev.split(",") if x])

    only_set = set(args.only.split(",")) if args.only else None
    return run_plan(cfg, only_set, args.list, args.workers, args.dry_run)

if __name__ == "__main__":
    sys.exit(main())
