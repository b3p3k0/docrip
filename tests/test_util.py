"""
Tests for utility functions.
"""
import pytest
from docrip.util import base36_digest5, host_identifier, clamp, utc_datestr


def test_base36_digest5():
    """Test stable token generation."""
    # Same input should produce same output
    token1 = base36_digest5("test:host-id")
    token2 = base36_digest5("test:host-id")
    assert token1 == token2
    
    # Different inputs should produce different outputs
    token3 = base36_digest5("different:host-id")
    assert token1 != token3
    
    # Should be exactly 5 characters
    assert len(token1) == 5
    
    # Should be base36 characters only
    valid_chars = set("0123456789abcdefghijklmnopqrstuvwxyz")
    assert all(c in valid_chars for c in token1)


def test_host_identifier():
    """Test host identifier generation."""
    # Should return something non-empty
    host_id = host_identifier()
    assert host_id
    assert len(host_id) > 0
    
    # Should be consistent between calls
    host_id2 = host_identifier()
    assert host_id == host_id2


def test_clamp():
    """Test value clamping function."""
    assert clamp(0, 5, 10) == 5
    assert clamp(0, -1, 10) == 0
    assert clamp(0, 15, 10) == 10
    assert clamp(5, 7, 10) == 7


def test_utc_datestr():
    """Test UTC date string formatting."""
    date_str = utc_datestr("%Y%m%d")
    assert len(date_str) == 8
    assert date_str.isdigit()
    
    # Should be today's date in YYYYMMDD format
    import datetime
    today = datetime.datetime.now(datetime.timezone.utc)
    expected = today.strftime("%Y%m%d")
    assert date_str == expected