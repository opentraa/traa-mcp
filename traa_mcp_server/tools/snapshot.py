"""Snapshot tool implementation for TRAA MCP server"""

import io
import numpy as np
from pydantic import BaseModel

from mcp.server.fastmcp.utilities.types import Image as MCPImage
from PIL import Image as PILImage

import traa

# Define public API
__all__ = [
    'enum_screen_sources',
    'create_snapshot',
    'save_snapshot',
    'SimpleScreenSourceInfo'
]

class SimpleScreenSourceInfo(BaseModel):
    """Simple container for screen source information"""
    id: int
    title: str
    is_window: bool
    rect: tuple[int, int, int, int]

def enum_screen_sources() -> list[SimpleScreenSourceInfo]:
    """Enumerate all available screen sources.

    Returns:
        List of SimpleScreenSourceInfo objects containing screen source information

    Raises:
        RuntimeError: If enumeration fails
    """
    try:
        sources = traa.enum_screen_sources()
        return [SimpleScreenSourceInfo(
            id=source.id,
            title=source.title,
            is_window=source.is_window,
            rect= (source.rect.left, source.rect.top, source.rect.right, source.rect.bottom)
        ) for source in sources]
    except traa.Error as e:
        raise RuntimeError(f"Failed to enumerate screen sources: {str(e)}") from e

def _create_snapshot(source_id: int, size: tuple[int, int], format: str) -> PILImage:
    """Create a snapshot of the specified screen source and return a PIL Image object.
    """

    if source_id < 0:
        raise ValueError("Source ID must be non-negative")
    
    width, height = size
    if width <= 0 or height <= 0:
        raise ValueError("Width and height must be positive")
    
    if format not in ["jpeg", "png"]:
        raise ValueError(f"Unsupported format: {format}")
    
    try:
        # create the snapshot
        result = traa.create_snapshot(int(source_id), traa.Size(size[0], size[1]))
        if result is None:
            raise RuntimeError("Invalid result format: traa.create_snapshot returned None")
        
        image_data, actual_size = result
        if not isinstance(image_data, np.ndarray) or not isinstance(actual_size, traa.Size):
            raise RuntimeError("Invalid result format: unexpected types")
        
        # assume the image is in RGBA format
        pil_image = PILImage.fromarray(image_data)

        if format == "jpeg":
            pil_image = pil_image.convert("RGB")

        return pil_image
    except traa.Error as e:
        raise RuntimeError(f"Failed to create snapshot: {e}")
    except Exception as e:
        raise RuntimeError(f"Unexpected error during snapshot creation: {e}")

def create_snapshot(source_id: int, size: tuple[int, int]) -> MCPImage:
    """Create a snapshot of the specified screen source.

    Args:
        source_id: ID of the screen source to capture
        size: Desired size of the snapshot (width, height)

    Returns:
        Image object containing the snapshot data

    Raises:
        ValueError: If source_id is negative or size is invalid
        RuntimeError: If snapshot creation fails
    """
    try:
        # if the file exceeds ~1MB, it may be rejected by AI models for now,
        # so we use JPEG format and set quality to 60 to reduce the file size
        const_format = "jpeg"

        # create the snapshot
        pil_image = _create_snapshot(int(source_id), size, const_format)

        # save the snapshot to a buffer
        buffer = io.BytesIO()
        pil_image.save(buffer, format=const_format, quality=60, optimize=True)

        # return the snapshot as an MCPImage object
        return MCPImage(data=buffer.getvalue(), format=const_format)
    except ValueError as e:
        # Re-raise ValueError as is
        raise e
    except Exception as e:
        raise RuntimeError(f"Unexpected error during snapshot creation: {e}")

def save_snapshot(source_id: int, size: tuple[int, int], file_path: str, quality: int = 80, format: str = "jpeg") -> None:
    """Create a snapshot and save it to a file.

    Args:
        source_id: ID of the screen source to capture
        size: Desired size of the snapshot (width, height)
        file_path: Path where the image should be saved
        format: Image format to save as (default: "jpeg"), only "jpeg" and "png" are supported

    Raises:
        ValueError: If source_id is negative or size is invalid
        RuntimeError: If snapshot creation or saving fails
        OSError: If file cannot be written
    """

    try:
        pil_image = _create_snapshot(int(source_id), size, format)
        
        # Ensure the directory exists
        import os
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)

        pil_image.save(file_path, format=format, quality=quality, optimize=True)
    except ValueError as e:
        # Re-raise ValueError as is
        raise e
    except Exception as e:
        raise RuntimeError(f"Failed to save snapshot: {e}")

if __name__ == "__main__":
    sources = enum_screen_sources()
    create_snapshot(sources[0].id, (1920, 1080))
    save_snapshot(sources[0].id, (1920, 1080), "snapshot_80.jpeg", 80, "jpeg")
    save_snapshot(sources[0].id, (1920, 1080), "snapshot_100.jpeg", 100, "jpeg")
    save_snapshot(sources[0].id, (1920, 1080), "snapshot_80.png", 80, "png")
    save_snapshot(sources[0].id, (1920, 1080), "snapshot_100.png", 100, "png")

