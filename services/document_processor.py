import base64
import logging
import requests
import fitz  # PyMuPDF
from typing import List

# Configure logger
logger = logging.getLogger(__name__)


class DocumentProcessingError(Exception):
    """Raised when a document cannot be downloaded or converted to base64."""


def fetch_and_convert_to_base64(file_url: str, filename: str) -> List[str]:
    """
    Downloads a file from a public URL (like your Supabase storage bucket),
    identifies if it is a PDF or Image, and converts it into a list
    of base64-encoded PNG strings optimized for VLM ingestion.
    """
    try:
        logger.info("Downloading document for processing: %s", filename)
        # Timeout prevents infinite hangs if the storage bucket is unreachable
        response = requests.get(file_url, stream=True, timeout=30)
        response.raise_for_status()
        file_bytes = response.content
    except requests.exceptions.RequestException as exc:
        logger.error("Failed to download file from %s: %s", file_url, exc)
        raise DocumentProcessingError(f"Download failed: {exc}") from exc

    return process_bytes_to_base64(file_bytes, filename)


def process_bytes_to_base64(file_bytes: bytes, filename: str) -> List[str]:
    """
    Core conversion logic. Decoupled from downloading so you can also
    pass raw bytes directly from a webhook if needed.
    """
    base64_images = []
    filename_lower = filename.lower()

    try:
        if filename_lower.endswith('.pdf'):
            logger.info("Processing PDF document: %s", filename)
            # Open PDF directly from the byte stream in memory (no disk I/O needed)
            doc = fitz.open(stream=file_bytes, filetype="pdf")

            # Extract up to the first 2 pages (TNB bills and quotes rarely need more)
            for page_num in range(min(2, doc.page_count)):
                page = doc.load_page(page_num)

                # Matrix(2, 2) scales the resolution by 2x. This is critical
                # so the Qwen2-VL model can read the small tariff codes on a TNB bill.
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                img_bytes = pix.tobytes("png")

                b64_str = base64.b64encode(img_bytes).decode('utf-8')
                base64_images.append(b64_str)
            doc.close()

        elif filename_lower.endswith(('.png', '.jpg', '.jpeg', '.webp')):
            logger.info("Processing standard image: %s", filename)
            b64_str = base64.b64encode(file_bytes).decode('utf-8')
            base64_images.append(b64_str)

        else:
            logger.warning("Unsupported extension for %s. Attempting raw image conversion.", filename)
            b64_str = base64.b64encode(file_bytes).decode('utf-8')
            base64_images.append(b64_str)

        logger.info("Successfully converted %s into %d base64 image(s).", filename, len(base64_images))
        return base64_images

    except Exception as exc:
        logger.exception("Failed to process document payload for %s", filename)
        raise DocumentProcessingError(f"Processing failed: {exc}") from exc