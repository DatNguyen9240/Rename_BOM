"""
Image preprocessing pipeline with Unicode path support, EXIF handling, CLAHE and Sharpening.
"""

import os
from typing import Optional, Tuple
import cv2
import numpy as np
from PIL import Image, ImageOps

from app.config import AppConfig


class ImageProcessor:
    """Provides safe Unicode image loading and OCR-optimized preprocessing."""

    @staticmethod
    def load_image_unicode(file_path: str) -> Optional[np.ndarray]:
        """
        Safely loads an image or PDF file supporting Unicode file paths on Windows.
        Loads file entirely via byte buffer to prevent Windows file locking issues.
        Returns a BGR numpy array compatible with OpenCV and PaddleOCR.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Image/PDF not found: {file_path}")

        ext = os.path.splitext(file_path)[1].lower()

        # Read all bytes into RAM first so Windows file handle is released immediately
        try:
            with open(file_path, "rb") as f:
                file_bytes = f.read()
        except Exception as e:
            print(f"[ImageProcessor] Error reading file bytes {file_path}: {e}")
            return None

        # Handle PDF files via in-memory buffer
        if ext == ".pdf":
            try:
                import pypdfium2 as pdfium
                pdf = pdfium.PdfDocument(file_bytes)
                try:
                    if len(pdf) > 0:
                        page = pdf.get_page(0)
                        try:
                            bmp = page.render(scale=1.5)
                            pil_img = bmp.to_pil()
                            if pil_img.mode != "RGB":
                                pil_img = pil_img.convert("RGB")
                            rgb_arr = np.array(pil_img)
                            bgr_arr = cv2.cvtColor(rgb_arr, cv2.COLOR_RGB2BGR)
                            return bgr_arr
                        finally:
                            page.close()
                finally:
                    pdf.close()
            except Exception as e:
                print(f"[ImageProcessor] Error rendering PDF {file_path}: {e}")
                return None

        # Handle Images via in-memory buffer with PIL and OpenCV fallback
        try:
            import io
            with Image.open(io.BytesIO(file_bytes)) as pil_img:
                pil_img = ImageOps.exif_transpose(pil_img)
                if pil_img.mode != "RGB":
                    pil_img = pil_img.convert("RGB")
                rgb_arr = np.array(pil_img)
                bgr_arr = cv2.cvtColor(rgb_arr, cv2.COLOR_RGB2BGR)
                return bgr_arr
        except Exception:
            try:
                np_arr = np.frombuffer(file_bytes, dtype=np.uint8)
                img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
                return img
            except Exception as e:
                print(f"[ImageProcessor] Failed to decode image {file_path}: {e}")
                return None

    @classmethod
    def resize_keep_aspect_ratio(
        cls, img: np.ndarray, max_dim: int = 2000
    ) -> Tuple[np.ndarray, float]:
        """Resizes image if its largest dimension exceeds max_dim, keeping aspect ratio."""
        h, w = img.shape[:2]
        largest_dim = max(h, w)
        if largest_dim <= max_dim:
            return img, 1.0

        scale = max_dim / float(largest_dim)
        new_w = max(1, int(w * scale))
        new_h = max(1, int(h * scale))
        resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
        return resized, scale

    @classmethod
    def enhance_contrast_clahe(cls, gray: np.ndarray, clip_limit: float = 2.5) -> np.ndarray:
        """Applies Contrast Limited Adaptive Histogram Equalization (CLAHE) on grayscale."""
        clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(8, 8))
        return clahe.apply(gray)

    @classmethod
    def sharpen(cls, img: np.ndarray) -> np.ndarray:
        """Applies Unsharp Masking filter to emphasize character edges."""
        gaussian = cv2.GaussianBlur(img, (0, 0), sigmaX=2.0)
        unsharp = cv2.addWeighted(img, 1.5, gaussian, -0.5, 0)
        return unsharp

    @classmethod
    def apply_adaptive_threshold(cls, gray: np.ndarray) -> np.ndarray:
        """Converts grayscale image to binary image with adaptive thresholding."""
        binary = cv2.adaptiveThreshold(
            gray,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            blockSize=19,
            C=9
        )
        return binary

    @classmethod
    def preprocess_for_ocr(cls, img: np.ndarray, config: AppConfig) -> np.ndarray:
        """
        Executes full preprocessing pipeline according to configuration.
        Returns preprocessed BGR or 3-channel matrix optimal for PaddleOCR.
        """
        if not config.enable_preprocessing or img is None:
            return img

        processed = img.copy()

        # 1. Resize if too large
        if config.max_dimension > 0:
            processed, _ = cls.resize_keep_aspect_ratio(processed, config.max_dimension)

        # 2. Grayscale & Contrast
        if config.to_grayscale or config.enhance_contrast_clahe or config.adaptive_threshold:
            if len(processed.shape) == 3:
                gray = cv2.cvtColor(processed, cv2.COLOR_BGR2GRAY)
            else:
                gray = processed

            # CLAHE
            if config.enhance_contrast_clahe:
                gray = cls.enhance_contrast_clahe(gray, config.clahe_clip_limit)

            # Sharpening
            if config.sharpen_image:
                gray = cls.sharpen(gray)

            # Binarization
            if config.adaptive_threshold:
                gray = cls.apply_adaptive_threshold(gray)

            # Convert back to 3-channel BGR for PaddleOCR standard input
            processed = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        else:
            if config.sharpen_image:
                processed = cls.sharpen(processed)

        return processed
