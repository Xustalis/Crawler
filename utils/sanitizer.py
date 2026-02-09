"""
Filename sanitizer for safe file system operations.

Removes illegal characters and handles edge cases like reserved names.
"""

import re
from pathlib import Path


# Windows reserved characters
ILLEGAL_CHARS = r'[<>:"/\\|?*\x00-\x1f]'

# Windows reserved names
RESERVED_NAMES = {
    'CON', 'PRN', 'AUX', 'NUL',
    'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
    'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
}


def sanitize_filename(filename: str, replacement: str = '_', max_length: int = 200) -> str:
    """
    Sanitize filename for safe file system usage.
    
    Args:
        filename: Original filename
        replacement: Character to replace illegal chars with
        max_length: Maximum filename length (excluding extension)
    
    Returns:
        Sanitized filename safe for Windows/Linux/macOS
    
    Examples:
        >>> sanitize_filename('video:title.mp4')
        'video_title.mp4'
        >>> sanitize_filename('CON.txt')
        'CON_.txt'
    """
    if not filename:
        return 'unnamed'
    
    # Split name and extension
    path = Path(filename)
    name = path.stem
    ext = path.suffix
    
    # Remove illegal characters
    name = re.sub(ILLEGAL_CHARS, replacement, name)
    
    # Remove leading/trailing spaces and dots
    name = name.strip('. ')
    
    # Check for reserved names (case-insensitive)
    if name.upper() in RESERVED_NAMES:
        name += '_'
    
    # Ensure not empty after sanitization
    if not name:
        name = 'unnamed'
    
    # Truncate if too long
    if len(name) > max_length:
        name = name[:max_length].rstrip('. ')
    
    return name + ext


def safe_join_path(base_dir: str, *parts: str) -> Path:
    """
    Safely join path components and prevent directory traversal.
    
    Args:
        base_dir: Base directory
        *parts: Path components to join
    
    Returns:
        Resolved Path object confined to base_dir
    
    Raises:
        ValueError: If resulting path escapes base_dir
    """
    base = Path(base_dir).resolve()
    target = base.joinpath(*parts).resolve()
    
    # Ensure target is within base directory
    try:
        target.relative_to(base)
    except ValueError:
        raise ValueError(f"Path traversal detected: {parts}")
    
    return target
