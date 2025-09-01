"""
chunker.py
Build the archive pipeline:
  find | tar (preserve xattrs/ACLs) | compress | split (chunk files)
Compute:
  - .whole.sha256 (of the compressed stream)
  - per-chunk *.sha256
  - .parts and .manifest.json
"""

from __future__ import annotations
import json
from pathlib import Path
from .types import Config
from .util import run, write_json
from .archiver import build_find_cmd, compressor_cmd


def make_chunks(
    cfg: Config, mp: Path, outdir: Path, compressor_threads: int, dry: bool = False
) -> bool:
    outdir.mkdir(parents=True, exist_ok=True)
    ext = "zst" if cfg.compressor == "zstd" else "gz"
    manifest = {"ext": ext, "chunk_size_mb": cfg.chunk_size_mb, "whole_sha256": None}
    manifest_path = outdir / ".manifest.json"
    parts_list = outdir / ".parts"
    whole_sha = outdir / ".whole.sha256"

    tar_flags = "--numeric-owner --acls --xattrs --xattrs-include='*'"
    find_cmd = build_find_cmd(mp, cfg.max_file_size_mb)
    comp_cmd = compressor_cmd(cfg, compressor_threads)
    tar_cmd = f"{find_cmd} | tar -C {str(mp)!s} {tar_flags} --null -T - -cpf -"

    if cfg.chunk_size_mb and cfg.chunk_size_mb > 0:
        split_prefix = str(outdir / f"{outdir.name}.tar.{ext}.part")
        pipe = (
            f"{tar_cmd} | {comp_cmd} "
            f"| tee >(sha256sum | awk '{{print $1}}' > {str(whole_sha)!s}) "
            f"| split -b {cfg.chunk_size_mb}M -d -a 4 - {split_prefix}"
        )
        rc, _ = run(pipe, dry=dry)
        if rc != 0:
            return False
        run(
            f'for p in {str(outdir)!s}/*.part*; do sha256sum "$p" > "$p.sha256"; done',
            dry=dry,
        )
        run(
            f"ls -1 {str(outdir)!s}/*.part* | sort | sed 's#^.*/##' > {str(parts_list)!s}",
            dry=dry,
        )
        if not dry and whole_sha.exists():
            manifest["whole_sha256"] = whole_sha.read_text().strip()
            write_json(manifest_path, manifest)
        return True
    else:
        archive_path = outdir / f"{outdir.name}.tar.{ext}"
        pipe = f"{tar_cmd} | {comp_cmd} > {str(archive_path)!s}"
        rc, _ = run(pipe, dry=dry)
        if rc != 0:
            return False
        run(f"sha256sum {str(archive_path)!s} > {str(whole_sha)!s}", dry=dry)
        if not dry:
            parts_list.write_text(f"{archive_path.name}\n")
            manifest["whole_sha256"] = whole_sha.read_text().strip()
            write_json(manifest_path, manifest)
        return True
