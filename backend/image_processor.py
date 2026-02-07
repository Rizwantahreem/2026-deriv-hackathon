"""
Image Processor - Handles image preprocessing for document analysis.
Validates, resizes, and assesses image quality before AI analysis.
"""

import io
import base64
from typing import Tuple, Optional
from PIL import Image, ImageFilter, ImageStat
import hashlib


# Supported image formats
SUPPORTED_FORMATS = {'JPEG', 'JPG', 'PNG'}
SUPPORTED_MIME_TYPES = {'image/jpeg', 'image/png', 'image/jpg'}

# Size limits
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10MB
MAX_DIMENSION = 4096  # Maximum width/height
TARGET_SIZE = 1536  # Target size for AI analysis (higher for better text clarity)
MIN_DIMENSION = 200  # Minimum acceptable dimension


class ImageProcessingError(Exception):
    """Raised when image processing fails."""
    pass


def validate_image_format(file_bytes: bytes, mime_type: Optional[str] = None) -> Tuple[bool, str]:
    """
    Validate that the uploaded file is a supported image format.
    
    Args:
        file_bytes: Raw file bytes
        mime_type: MIME type from upload (optional)
    
    Returns:
        Tuple of (is_valid, message)
    """
    # Check file size
    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        size_mb = len(file_bytes) / (1024 * 1024)
        return False, f"File too large: {size_mb:.1f}MB (max 10MB)"
    
    if len(file_bytes) < 1000:  # Less than 1KB is suspicious
        return False, "File too small - may be corrupted"
    
    # Try to open with PIL to validate format
    try:
        image = Image.open(io.BytesIO(file_bytes))
        image_format = image.format
        
        if image_format not in SUPPORTED_FORMATS:
            return False, f"Unsupported format: {image_format}. Use JPEG or PNG."
        
        # Verify the image can be fully loaded (not truncated)
        image.verify()
        
        return True, f"Valid {image_format} image"
        
    except Exception as e:
        return False, f"Invalid or corrupted image: {str(e)}"


def load_image(file_bytes: bytes) -> Image.Image:
    """Load image from bytes, handling various formats."""
    try:
        image = Image.open(io.BytesIO(file_bytes))
        # Convert to RGB if necessary (handles RGBA, P mode, etc.)
        if image.mode in ('RGBA', 'P', 'LA'):
            # Create white background for transparency
            background = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'P':
                image = image.convert('RGBA')
            background.paste(image, mask=image.split()[-1] if 'A' in image.mode else None)
            image = background
        elif image.mode != 'RGB':
            image = image.convert('RGB')
        return image
    except Exception as e:
        raise ImageProcessingError(f"Failed to load image: {str(e)}")


def resize_for_analysis(image: Image.Image, max_size: int = TARGET_SIZE) -> Image.Image:
    """
    Resize image for AI analysis while maintaining aspect ratio.
    
    Args:
        image: PIL Image object
        max_size: Maximum dimension (width or height)
    
    Returns:
        Resized image
    """
    width, height = image.size
    
    # If already smaller than max_size, return as-is
    if width <= max_size and height <= max_size:
        return image
    
    # Calculate new dimensions maintaining aspect ratio
    if width > height:
        new_width = max_size
        new_height = int(height * (max_size / width))
    else:
        new_height = max_size
        new_width = int(width * (max_size / height))
    
    # Use high-quality resampling
    resized = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
    return resized


def convert_to_base64(image: Image.Image, format: str = 'JPEG', quality: int = 92) -> str:
    """
    Convert PIL Image to base64 string for API transmission.
    
    Args:
        image: PIL Image object
        format: Output format (JPEG or PNG)
        quality: JPEG quality (1-100)
    
    Returns:
        Base64 encoded string
    """
    buffer = io.BytesIO()
    
    if format.upper() == 'PNG':
        image.save(buffer, format='PNG', optimize=True)
    else:
        image.save(buffer, format='JPEG', quality=quality, optimize=True)
    
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode('utf-8')


