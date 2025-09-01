"""
Pytest configuration and shared fixtures.
"""
import pytest
import tempfile
from pathlib import Path
from docrip.types import Config


@pytest.fixture
def temp_config_file():
    """Create a temporary configuration file for testing."""
    toml_content = """
version = 1

[server]
rsync_remote = "test@localhost:/tmp/docrip-test"
ssh_key = "/tmp/test-key"
port = 22

[archive]
compressor = "zstd"
compression_level = 1
chunk_size_mb = 10
stream_direct = false
spool_dir = "/tmp/docrip-test-spool"
preserve_xattrs = true

[discovery]
include_fstypes = ["ext4", "ext3", "ext2"]
skip_fstypes = ["swap"]
skip_if_encrypted = true
allow_lvm = false
allow_raid = false
min_partition_size_gb = 1
avoid_devices = []

[filters]
max_file_size_mb = 1

[runtime]
workers = 1
rsync_bwlimit_kbps = 0
log_level = "DEBUG"

[naming]
date_fmt = "%Y%m%d"
token_source = "hostname"
pattern = "{date}_{token}_d{disk}_p{part}"

[integrity]
algorithm = "sha256"

[output]
run_summary_dir = "/tmp/docrip-test-logs"
per_volume_json = true
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
        f.write(toml_content)
        f.flush()
        yield Path(f.name)
    
    # Cleanup
    Path(f.name).unlink(missing_ok=True)


@pytest.fixture
def sample_config():
    """Create a sample configuration object for testing."""
    return Config(
        server_rsync_remote="test@localhost:/tmp/docrip-test",
        server_ssh_key="/tmp/test-key",
        server_port=22,
        compressor="zstd",
        compression_level=1,
        chunk_size_mb=10,
        stream_direct=False,
        spool_dir=Path("/tmp/docrip-test-spool"),
        preserve_xattrs=True,
        include_fstypes=["ext4", "ext3", "ext2"],
        skip_fstypes=["swap"],
        skip_if_encrypted=True,
        allow_lvm=False,
        allow_raid=False,
        min_partition_size_gb=1,
        avoid_devices=[],
        max_file_size_mb=1,
        workers=1,
        rsync_bwlimit_kbps=0,
        log_level="DEBUG",
        date_fmt="%Y%m%d",
        token_source="hostname",
        pattern="{date}_{token}_d{disk}_p{part}",
        integrity_algo="sha256",
        run_summary_dir=Path("/tmp/docrip-test-logs"),
        per_volume_json=True
    )