"""Cross-platform compatibility utilities for og-canvas-forge.

Provides atomic file I/O (with fsync), safe path normalization across
Linux, macOS, Windows, WSL, and Termux environments, safe JSON serialization,
and comprehensive platform detection.
"""

from __future__ import annotations

import json
import os
import platform
import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Union


@dataclass(frozen=True)
class PlatformInfo:
    """System platform and runtime environment metadata."""

    os_name: str
    system: str
    release: str
    is_windows: bool
    is_linux: bool
    is_macos: bool
    is_termux: bool
    is_wsl: bool
    python_version: str
    path_separator: str
    newline: str


def _detect_termux() -> bool:
    """Check if running in Android Termux environment."""
    return (
        bool(os.environ.get("TERMUX_VERSION"))
        or bool(os.environ.get("PREFIX", "").startswith("/data/data/com.termux"))
        or Path("/data/data/com.termux").exists()
    )


def _detect_wsl() -> bool:
    """Check if running inside Windows Subsystem for Linux."""
    if sys.platform != "linux":
        return False
    try:
        proc_ver = Path("/proc/version")
        if proc_ver.exists():
            content = proc_ver.read_text(encoding="utf-8", errors="ignore").lower()
            return "microsoft" in content or "wsl" in content
    except Exception:
        pass
    return False


def get_platform_info() -> PlatformInfo:
    """Retrieve detailed platform detection metadata."""
    sys_name = platform.system()
    return PlatformInfo(
        os_name=os.name,
        system=sys_name,
        release=platform.release(),
        is_windows=(sys_name == "Windows"),
        is_linux=(sys_name == "Linux"),
        is_macos=(sys_name == "Darwin"),
        is_termux=_detect_termux(),
        is_wsl=_detect_wsl(),
        python_version=platform.python_version(),
        path_separator=os.sep,
        newline=os.linesep,
    )


def normalize_path(path: Union[str, Path]) -> Path:
    """Normalize and resolve a filesystem path safely across platforms.

    Expands `~` (user home), resolves symlinks/relative segments, and normalizes
    directory separators for the current OS.
    """
    if isinstance(path, str):
        path = Path(path.strip())
    try:
        return path.expanduser().resolve()
    except Exception:
        # Fallback to simple absolute path if resolve fails (e.g. permission or special mounts)
        return path.expanduser().absolute()


def atomic_write_bytes(file_path: Union[str, Path], data: bytes) -> Path:
    """Atomically write binary data to a file using a temp file and fsync.

    Guarantees that readers will never observe a partially written or corrupted
    file, even on abrupt process termination or power loss.
    """
    target = normalize_path(file_path)
    parent_dir = target.parent
    parent_dir.mkdir(parents=True, exist_ok=True)

    temp_file = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=parent_dir,
            delete=False,
            prefix=f".tmp_{target.stem}_",
            suffix=".tmp",
        ) as f:
            temp_file = Path(f.name)
            f.write(data)
            f.flush()
            try:
                os.fsync(f.fileno())
            except (AttributeError, OSError):
                # fsync may not be supported on some in-memory filesystems
                pass

        # Atomic replacement (POSIX atomic rename, Windows atomic in Python 3.3+)
        os.replace(temp_file, target)
        return target
    except Exception:
        if temp_file and temp_file.exists():
            try:
                temp_file.unlink(missing_ok=True)
            except Exception:
                pass
        raise


def atomic_write_text(
    file_path: Union[str, Path],
    content: str,
    encoding: str = "utf-8",
) -> Path:
    """Atomically write string content to a file with specified encoding."""
    return atomic_write_bytes(file_path, content.encode(encoding))


def safe_read_bytes(
    file_path: Union[str, Path],
    default: Optional[bytes] = None,
) -> Optional[bytes]:
    """Safely read binary data from a file, returning default on error."""
    try:
        path = normalize_path(file_path)
        if path.is_file():
            return path.read_bytes()
    except Exception:
        pass
    return default


def safe_read_text(
    file_path: Union[str, Path],
    encoding: str = "utf-8",
    default: Optional[str] = None,
) -> Optional[str]:
    """Safely read text from a file, returning default on error."""
    try:
        path = normalize_path(file_path)
        if path.is_file():
            return path.read_text(encoding=encoding, errors="replace")
    except Exception:
        pass
    return default


def safe_write_json(
    file_path: Union[str, Path],
    data: Any,
    indent: int = 2,
    ensure_ascii: bool = False,
) -> Path:
    """Serialize and atomically write data to a JSON file."""
    content = json.dumps(data, indent=indent, ensure_ascii=ensure_ascii, default=str)
    return atomic_write_text(file_path, content + "\n")


def safe_read_json(
    file_path: Union[str, Path],
    default: Any = None,
) -> Any:
    """Read and parse a JSON file, returning default on any failure."""
    text = safe_read_text(file_path)
    if text is None:
        return default
    try:
        return json.loads(text)
    except Exception:
        return default


def safe_delete_file(file_path: Union[str, Path]) -> bool:
    """Safely delete a file if it exists. Returns True if deleted or already absent."""
    try:
        path = normalize_path(file_path)
        if path.exists() and path.is_file():
            path.unlink(missing_ok=True)
            return True
        return not path.exists()
    except Exception:
        return False


def safe_delete_dir(dir_path: Union[str, Path]) -> bool:
    """Safely delete a directory and its contents if it exists."""
    try:
        path = normalize_path(dir_path)
        if path.exists() and path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
            return True
        return not path.exists()
    except Exception:
        return False