def base64_to_image(base64_string: str) -> Image.Image:
    """Convert base64 string back to PIL Image."""
    # Handle data URL format
    if ',' in base64_string:
        base64_string = base64_string.split(',')[1]
    
    image_bytes = base64.b64decode(base64_string)
    return load_image(image_bytes)


def calculate_md5_checksum(file_bytes: bytes) -> str:
    """Calculate MD5 checksum for file (used by Deriv API)."""
    return hashlib.md5(file_bytes).hexdigest()


def assess_basic_quality(image: Image.Image) -> dict:
    """
    Assess basic image quality metrics.
    
    Returns dict with:
        - is_blurry: bool
        - is_too_dark: bool
        - is_too_bright: bool
        - resolution_ok: bool
        - blur_score: float (lower = blurrier)
        - brightness: float (0-255)
        - contrast: float
    """
    # Convert to grayscale for analysis
    gray = image.convert('L')
    
    # 1. Check blur using Laplacian variance
    # Apply edge detection and measure variance
    edges = gray.filter(ImageFilter.FIND_EDGES)
    edge_stat = ImageStat.Stat(edges)
    blur_score = edge_stat.var[0]  # Variance of edge detection
    
    # Lower variance = more blur
    # Threshold determined experimentally
    is_blurry = blur_score < 100
    
    # 2. Check brightness
    stat = ImageStat.Stat(gray)
    brightness = stat.mean[0]  # Average pixel value (0-255)
    
    is_too_dark = brightness < 40
    is_too_bright = brightness > 235
    
    # 3. Check contrast (standard deviation of pixel values)
    contrast = stat.stddev[0]
    low_contrast = contrast < 30
    
    # 4. Check resolution
    width, height = image.size
    resolution_ok = width >= MIN_DIMENSION and height >= MIN_DIMENSION
    
    return {
        "is_blurry": is_blurry,
        "is_too_dark": is_too_dark,
        "is_too_bright": is_too_bright,
        "low_contrast": low_contrast,
        "resolution_ok": resolution_ok,
        "blur_score": round(blur_score, 2),
        "brightness": round(brightness, 2),
        "contrast": round(contrast, 2),
        "width": width,
        "height": height
    }


def get_image_orientation(image: Image.Image) -> str:
    """
    Detect image orientation.
    
    Returns: 'landscape', 'portrait', or 'square'
    """
    width, height = image.size
    
    if width > height * 1.1:
        return 'landscape'
    elif height > width * 1.1:
        return 'portrait'
    else:
        return 'square'


def process_document_image(
    file_bytes: bytes,
    mime_type: Optional[str] = None
) -> Tuple[str, dict]:
    """
    Full preprocessing pipeline for document images.
    
    Args:
        file_bytes: Raw uploaded file bytes
        mime_type: MIME type from upload
    
    Returns:
        Tuple of (base64_image, quality_assessment)
    
    Raises:
        ImageProcessingError: If image is invalid or processing fails
    """
    # Step 1: Validate format
    is_valid, message = validate_image_format(file_bytes, mime_type)
    if not is_valid:
        raise ImageProcessingError(message)
    
    # Step 2: Load image
    image = load_image(file_bytes)
    
    # Step 3: Assess quality BEFORE resize (on original)
    quality = assess_basic_quality(image)
    quality['orientation'] = get_image_orientation(image)
    quality['original_size'] = f"{image.size[0]}x{image.size[1]}"
    quality['file_size_kb'] = len(file_bytes) / 1024
    
    # Step 4: Resize for API
    resized = resize_for_analysis(image)
    quality['processed_size'] = f"{resized.size[0]}x{resized.size[1]}"
    
    # Step 5: Convert to base64 (PNG preserves text edges better for OCR)
    base64_image = convert_to_base64(resized, format="PNG")
    
    # Step 6: Calculate checksum (for Deriv API)
    quality['checksum'] = calculate_md5_checksum(file_bytes)
    
    return base64_image, quality
