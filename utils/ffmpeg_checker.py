"""
FFmpeg environment checker.

Verifies FFmpeg availability in system PATH before attempting
M3U8 merging operations.
"""

import subprocess
from typing import Tuple


def check_ffmpeg() -> Tuple[bool, str]:
    """
    Check if FFmpeg is available in system PATH.
    
    Returns:
        Tuple of (is_available, version_or_error)
    """
    try:
        result = subprocess.run(
            ['ffmpeg', '-version'],
            capture_output=True,
            text=True,
            timeout=5,
            check=False
        )
        
        if result.returncode == 0:
            # Extract version from first line
            version_line = result.stdout.split('\n')[0]
            return True, version_line
        else:
            return False, "FFmpeg returned non-zero exit code"
            
    except FileNotFoundError:
        return False, "FFmpeg not found in PATH. Please install FFmpeg and add it to system PATH."
    except subprocess.TimeoutExpired:
        return False, "FFmpeg check timed out"
    except Exception as e:
        return False, f"Error checking FFmpeg: {str(e)}"


def get_ffmpeg_command() -> str:
    """
    Get the FFmpeg command name.
    
    Returns:
        'ffmpeg' on most systems, could be extended for platform-specific variants
    """
    return 'ffmpeg'
