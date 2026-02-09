"""
M3U8 stream handler with FFmpeg integration.

Handles M3U8 playlist parsing, segment downloading, and merging.
"""

import os
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional, Callable

import m3u8
import requests

from .models import Resource, DownloadStatus
from utils.logger import setup_logger
from utils.sanitizer import sanitize_filename
from utils.ffmpeg_checker import get_ffmpeg_command


logger = setup_logger(__name__)


class M3U8Handler:
    """
    M3U8 playlist handler with segment downloading and FFmpeg merging.
    
    Workflow:
    1. Parse M3U8 playlist
    2. Download all segments to temp directory
    3. Merge segments using FFmpeg
    4. Clean up temp files
    """
    
    def __init__(self, output_dir: str = './downloads', timeout: int = 30):
        """
        Initialize M3U8 handler.
        
        Args:
            output_dir: Directory to save merged videos
            timeout: Request timeout in seconds
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout
    
    def download_m3u8(
        self,
        resource: Resource,
        progress_callback: Optional[Callable[[float], None]] = None,
        is_cancelled: Optional[Callable[[], bool]] = None
    ) -> bool:
        """
        Download and merge M3U8 stream.
        
        Args:
            resource: M3U8 resource object
            progress_callback: Progress callback function
            is_cancelled: Cancellation check function
        
        Returns:
            True if successful, False otherwise
        """
        temp_dir = None
        
        try:
            # Parse M3U8 playlist
            logger.info(f"Parsing M3U8 playlist: {resource.url}")
            playlist = self._parse_playlist(resource.url, resource.headers)
            
            if not playlist:
                resource.mark_failed("Failed to parse M3U8 playlist")
                return False
            
            segments = playlist.segments
            if not segments:
                resource.mark_failed("No segments found in M3U8 playlist")
                return False
            
            logger.info(f"Found {len(segments)} segments")
            
            # Download segments
            temp_dir = tempfile.mkdtemp(prefix='m3u8_')
            segment_files = self._download_segments(
                segments,
                playlist.base_uri or resource.url,
                temp_dir,
                resource.headers,
                progress_callback,
                is_cancelled
            )
            
            if is_cancelled and is_cancelled():
                resource.status = DownloadStatus.CANCELLED
                return False
            
            if not segment_files:
                resource.mark_failed("Failed to download segments")
                return False
            
            # Merge segments
            logger.info("Merging segments with FFmpeg...")
            resource.status = DownloadStatus.MERGING
            
            output_path = self._merge_segments(segment_files, resource)
            
            if not output_path:
                resource.mark_failed("Failed to merge segments")
                return False
            
            # Mark as completed
            resource.mark_completed(str(output_path))
            logger.info(f"M3U8 download completed: {output_path}")
            return True
            
        except Exception as e:
            error_msg = f"M3U8 download error: {e}"
            logger.error(error_msg)
            resource.mark_failed(error_msg)
            return False
        
        finally:
            # Clean up temp directory
            if temp_dir and os.path.exists(temp_dir):
                try:
                    import shutil
                    shutil.rmtree(temp_dir)
                    logger.debug(f"Cleaned up temp directory: {temp_dir}")
                except Exception as e:
                    logger.warning(f"Failed to clean up temp directory: {e}")
    
    def _parse_playlist(self, url: str, headers: dict) -> Optional[m3u8.M3U8]:
        """Parse M3U8 playlist from URL."""
        try:
            response = requests.get(url, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            
            playlist = m3u8.loads(response.text)
            playlist.base_uri = url.rsplit('/', 1)[0] + '/'
            
            return playlist
            
        except Exception as e:
            logger.error(f"Failed to parse M3U8 playlist: {e}")
            return None
    
    def _download_segments(
        self,
        segments: List,
        base_uri: str,
        temp_dir: str,
        headers: dict,
        progress_callback: Optional[Callable[[float], None]],
        is_cancelled: Optional[Callable[[], bool]]
    ) -> List[str]:
        """Download all segments to temp directory."""
        segment_files = []
        total_segments = len(segments)
        
        for i, segment in enumerate(segments):
            # Check cancellation
            if is_cancelled and is_cancelled():
                logger.info("Segment download cancelled")
                return []
            
            # Construct segment URL
            segment_url = segment.uri
            if not segment_url.startswith('http'):
                segment_url = base_uri + segment_url
            
            # Download segment
            segment_path = os.path.join(temp_dir, f'segment_{i:05d}.ts')
            
            try:
                response = requests.get(segment_url, headers=headers, timeout=self.timeout)
                response.raise_for_status()
                
                with open(segment_path, 'wb') as f:
                    f.write(response.content)
                
                segment_files.append(segment_path)
                
                # Report progress (50% for download, 50% for merge)
                if progress_callback:
                    progress = (i + 1) / total_segments * 0.5
                    progress_callback(progress)
                
                logger.debug(f"Downloaded segment {i + 1}/{total_segments}")
                
            except Exception as e:
                logger.error(f"Failed to download segment {i}: {e}")
                return []
        
        return segment_files
    
    def _merge_segments(self, segment_files: List[str], resource: Resource) -> Optional[str]:
        """Merge segments using FFmpeg."""
        try:
            # Prepare output filename
            safe_name = sanitize_filename(resource.title or 'video')
            if not safe_name.endswith('.mp4'):
                safe_name += '.mp4'
            
            output_path = self.output_dir / safe_name
            
            # Create file list for FFmpeg
            list_file = os.path.join(os.path.dirname(segment_files[0]), 'filelist.txt')
            with open(list_file, 'w', encoding='utf-8') as f:
                for segment in segment_files:
                    # Use forward slashes for FFmpeg on Windows
                    segment_path = segment.replace('\\', '/')
                    f.write(f"file '{segment_path}'\n")
            
            # Run FFmpeg
            ffmpeg_cmd = get_ffmpeg_command()
            cmd = [
                ffmpeg_cmd,
                '-f', 'concat',
                '-safe', '0',
                '-i', list_file,
                '-c', 'copy',
                '-y',  # Overwrite output file
                str(output_path)
            ]
            
            logger.debug(f"Running FFmpeg: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes timeout
            )
            
            if result.returncode == 0:
                logger.info(f"FFmpeg merge successful: {output_path}")
                return str(output_path)
            else:
                logger.error(f"FFmpeg error: {result.stderr}")
                return None
                
        except subprocess.TimeoutExpired:
            logger.error("FFmpeg merge timed out")
            return None
        except Exception as e:
            logger.error(f"FFmpeg merge failed: {e}")
            return None
