# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

docrip is a live USB data capture tool designed for forensic data collection and archival. It automatically discovers storage devices, mounts filesystems read-only, creates compressed archives with integrity verification, and syncs them to remote servers.

**Key Features:**
- Read-only filesystem mounting with safety options (nodev/nosuid/noexec)
- Support for multiple filesystems: ext2/3/4, XFS, Btrfs, NTFS, VFAT/ExFAT, HFS/HFS+, APFS, ZFS
- Storage layer support: LVM, md-RAID (read-only assembly)
- Chunked, resumable transfers with integrity verification (SHA-256)
- Encrypted volume detection and automatic skipping
- Concurrent processing with adaptive worker scaling

## Architecture

The project follows a modular Python package structure:

```
docrip/                     # Main package
├── cli.py                  # Command-line interface and argument parsing
├── config.py               # TOML configuration loading and validation
├── orchestrator.py         # Main workflow coordination and threading
├── discover.py             # Device discovery and filtering
├── layers.py               # Storage layer assembly (LVM/RAID/ZFS)
├── mounter.py              # Filesystem mounting with safety options
├── archiver.py             # File selection and tar command building
├── chunker.py              # Archive compression and chunking pipeline
├── syncer.py               # Rsync transfer with resume support
├── util.py                 # Utility functions and shell execution
├── types.py                # Data classes for Config, Volume, etc.
└── bundle.py               # Bundle detection and PATH management

main.py                     # Entry point (development and bundled)
setup.sh                    # Build script for PyInstaller packaging
requirements.txt            # Development dependencies
docrip.toml                 # Configuration file (TOML format)
```

## Core Workflow

1. **Initialization**: Load config, set up logging, configure worker threads
2. **Layer Assembly**: Assemble LVM VGs, md-RAID arrays, import ZFS pools (all read-only)
3. **Discovery**: Enumerate block devices, detect encrypted volumes, apply filters
4. **Processing** (per volume, concurrent):
   - Mount filesystem read-only with safety options
   - Build file list (excluding large files per config)
   - Create compressed archive stream with tar
   - Split into chunks with integrity hashes
   - Rsync chunks to remote server
   - Generate JSON summaries

## Common Development Commands

### Development Setup
```bash
# Install development dependencies
./setup.sh install-deps

# Check build environment and project structure
./setup.sh check

# Run in development mode
python3 main.py --help
python3 main.py --list --dry-run
```

### Code Quality
```bash
# Format code
./setup.sh format

# Check formatting and style
./setup.sh lint

# Type checking
./setup.sh typecheck

# Run tests
./setup.sh test
```

### Building
```bash
# Create demo configuration
./setup.sh demo-config

# Build bundled executable
./setup.sh build

# Build AppImage (requires appimagetool)
./setup.sh appimage

# Clean build artifacts
./setup.sh clean
```

## Configuration

The tool uses TOML configuration with the following key sections:

- **server**: Rsync destination, SSH keys, port
- **archive**: Compression (zstd/pigz), chunking, spooling
- **discovery**: Filesystem filters, LVM/RAID options, size thresholds
- **filters**: File size exclusions
- **runtime**: Worker threads, bandwidth limits, logging
- **naming**: Archive naming patterns with stable tokens
- **integrity**: Hash algorithms (SHA-256)
- **output**: JSON logging configuration

## Testing Strategy

The project requires both unit tests and integration tests:

### Unit Tests (no root required)
- Configuration parsing and validation
- Device discovery logic with mock data
- Archive name generation and token derivation
- File selection logic and size filtering
- Hash computation and manifest generation

### Integration Tests (requires root/VM)
- End-to-end processing with loopback devices
- Filesystem mounting across different types
- LVM/RAID assembly and read-only mounting
- Network transfer and resume functionality
- Error handling and cleanup

## Safety Considerations

This tool is designed for forensic data collection with strict safety requirements:

1. **Read-only operations**: Never modify source devices
2. **Encryption respect**: Skip encrypted volumes entirely
3. **Boot device exclusion**: Auto-detect and skip live USB
4. **Mount safety**: Use nodev/nosuid/noexec options
5. **Process isolation**: Sanitize all shell command inputs
6. **Error containment**: Continue processing other volumes on failure

## Troubleshooting

### Import Issues
- Ensure you're running from project root directory
- Check that `docrip/` package directory exists
- Verify all modules are in the package directory

### Build Issues
- Python 3.11+ required for tomllib support
- PyInstaller must be installed for bundling
- Missing system utilities logged as warnings

### Runtime Issues
- Must run as root for device discovery and mounting
- Network connectivity required for rsync transfers
- Filesystem support depends on available kernel drivers/tools

## Development Notes

### Bundle Detection
The `bundle.py` module handles both development and bundled execution modes:
- Development: Looks for `main.py` and `docrip.toml` to find project root
- Bundled: Uses PyInstaller's sys._MEIPASS and executable location
- Portable helpers: Prepends `./bin/` to PATH for bundled tools

### Error Handling
- Individual volume failures don't stop overall processing
- Network errors are retried with exponential backoff
- All errors are logged with structured JSON output
- Exit codes reflect overall success/failure status

### Performance Tuning
- Worker threads auto-scale based on CPU count (default: cpu_count/2, max 8)
- Compressor threads allocated per worker to avoid contention  
- Largest volumes processed first to minimize tail latency
- Optional I/O prioritization with ionice/nice

## Dependencies

**Runtime**: Python 3.11+ only (uses tomllib from stdlib)

**Development**:
- PyInstaller (bundling)
- pytest (testing)
- black (formatting) 
- flake8 (linting)
- mypy (type checking)

**System Tools** (bundled or system-provided):
- Core: lsblk, blkid, mount, umount, tar, ssh, rsync, split, sha256sum
- Compression: zstd (preferred) or pigz
- Filesystems: ntfs-3g, apfs-fuse, hfsprogs, etc.
- Storage: mdadm, lvm2, zpool/zfs