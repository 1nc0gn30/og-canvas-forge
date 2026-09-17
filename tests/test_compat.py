"""Tests for cross-platform compatibility and atomic file I/O utilities."""

import os
from pathlib import Path
import pytest

from og_canvas_forge.compat import (
    atomic_write_bytes,
    atomic_write_text,
    get_platform_info,
    normalize_path,
    safe_delete_dir,
    safe_delete_file,
    safe_read_bytes,
    safe_read_json,
    safe_read_text,
    safe_write_json,
)


def test_platform_info_detection():
    """Verify platform info structure is populated correctly."""
    info = get_platform_info()
    assert isinstance(info.os_name, str)
    assert isinstance(info.system, str)
    assert isinstance(info.python_version, str)
    assert isinstance(info.is_windows, bool)
    assert isinstance(info.is_linux, bool)
    assert isinstance(info.is_macos, bool)
    assert info.path_separator in ("/", "\\")


def test_normalize_path(temp_workspace: Path):
    """Verify path normalization resolves user paths, relative components, and strings."""
    test_file = temp_workspace / "subdir" / ".." / "target.txt"
    resolved = normalize_path(str(test_file))
    assert resolved == (temp_workspace / "target.txt").resolve()


def test_atomic_write_and_read_text(temp_workspace: Path):
    """Verify atomic write text produces exact content and parent dirs."""
    target_file = temp_workspace / "nested" / "deep" / "message.txt"
    content = "Hello OpenGraph Studio 🚀"
    
    written_path = atomic_write_text(target_file, content)
    assert written_path.is_file()
    assert written_path.read_text(encoding="utf-8") == content

    # Test safe_read_text
    read_back = safe_read_text(target_file)
    assert read_back == content

    # Non-existent file returns default
    missing = safe_read_text(temp_workspace / "non_existent.txt", default="fallback")
    assert missing == "fallback"


def test_atomic_write_and_read_bytes(temp_workspace: Path):
    """Verify atomic write binary data."""
    target_file = temp_workspace / "binary" / "data.bin"
    payload = b"\x00\x01\x02\xFF\xFE\xFD"

    written_path = atomic_write_bytes(target_file, payload)
    assert written_path.is_file()
    assert safe_read_bytes(target_file) == payload

    # Missing binary file
    missing = safe_read_bytes(temp_workspace / "ghost.bin", default=b"none")
    assert missing == b"none"


def test_safe_json_io(temp_workspace: Path):
    """Verify safe JSON serialization and parsing."""
    target_json = temp_workspace / "data.json"
    data = {
        "title": "Canvas Forge",
        "dimensions": [1200, 630],
        "active": True,
        "tags": ["python", "svg"],
    }

    safe_write_json(target_json, data)
    parsed = safe_read_json(target_json)
    assert parsed == data

    # Malformed JSON returns default
    bad_json = temp_workspace / "corrupted.json"
    atomic_write_text(bad_json, "{ bad json")
    fallback = safe_read_json(bad_json, default={"status": "error"})
    assert fallback == {"status": "error"}


def test_safe_delete_file_and_dir(temp_workspace: Path):
    """Verify safe deletion of files and directory trees."""
    f = temp_workspace / "to_delete.txt"
    atomic_write_text(f, "temp")
    assert f.exists()
    assert safe_delete_file(f) is True
    assert not f.exists()
    assert safe_delete_file(f) is True  # Idempotent

    d = temp_workspace / "dir_to_delete" / "child"
    d.mkdir(parents=True)
    (d / "file.txt").write_text("dummy")
    assert safe_delete_dir(temp_workspace / "dir_to_delete") is True
    assert not (temp_workspace / "dir_to_delete").exists()
