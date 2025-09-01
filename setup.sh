
#!/usr/bin/env bash
# setup.sh — Build & package docrip as a single binary (PyInstaller) and optional AppImage.
# Uses Python 3.11+ (tomllib). Runtime (client) does not need Python.
set -euo pipefail

APP_NAME="docrip"
ENTRY="main.py"
DIST="dist"
BUILD="build"
APPDIR="${BUILD}/AppDir"
ARCH=$(uname -m)
: "${ARCH:=x86_64}"

die()  { echo "ERROR: $*" >&2; exit 2; }
need() { command -v "$1" >/dev/null 2>&1 || die "Missing required tool: $1"; }

ensure_venv() {
  if [ ! -d "venv" ]; then
    echo "[*] Creating virtual environment"
    python3 -m venv venv
  fi
  if [ -z "${VIRTUAL_ENV:-}" ]; then
    echo "[*] Activating virtual environment"
    # shellcheck disable=SC1091
    . venv/bin/activate
  fi
}

get_python() {
  if [ -n "${VIRTUAL_ENV:-}" ] || [ -d "venv" ]; then
    echo "venv/bin/python"
  else
    echo "python3"
  fi
}

get_pip() {
  if [ -n "${VIRTUAL_ENV:-}" ] || [ -d "venv" ]; then
    echo "venv/bin/pip"
  else
    echo "python3 -m pip"
  fi
}

check_python311() {
  need python3
  python3 - <<'PY'
import sys
maj, min = sys.version_info[:2]
assert (maj, min) >= (3, 11), f"Python 3.11+ required, found {sys.version}"
print(f"[ok] Python {sys.version.split()[0]}")
PY
}

ensure_pyinstaller() {
  if ! python3 -c 'import PyInstaller' >/dev/null 2>&1; then
    echo "[*] Installing PyInstaller for build-time (user scope)"
    python3 -m pip install --user --upgrade pyinstaller
  fi
  need pyinstaller
}

ensure_appimagetool() {
  command -v appimagetool >/dev/null 2>&1 || die "appimagetool not found. Install it to build an AppImage."
}

install_dev_deps() {
  echo "[*] Installing development dependencies"
  ensure_venv
  PIP=$(get_pip)
  $PIP install -r requirements.txt
}

write_demo_toml() {
  if [ -f docrip.toml ]; then
    echo "[info] docrip.toml exists; not overwriting."
    return
  fi
  cat > docrip.toml <<'EOF'
version = 1
[server]
rsync_remote = "backup@datavault.example:/srv/docrip"
ssh_key      = "/root/.ssh/docrip_ed25519"
port         = 22
[archive]
compressor = "zstd"
compression_level = 3
chunk_size_mb = 4096
stream_direct = false
spool_dir = "/var/tmp/docrip"
preserve_xattrs = true
[discovery]
include_fstypes = ["ext2","ext3","ext4","xfs","btrfs","zfs","ntfs","vfat","exfat","hfs","hfsplus","apfs"]
skip_fstypes = ["swap","iso9660","udf","crypto_LUKS"]
skip_if_encrypted = true
allow_lvm = true
allow_raid = true
min_partition_size_gb = 256
avoid_devices = []
[filters]
max_file_size_mb = 100
[runtime]
workers = 0
rsync_bwlimit_kbps = 0
log_level = "INFO"
[naming]
date_fmt = "%Y%m%d"
token_source = "machine-id"
pattern = "{date}_{token}_d{disk}_p{part}"
[integrity]
algorithm = "sha256"
[output]
run_summary_dir = "/var/log/docrip"
per_volume_json = true
EOF
  echo "[ok] wrote demo docrip.toml"
}

do_build() {
  check_python311
  ensure_pyinstaller
  [ -f "${ENTRY}" ] || die "Missing ${ENTRY}"

  # Include docrip.toml as in-bundle default (can be overridden by adjacent or /etc)
  pyinstaller --clean --noconfirm \
    --name "${APP_NAME}" \
    --onefile \
    --strip \
    --add-data "docrip.toml:." \
    --hidden-import "docrip" \
    --hidden-import "docrip.cli" \
    --hidden-import "docrip.config" \
    --hidden-import "docrip.orchestrator" \
    --hidden-import "docrip.discover" \
    --hidden-import "docrip.mounter" \
    --hidden-import "docrip.archiver" \
    --hidden-import "docrip.chunker" \
    --hidden-import "docrip.syncer" \
    --hidden-import "docrip.layers" \
    --hidden-import "docrip.util" \
    --hidden-import "docrip.types" \
    --hidden-import "docrip.bundle" \
    "${ENTRY}"

  echo "[ok] built ${DIST}/${APP_NAME}"
}

