# docrip

**Live USB Data Capture and Archive Tool** ⚡

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Platform: Linux](https://img.shields.io/badge/platform-Linux-green.svg)](https://www.kernel.org/)

A small, bundled utility designed for forensic data collection from Linux live USB environments. docrip automatically discovers storage devices, mounts filesystems read-only with safety options, creates compressed archives with integrity verification, and syncs them to remote servers with resume capability.

## 📋 Table of Contents

- [Quick Start](#-quick-start)
- [Features](#-features) 
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Usage](#-usage)
- [Supported Filesystems](#-supported-filesystems)
- [Architecture](#-architecture)
- [Development](#-development)
- [Deployment](#-deployment)
- [Troubleshooting](#-troubleshooting)
- [Security](#-security)
- [Contributing](#-contributing)
- [License](#-license)

## 🚀 Quick Start

### Prerequisites
- Linux live USB environment (Ubuntu/Debian-based recommended)
- Root access
- Network connectivity to SSH destination
- Python 3.11+ (for development/building only)

### Basic Usage

1. **Prepare your USB stick:**
   ```bash
   # Copy to USB stick
   docrip/
     docrip              # bundled executable
     docrip.toml         # configuration file
     bin/                # optional portable helpers
   ```

2. **Configure the tool:**
   ```bash
   # Edit docrip.toml with your server details
   vim docrip.toml
   ```

3. **Preview what will be processed:**
   ```bash
   sudo ./docrip --list
   ```

4. **Run data capture:**
   ```bash
   sudo ./docrip --config ./docrip.toml
   ```

5. **Monitor progress:**
   ```bash
   tail -f /var/log/docrip/run-*.json
   ```

## ✨ Features

### Core Capabilities
- 🔍 **Automatic Discovery** - Detects disks, partitions, LVM, and md-RAID
- 🔒 **Read-Only Safety** - Never modifies source devices, uses `nodev/nosuid/noexec`
- 🗜️ **Smart Compression** - Multi-threaded zstd/pigz with adaptive worker scaling
- 📦 **Chunked Transfer** - Resumable rsync with per-chunk integrity verification
- 🔐 **Encryption Aware** - Automatically skips encrypted volumes (BitLocker/LUKS/APFS/etc.)
- ⚡ **High Performance** - Concurrent processing with largest-first scheduling
- 🏷️ **Stable Naming** - Deterministic archive naming with date/host tokens

### Safety Features
- **Boot Device Exclusion** - Automatically detects and excludes live USB
- **Encrypted Volume Detection** - Skips BitLocker, LUKS, FileVault, APFS encrypted
- **No Filesystem Modification** - Never runs fsck or journal replay
- **Process Isolation** - Sanitized shell commands and error containment
- **Comprehensive Logging** - JSON logs with skip reasons and error details

### Performance Features
- **Adaptive Concurrency** - Auto-scales workers based on CPU count
- **Multi-threaded Compression** - zstd/pigz with per-worker thread allocation
- **Intelligent Scheduling** - Processes largest volumes first
- **Resume Support** - Interrupted transfers resume at chunk granularity

## 📦 Installation

### Pre-built Binary (Recommended)
Download the latest release from GitHub and extract to your USB stick.

### Build from Source
```bash
# Clone repository
git clone https://github.com/your-org/docrip.git
cd docrip

# Install build dependencies
./setup.sh install-deps

# Build bundled executable
./setup.sh build

# Optional: Build AppImage
./setup.sh appimage
```

## ⚙️ Configuration

docrip uses TOML configuration files. Configuration is searched in this order:

1. `--config <path>` (command line)
2. `docrip.toml` (next to binary)
3. `/etc/docrip.toml`

### Basic Configuration

```toml
version = 1

[server]
rsync_remote = "backup@datavault.example:/srv/docrip"
ssh_key = "/root/.ssh/docrip_ed25519"
port = 22

[archive]
compressor = "zstd"                    # "zstd" | "pigz"
compression_level = 3                  # 1-9, balance speed vs size
chunk_size_mb = 4096                   # chunk size, 0 = no chunking
spool_dir = "/var/tmp/docrip"
preserve_xattrs = true

[discovery]
min_partition_size_gb = 256            # skip partitions smaller than this
skip_if_encrypted = true               # skip encrypted volumes
allow_lvm = true                       # process LVM logical volumes
allow_raid = true                      # process md-RAID arrays

[filters]
max_file_size_mb = 100                 # exclude files larger than this

[runtime]
workers = 0                            # 0 = auto (cpu_count/2, max 8)
log_level = "INFO"
```

### Configuration Reference

| Section | Key | Default | Description |
|---------|-----|---------|-------------|
| `server` | `rsync_remote` | *required* | SSH destination `user@host:/path` |
| `server` | `ssh_key` | `/root/.ssh/docrip_ed25519` | SSH private key path |
| `server` | `port` | `22` | SSH port |
| `archive` | `compressor` | `"zstd"` | Compression algorithm |
| `archive` | `compression_level` | `3` | Compression level (1-9) |
| `archive` | `chunk_size_mb` | `4096` | Chunk size in MB |
| `discovery` | `min_partition_size_gb` | `256` | Skip partitions below this size |
| `discovery` | `skip_if_encrypted` | `true` | Skip encrypted volumes |
| `filters` | `max_file_size_mb` | `100` | Exclude large files |
| `runtime` | `workers` | `0` | Worker threads (0 = auto) |

## 🖥️ Usage

### Command Line Options

```bash
./docrip [OPTIONS]

Options:
  --config PATH           Configuration file path
  --list                  Show discovery plan and skip reasons  
  --dry-run              Show commands without executing
  --workers N            Override worker thread count
  --only DEV1,DEV2       Process only specified devices
  --exclude-dev DEV      Skip specified devices
  -h, --help             Show help message
```

### Common Workflows

#### Preview Operations
```bash
# See what devices will be processed
sudo ./docrip --list

# Test configuration without changes
sudo ./docrip --dry-run
```

#### Selective Processing
```bash
# Process only specific devices
sudo ./docrip --only /dev/sdb1,/dev/nvme0n1p3

# Skip specific devices  
sudo ./docrip --exclude-dev sda,nvme0n1
```

#### Performance Tuning
```bash
# Override worker count
sudo ./docrip --workers 4

# Use specific configuration
sudo ./docrip --config /path/to/custom.toml
```

### Output Structure

Archives are organized on the remote server as:
```
{rsync_remote}/
├── 20240901/                    # Date (YYYYMMDD)
│   └── a6f09/                   # Host token (5 chars)
│       ├── 20240901_a6f09_d0_p1/    # Volume archive
│       │   ├── *.tar.zst.part0001   # Archive chunks
│       │   ├── *.tar.zst.part0002
│       │   ├── *.sha256             # Per-chunk hashes
│       │   ├── .whole.sha256        # Whole stream hash
│       │   ├── .parts               # Chunk list
│       │   └── .manifest.json       # Metadata
│       └── 20240901_a6f09_d0_p2/
```

## 💾 Supported Filesystems

| Filesystem | Mount Command | Notes |
|------------|---------------|-------|
| **ext2/3/4** | `mount -t ext4 -o ro,noload,nodev,nosuid,noexec` | Native kernel support |
| **XFS** | `mount -t xfs -o ro,norecovery,nodev,nosuid,noexec` | Native kernel support |
| **Btrfs** | `mount -t btrfs -o ro,nodev,nosuid,noexec` | Native kernel support |
| **NTFS** | `ntfs-3g -o ro,nodev,nosuid,noexec` | Requires ntfs-3g |
| **VFAT** | `mount -t vfat -o ro,uid=0,gid=0,umask=022,nodev,nosuid,noexec` | Native kernel support |
| **ExFAT** | `mount -t exfat -o ro,nodev,nosuid,noexec` | Native kernel support |
| **HFS** | `mount -t hfs -o ro,nodev,nosuid,noexec` | Requires hfsprogs |
| **HFS+** | `mount -t hfsplus -o ro,force,nodev,nosuid,noexec` | Requires hfsprogs |
| **APFS** | `apfs-fuse --readonly` | Requires apfs-fuse |
| **ZFS** | `zpool import -a -o readonly=on` | Requires zfs-utils |

### Storage Layers

| Layer | Assembly Command | Notes |
|-------|------------------|-------|
| **md-RAID** | `mdadm --assemble --scan --readonly` | Read-only assembly only |
| **LVM** | `vgchange -ay` + read-only mounts | Activates volume groups |
| **ZFS** | `zpool import -a -o readonly=on -N -f` | Read-only import |

## 🏗️ Architecture

### Core Workflow

1. **Layer Assembly** - Activate LVM/RAID/ZFS in read-only mode
2. **Device Discovery** - Enumerate block devices with `lsblk`
3. **Filtering** - Apply size, encryption, and filesystem filters
4. **Concurrent Processing** - Process volumes in parallel (largest first)
   - Mount filesystem read-only
   - Create compressed tar stream  
   - Split into fixed-size chunks
   - Generate integrity hashes
   - Rsync to remote server
5. **Logging** - Generate JSON summaries

### Module Structure

```
docrip/
├── cli.py           # Command-line interface
├── config.py        # TOML configuration loading  
├── orchestrator.py  # Main workflow coordination
├── discover.py      # Device discovery and filtering
├── layers.py        # Storage layer assembly (LVM/RAID/ZFS)
├── mounter.py       # Filesystem mounting
├── archiver.py      # File selection and tar commands
├── chunker.py       # Compression and chunking pipeline  
├── syncer.py        # Rsync transfer
├── util.py          # Utilities and shell execution
├── types.py         # Data classes
└── bundle.py        # Bundle detection and PATH management
```

## 🛠️ Development

### Development Setup

```bash
# Clone and setup
git clone https://github.com/your-org/docrip.git
cd docrip

# Install development dependencies (creates and manages virtual environment automatically)
./setup.sh install-deps

# Check environment
./setup.sh check

# Run in development mode
python3 main.py --help
```

**Note**: The setup script automatically creates and manages a Python virtual environment (`venv/`) to ensure compatibility with modern Python distributions that implement PEP 668 (externally-managed environments). All development commands automatically use the virtual environment.

### Development Commands

```bash
# Code formatting
./setup.sh format

# Linting and style checks  
./setup.sh lint

# Type checking
./setup.sh typecheck

# Run tests
./setup.sh test

# Clean build artifacts
./setup.sh clean
```

### Testing

The project includes both unit tests and integration tests:

- **Unit Tests** - Test individual modules without requiring root
- **Integration Tests** - End-to-end testing with loopback devices (requires root)

```bash
# Run all tests
python3 -m pytest

# Run unit tests only  
python3 -m pytest -m unit

# Run with coverage
python3 -m pytest --cov=docrip
```

### Development Troubleshooting

#### Virtual Environment Issues

```bash
# If virtual environment becomes corrupted, remove and recreate
rm -rf venv/
./setup.sh install-deps

# Check if virtual environment is active
echo $VIRTUAL_ENV

# Manually activate virtual environment if needed
source venv/bin/activate
```

#### Python Version Issues

```bash
# Verify Python 3.11+ is available
python3 --version

# If using older Python, install Python 3.11+
sudo apt update
sudo apt install python3.11 python3.11-venv python3.11-dev
```

#### Dependency Issues

```bash
# Clean install all dependencies
rm -rf venv/
./setup.sh install-deps

# Check installed packages
venv/bin/pip list

# Upgrade all dependencies
venv/bin/pip install --upgrade -r requirements.txt
```

## 🚀 Deployment

### USB Stick Preparation

1. **Build the binary:**
   ```bash
   ./setup.sh build
   ```

2. **Prepare USB structure:**
   ```
   /media/usb/docrip/
   ├── docrip                    # bundled executable
   ├── docrip.toml              # configuration  
   ├── bin/                     # portable helpers (optional)
   │   ├── zstd
   │   ├── ntfs-3g
   │   ├── mdadm
   │   └── ...
   └── LICENSES/                # license texts
   ```

3. **Set permissions:**
   ```bash
   chmod +x docrip
   chmod 600 docrip.toml        # protect SSH keys
   ```

### Field Operations Checklist

- [ ] Verify SSH key access to destination server
- [ ] Test network connectivity from live environment  
- [ ] Run `--list` to preview operations
- [ ] Check available disk space in spool directory
- [ ] Monitor `/var/log/docrip/` during operations
- [ ] Verify chunk integrity after transfer

### Portable Helpers

Include statically compiled tools in `bin/` for maximum compatibility:

- **Core Tools**: `busybox`, `zstd`, `pigz`, `rsync`
- **Filesystem Support**: `ntfs-3g`, `apfs-fuse`, `hfsprogs`  
- **Storage Layers**: `mdadm`, `lvm2`, `zfs-utils`

## 🔧 Troubleshooting

### Common Issues

#### No Devices Listed
```bash
# Check if running as root
sudo id

# Verify lsblk works
sudo lsblk

# Check boot device exclusion
sudo findmnt -no SOURCE /
```

#### Mount Failures
```bash
# Check filesystem support
cat /proc/filesystems

# Check for required tools
which ntfs-3g apfs-fuse

# Review mount errors in logs
tail /var/log/docrip/run-*.json
```

#### Transfer Issues
```bash
# Test SSH connectivity
ssh -i /path/to/key user@host

# Check network and firewall
ping destination-host
telnet destination-host 22

# Monitor rsync progress
rsync --progress --dry-run ...
```

#### Performance Issues
```bash
# Check CPU and memory
top
free -h

# Monitor I/O
iostat 5

# Adjust worker count
./docrip --workers 2
```

### Log Analysis

docrip generates detailed JSON logs:

```bash
# View run summary
jq '.' /var/log/docrip/run-*.json

# Check failed volumes
jq '.results[] | select(.status != "ok")' /var/log/docrip/run-*.json

# View per-volume details
ls /var/log/docrip/*.json
```

## 🔒 Security

### Security Model

- **No Decryption** - Encrypted volumes are intentionally skipped
- **Read-Only Operations** - Never modifies source devices
- **Mount Safety** - Uses `nodev`, `nosuid`, `noexec` options
- **Process Isolation** - Sanitizes all shell command inputs
- **SSH Key Security** - Uses dedicated deployment keys

### Best Practices

- Use dedicated SSH keys with restricted permissions
- Store configuration files securely (SSH keys, server details)
- Verify integrity hashes after transfer
- Monitor logs for security events
- Test in isolated environments before field deployment

### Integrity Verification

```bash
# Verify chunk integrity
sha256sum -c *.sha256

# Verify whole stream
cat *.part* | sha256sum -c .whole.sha256

# Test archive contents
cat *.part* | tar -tf -
```

## 🤝 Contributing

We welcome contributions! Please see our contributing guidelines:

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Run the test suite and linting
5. Submit a pull request

### Development Workflow

```bash
# Setup development environment
git clone https://github.com/your-org/docrip.git
cd docrip
./setup.sh install-deps

# Make changes and test
./setup.sh format
./setup.sh lint  
./setup.sh test

# Build and test
./setup.sh build
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

### Third-Party Licenses

Tools included in the `bin/` directory retain their original licenses:
- **GPL/LGPL**: mdadm, lvm2, ntfs-3g
- **BSD**: zstd, rsync  
- **Various**: See `LICENSES/` directory

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/your-org/docrip/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/docrip/discussions)
- **Security**: Report security issues privately to security@example.com

---

**docrip** - Fast, safe, resumable data capture for live USB environments.