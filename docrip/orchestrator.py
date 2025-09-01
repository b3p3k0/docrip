"""
orchestrator.py
Coordinates the end-to-end flow with concurrency:
  - Assemble layers (RO)
  - Discover volumes & apply filters
  - For each volume (largest first):
      mount RO -> archive+chunk -> rsync
  - Write run and per-volume JSON summaries
"""

from __future__ import annotations
import concurrent.futures, os, sys, time
from datetime import datetime, timezone
from pathlib import Path
from typing import List
from .types import Config, Volume, VolumeResult
from .util import (
    ensure_dir,
    write_json,
    utc_datestr,
    base36_digest5,
    host_identifier,
    clamp,
)
from .bundle import DEFAULT_CONFIG_PATH, prepend_bin_to_path
from .layers import assemble_layers
from .discover import collect_volumes, print_plan
from .mounter import mount_ro, umount
from .chunker import make_chunks
from .syncer import rsync_dir


def derive_token(cfg: Config, date_str: str) -> str:
    return base36_digest5(f"{date_str}:{host_identifier(cfg.token_source)}")


def auto_workers(explicit: int) -> int:
    if explicit and explicit > 0:
        return explicit
    cpu = os.cpu_count() or 2
    return clamp(1, cpu // 2, 8)


def comp_threads_for(workers: int) -> int:
    cpu = os.cpu_count() or 2
    return max(1, (cpu // max(1, workers)) - 1)


def process_one(
    cfg: Config, v: Volume, token: str, date_str: str, comp_threads_job: int, dry=False
) -> VolumeResult:
    name = cfg.pattern.format(date=date_str, token=token, disk=v.diskno, part=v.partno)
    work_root = cfg.spool_dir / name
    mp = Path("/mnt") / "docrip" / name
    started = time.time()
    status = "ok"
    error = None
    try:
        if not mount_ro(v, mp, dry=dry):
            status = "mount_failed"
            return VolumeResult(
                v.path,
                v.fstype,
                v.size_bytes,
                name,
                str(mp),
                status,
                round(time.time() - started, 2),
            )
        ok = make_chunks(
            cfg, mp, work_root, compressor_threads=comp_threads_job, dry=dry
        )
        if not ok:
            status = "chunk_failed"
            return VolumeResult(
                v.path,
                v.fstype,
                v.size_bytes,
                name,
                str(mp),
                status,
                round(time.time() - started, 2),
            )
        ok2 = rsync_dir(cfg, work_root, date_str, token, dry=dry)
        status = "ok" if ok2 else "rsync_failed"
        return VolumeResult(
            v.path,
            v.fstype,
            v.size_bytes,
            name,
            str(mp),
            status,
            round(time.time() - started, 2),
        )
    except Exception as e:
        status = "exception"
        error = str(e)
        return VolumeResult(
            v.path,
            v.fstype,
            v.size_bytes,
            name,
            str(mp),
            status,
            round(time.time() - started, 2),
            error=error,
        )
    finally:
        umount(mp, dry=dry)


def run_plan(
    cfg: Config,
    only: set[str] | None,
    list_only: bool,
    workers_override: int | None,
    dry: bool,
):
    prepend_bin_to_path()

    # Only create directories if not in dry-run or list-only mode
    if not dry and not list_only:
        try:
            ensure_dir(cfg.run_summary_dir)
            ensure_dir(cfg.spool_dir)
            ensure_dir(Path("/mnt/docrip"))
        except PermissionError as e:
            print(f"[warn] Cannot create directories (try running as root): {e}")
            if not list_only:
                return 1

    date_str = utc_datestr(cfg.date_fmt)
    token = derive_token(cfg, date_str)

    assemble_layers(cfg.allow_raid, cfg.allow_lvm, dry=dry)
    vols = collect_volumes(cfg)

    # Apply --only
    if only:
        for v in vols:
            if v.path not in only:
                v.skip_reason = v.skip_reason or "not_in_only"

    if list_only:
        print_plan(vols)
        return 0

    to_process: List[Volume] = [v for v in vols if not v.skip_reason]
    to_process.sort(key=lambda x: x.size_bytes, reverse=True)

    workers = auto_workers(
        workers_override if workers_override is not None else cfg.workers
    )
    comp_thr = comp_threads_for(workers)
    print(
        f"[info] workers={workers} comp_threads/job≈{comp_thr} date={date_str} token={token}"
    )

    results: List[VolumeResult] = []
    start = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        futs = [
            ex.submit(process_one, cfg, v, token, date_str, comp_thr, dry)
            for v in to_process
        ]
        for f in concurrent.futures.as_completed(futs):
            results.append(f.result())

    run_summary = {
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "duration_sec": round(time.time() - start, 2),
        "host": os.uname().nodename,
        "date": date_str,
        "token": token,
        "volumes_total": len(vols),
        "volumes_processed": len(to_process),
        "results": [r.__dict__ for r in results],
    }
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    write_json(cfg.run_summary_dir / f"run-{ts}.json", run_summary)

    if cfg.per_volume_json:
        for r in results:
            write_json(cfg.run_summary_dir / f"{r.name}.json", r.__dict__)

    failed = [r for r in results if r.status != "ok"]
    if failed:
        print(
            f"[warn] {len(failed)} volume(s) failed or partial. See JSON logs in {cfg.run_summary_dir}.",
            file=sys.stderr,
        )
        return 1
    print("[ok] all processed volumes succeeded.")
    return 0
