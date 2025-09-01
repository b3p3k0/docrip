"""
Tests for configuration loading and validation.
"""
import pytest
import tempfile
from pathlib import Path

from docrip.config import load_config
from docrip.types import Config


def test_load_config_basic():
    """Test basic configuration loading."""
    toml_content = """
version = 1

[server]
rsync_remote = "user@host:/path"
ssh_key = "/root/.ssh/key"
port = 22

[archive]
compressor = "zstd"
compression_level = 3
chunk_size_mb = 1024
stream_direct = false
spool_dir = "/tmp/docrip"
preserve_xattrs = true

[discovery]
include_fstypes = ["ext4", "ntfs"]
skip_fstypes = ["swap"]
skip_if_encrypted = true
allow_lvm = true
allow_raid = true
min_partition_size_gb = 100
avoid_devices = []

[filters]
max_file_size_mb = 50

[runtime]
workers = 2
rsync_bwlimit_kbps = 1000
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
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
        f.write(toml_content)
        f.flush()
        
        config = load_config(Path(f.name))
        
        assert config.server_rsync_remote == "user@host:/path"
        assert config.server_ssh_key == "/root/.ssh/key"
        assert config.server_port == 22
        assert config.compressor == "zstd"
        assert config.compression_level == 3
        assert config.chunk_size_mb == 1024
        assert config.workers == 2
        assert config.include_fstypes == ["ext4", "ntfs"]
        assert config.skip_fstypes == ["swap"]
        assert config.min_partition_size_gb == 100
        

def test_config_defaults():
    """Test that configuration uses proper defaults."""
    toml_content = """
version = 1

[server]
rsync_remote = "user@host:/path"
ssh_key = "/root/.ssh/key"
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
        f.write(toml_content)
        f.flush()
        
        config = load_config(Path(f.name))
        
        # Check defaults
        assert config.server_port == 22
        assert config.compressor == "zstd"
        assert config.compression_level == 3
        assert config.chunk_size_mb == 4096
        assert config.workers == 0  # auto
        assert config.min_partition_size_gb == 256
        assert config.max_file_size_mb == 100