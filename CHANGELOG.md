# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2024-09-01

### Added
- Proper Python package structure with `docrip/` directory containing all modules
- `main.py` entry point that works in both development and PyInstaller bundled modes
- Comprehensive `.gitignore` with Python development artifacts and project-specific exclusions
- `requirements.txt` with development dependencies (pytest, black, flake8, mypy, pyinstaller)
- `CLAUDE.md` development documentation with architecture overview and build instructions
- Basic test framework with pytest configuration and sample unit tests for core modules
- GitHub-ready `README.md` with proper markdown formatting, badges, table of contents, and navigation
- Configuration reference table with all TOML options documented
- Filesystem support table with mount commands and requirements
- Troubleshooting section with common issues and solutions
- Development workflow documentation with setup and testing instructions
- Security best practices and integrity verification procedures

### Changed
- Converted from flat module structure to proper Python package layout
- Updated `setup.sh` build script to work with new package structure and added development commands
- Improved bundle detection logic to handle both development and production environments
- Enhanced orchestrator error handling to gracefully handle permission issues in development mode
- Renamed `layer.py` to `layers.py` to match import statements
- Updated all relative imports to work correctly with package structure

### Fixed
- Import system issues that prevented module loading due to relative import problems
- Bundle root detection for development vs PyInstaller bundled execution modes  
- Permission errors when creating system directories (`/mnt/docrip`, `/var/log/docrip`) in non-root development
- PyInstaller build configuration with proper hidden imports and data file inclusion

### Technical Details
- **Package Structure**: Migrated to `docrip/` package with proper `__init__.py` and module organization
- **Entry Point**: `main.py` handles Python path setup and imports the CLI from the package
- **Bundle Detection**: Enhanced `bundle.py` to detect project root by looking for `main.py` or `docrip.toml`
- **Error Handling**: Orchestrator now handles permission errors gracefully in dry-run and list-only modes
- **Build System**: Updated PyInstaller configuration with explicit hidden imports for all package modules

## [0.1.0] - Initial Implementation

### Added
- Core docrip functionality for live USB data capture and archival
- Device discovery system using `lsblk` and `blkid` for comprehensive block device enumeration
- Read-only filesystem mounting with safety options (`nodev`, `nosuid`, `noexec`)
- Storage layer assembly for LVM volume groups, md-RAID arrays, and ZFS pools (read-only)
- Multi-threaded compression support (zstd preferred, pigz fallback) with adaptive thread allocation
- Chunked archive system with fixed-size parts for resumable transfers
- Integrity verification using SHA-256 hashes (per-chunk and whole-stream)
- Resumable rsync transfers with `--partial`, `--inplace`, and `--append-verify`
- TOML configuration system with comprehensive options and defaults
- Encrypted volume detection and automatic skipping (BitLocker, LUKS, APFS, FileVault, etc.)
- Boot device detection and exclusion to prevent live USB modification
- JSON logging system with run summaries and per-volume details
- Concurrent volume processing with largest-first scheduling for optimal performance
- File size filtering to exclude large files while preserving directory structure

### Filesystem Support
- **ext2/3/4**: Native kernel support with `noload` option
- **XFS**: Native support with `norecovery` option  
- **Btrfs**: Native kernel support
- **NTFS**: Via ntfs-3g with read-only mode
- **VFAT/ExFAT**: Native kernel support
- **HFS/HFS+**: Via hfsprogs with force read-only
- **APFS**: Via apfs-fuse (optional) with readonly mode
- **ZFS**: Via zpool/zfs tools with readonly import

### Safety Features
- Automatic boot device exclusion using `findmnt` root source detection
- Comprehensive encrypted volume detection with multiple signature types
- Read-only mount enforcement with no filesystem modification capabilities
- Process isolation with sanitized shell command execution
- Error containment allowing individual volume failures without stopping overall process

### Performance Features  
- Adaptive worker thread scaling based on CPU count (default: cpu_count/2, max 8)
- Per-worker compression thread allocation to avoid resource contention
- Largest volume first scheduling to minimize tail latency in concurrent processing
- Optional I/O priority management with ionice/nice integration

### Configuration System
- TOML-based configuration with hierarchical sections
- Comprehensive defaults for all options
- Support for server credentials, archive settings, discovery filters, and runtime parameters
- Flexible naming patterns with date/host token generation for stable, unique archive names
- Multiple configuration file locations with precedence (CLI > bundle > /etc)