"""
Tests for archiver module.
"""
import pytest
from pathlib import Path
from docrip.archiver import build_find_cmd, compressor_cmd
from docrip.types import Config


def test_build_find_cmd_with_size_limit():
    """Test find command generation with file size limit."""
    mp = Path("/mnt/test")
    cmd = build_find_cmd(mp, 100)
    
    assert "cd '/mnt/test'" in cmd
    assert "find . -xdev" in cmd
    assert "-size -100M" in cmd
    assert "-type d -print0" in cmd
    assert "-type l -print0" in cmd
    assert "-type f" in cmd


def test_build_find_cmd_no_size_limit():
    """Test find command generation without file size limit."""
    mp = Path("/mnt/test")
    cmd = build_find_cmd(mp, 0)
    
    assert "cd '/mnt/test'" in cmd
    assert "find . -xdev" in cmd
    assert "-size" not in cmd
    assert "-type d -print0" in cmd
    assert "-type l -print0" in cmd
    assert "-type f -print0" in cmd


def test_compressor_cmd_zstd():
    """Test zstd compressor command generation."""
    # Create a minimal config
    config = type('Config', (), {
        'compressor': 'zstd',
        'compression_level': 5
    })()
    
    cmd = compressor_cmd(config, 4)
    assert cmd == "zstd -T4 -5"


def test_compressor_cmd_pigz():
    """Test pigz compressor command generation."""
    config = type('Config', (), {
        'compressor': 'pigz', 
        'compression_level': 3
    })()
    
    cmd = compressor_cmd(config, 2)
    assert cmd == "pigz -p 2 -3"


def test_compressor_cmd_invalid():
    """Test invalid compressor raises error."""
    config = type('Config', (), {
        'compressor': 'invalid',
        'compression_level': 3
    })()
    
    with pytest.raises(ValueError):
        compressor_cmd(config, 2)