do_appimage() {
  do_build
  ensure_appimagetool
  rm -rf "${APPDIR}"
  mkdir -p "${APPDIR}/usr/bin" "${APPDIR}/usr/share/applications"
  cp -a "dist/${APP_NAME}" "${APPDIR}/usr/bin/"
  # optional: stage portable helpers into AppImage
  if [ -d bin ]; then cp -a bin "${APPDIR}/usr/bin/"; fi
  # stage config alongside binary inside AppImage
  [ -f docrip.toml ] && cp -a docrip.toml "${APPDIR}/usr/bin/"
  cat > "${APPDIR}/usr/share/applications/${APP_NAME}.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=${APP_NAME}
Exec=${APP_NAME}
Categories=Utility;
EOF
  cat > "${APPDIR}/AppRun" <<'EOF'
#!/bin/sh
HERE="$(dirname "$0")"
export PATH="$HERE/usr/bin:$PATH"
exec "$HERE/usr/bin/docrip" "$@"
EOF
  chmod +x "${APPDIR}/AppRun"
  mkdir -p "${DIST}"
  appimagetool "${APPDIR}" "${DIST}/${APP_NAME}-${ARCH}.AppImage"
  echo "[ok] built ${DIST}/${APP_NAME}-${ARCH}.AppImage"
}

do_clean() { rm -rf "${BUILD}" "${DIST}"; echo "[ok] cleaned"; }

do_test() {
  echo "[*] Running tests"
  PYTHON=$(get_python)
  $PYTHON -m pytest tests/ -v
}

do_lint() {
  echo "[*] Running linters"
  PYTHON=$(get_python)
  $PYTHON -m black --check docrip/ main.py
  $PYTHON -m flake8 docrip/ main.py
}

do_format() {
  echo "[*] Formatting code"
  PYTHON=$(get_python)
  $PYTHON -m black docrip/ main.py
}

do_typecheck() {
  echo "[*] Running type check"
  PYTHON=$(get_python)
  $PYTHON -m mypy docrip/ main.py --ignore-missing-imports
}

do_changelog() {
  echo "[*] Recent changes (last 20 lines from CHANGELOG.md)"
  if [ -f CHANGELOG.md ]; then
    head -20 CHANGELOG.md | tail -n +4  # Skip the header lines
  else
    echo "[warn] CHANGELOG.md not found"
  fi
}

do_version() {
  echo "[*] Current version information"
  if [ -f docrip/__init__.py ]; then
    grep "__version__" docrip/__init__.py || echo "[warn] No version found in __init__.py"
  else
    echo "[warn] docrip/__init__.py not found"
  fi
  
  if [ -f CHANGELOG.md ]; then
    echo "[*] Latest CHANGELOG entry:"
    grep -A 5 "^## \[" CHANGELOG.md | head -6
  else
    echo "[warn] CHANGELOG.md not found"
  fi
}

do_check_tools() {
  echo "[*] Checking optional tool availability"
  PYTHON=$(get_python)
  $PYTHON -c "
from docrip.util import check_optional_tools
check_optional_tools()
print('[info] Run \\'./setup.sh check-tools\\' anytime to see this summary')
"
}

do_check() {
  echo "== Build Environment =="; python3 -V || true
  command -v pyinstaller >/dev/null && pyinstaller --version || echo "(pyinstaller not installed)"
  command -v appimagetool >/dev/null && appimagetool --version || echo "(appimagetool not installed)"
  echo "== Runtime helpers =="
  if [ -d bin ]; then echo "[bin] contains:"; (cd bin && ls -1) || true
  else echo "No ./bin (optional)."; fi
  echo "== Package structure =="
  [ -f main.py ] && echo "[ok] main.py entry point" || echo "[!] missing main.py"
  [ -d docrip ] && echo "[ok] docrip package" || echo "[!] missing docrip package"
  [ -f docrip.toml ] && echo "[ok] docrip.toml config" || echo "[warn] missing docrip.toml"
  [ -f requirements.txt ] && echo "[ok] requirements.txt" || echo "[warn] missing requirements.txt"
  [ -f CHANGELOG.md ] && echo "[ok] CHANGELOG.md" || echo "[warn] missing CHANGELOG.md"
}

case "${1:-}" in
  build)         do_build ;;
  appimage)      do_appimage ;;
  clean)         do_clean ;;
  demo-config)   write_demo_toml ;;
  install-deps)  install_dev_deps ;;
  test)          do_test ;;
  lint)          do_lint ;;
  format)        do_format ;;
  typecheck)     do_typecheck ;;
  changelog)     do_changelog ;;
  version)       do_version ;;
  check)         do_check ;;
  check-tools)   do_check_tools ;;
  *) echo "Usage: $0 {build|appimage|clean|demo-config|install-deps|test|lint|format|typecheck|changelog|version|check|check-tools}"; exit 1 ;;
esac
