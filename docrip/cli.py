#!/usr/bin/env python3
"""
cli.py
Command-line interface for docrip.
Parses arguments, loads config, and invokes the orchestrator.
"""
from __future__ import annotations
import argparse, os, sys
from pathlib import Path
from .bundle import DEFAULT_CONFIG_PATH
from .config import find_config, load_config
from .orchestrator import run_plan


def check_root_access() -> None:
    """Check if running as root and provide witty error message if not."""
    if os.geteuid() != 0:
        user = os.environ.get('USER', 'mortal')
        print(f"\n💥 Hold up there, {user}! This power is too great for mere mortals! 💥")
        print(f"\n🔒 docrip needs root privileges to:")
        print(f"   • Mount filesystems read-only")
        print(f"   • Access block devices directly")
        print(f"   • Create directories in /var/log and /mnt")
        print(f"\n✨ Try this instead: sudo {' '.join(sys.argv)}")
        print(f"\n(Don't worry - it's read-only operations, we're not here to break things! 😉)\n")
        sys.exit(1)


def validate_arguments(args) -> None:
    """Validate CLI arguments and provide helpful error messages."""
    # Validate workers
    if args.workers is not None and args.workers < 1:
        print(f"❌ Error: --workers must be a positive integer, got {args.workers}")
        print(f"💡 Hint: Try --workers 4 for example")
        sys.exit(1)
    
    # Validate --only format
    if args.only:
        devices = [d.strip() for d in args.only.split(",") if d.strip()]
        invalid_devices = [d for d in devices if not d.startswith("/dev/")]
        if invalid_devices:
            print(f"❌ Error: --only devices must start with /dev/, invalid: {', '.join(invalid_devices)}")
            print(f"💡 Hint: Try --only /dev/sdb1,/dev/nvme0n1p2")
            sys.exit(1)
    
    # Validate --exclude-dev format  
    if args.exclude_dev:
        devices = [d.strip() for d in args.exclude_dev.split(",") if d.strip()]
        invalid_devices = [d for d in devices if "/" in d]
        if invalid_devices:
            print(f"❌ Error: --exclude-dev should be device names only (no /dev/ prefix), invalid: {', '.join(invalid_devices)}")
            print(f"💡 Hint: Try --exclude-dev sda,nvme0n1")
            sys.exit(1)


def main(argv=None) -> int:
    try:
        ap = argparse.ArgumentParser(
            description="docrip: discover, mount RO, archive->chunk->rsync (bundled)",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="\nNeed help? This tool requires root privileges to access block devices safely."
        )
        ap.add_argument(
            "--config",
            default=None,
            help=f"path to docrip.toml (default: {DEFAULT_CONFIG_PATH} then /etc/docrip.toml)",
        )
        ap.add_argument("--dry-run", action="store_true", help="show commands without executing")
        ap.add_argument("--list", action="store_true", help="show discovery plan and skip reasons")
        ap.add_argument("--workers", type=int, default=None, help="override concurrency (must be positive)")
        ap.add_argument("--only", help="comma-separated /dev paths to include (e.g., /dev/sdb1,/dev/nvme0n1p2)")
        ap.add_argument(
            "--exclude-dev",
            help="comma-separated device names to skip (e.g., sda,nvme0n1 - no /dev/ prefix)",
        )
        
        args = ap.parse_args(argv)
        
        # Validate arguments early
        validate_arguments(args)
        
        # Check for root access unless just listing or help
        if not args.list:
            check_root_access()
        
        # Find and load config with error handling
        try:
            cfg_path = find_config(args.config)
            cfg = load_config(cfg_path)
        except FileNotFoundError as e:
            print(f"❌ Error: {e}")
            if args.config:
                print(f"💡 Hint: Check the path or run './setup.sh demo-config' to generate a template")
            else:
                print(f"💡 Hint: Create {cfg_path} or run './setup.sh demo-config' to generate a template")
            return 1
        except Exception as e:
            print(f"❌ Error: Invalid configuration file {cfg_path}: {e}")
            print(f"💡 Hint: Check TOML syntax with 'python3 -c \"import tomllib; tomllib.load(open(\"{cfg_path}\", \"rb\"))\"'")
            return 1
        
        # Validate required config fields
        if not args.list and not args.dry_run:
            if not cfg.server_rsync_remote:
                print(f"❌ Error: Missing required config: server.rsync_remote")
                print(f"💡 Hint: Add 'rsync_remote = \"user@host:/path\"' to [server] section in {cfg_path}")
                return 1
        
        # extend avoid list from CLI once
        if args.exclude_dev:
            cfg.avoid_devices.extend([x.strip() for x in args.exclude_dev.split(",") if x.strip()])
        
        only_set = None
        if args.only:
            only_set = set(d.strip() for d in args.only.split(",") if d.strip())
        
        return run_plan(cfg, only_set, args.list, args.workers, args.dry_run)
        
    except KeyboardInterrupt:
        print(f"\n\n⚡ Interrupted by user. No harm done!")
        return 130
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        print(f"💡 Hint: Run with --dry-run or --list first to check configuration")
        return 1


if __name__ == "__main__":
    sys.exit(main())
