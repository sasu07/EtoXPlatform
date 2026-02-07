"""
pix2text_processor.py

Module for processing PDFs using pix2text library.
Extracts text and mathematical formulas from PDF documents.
"""

import os
import platform
from typing import List, Dict, Optional
from pathlib import Path
from pix2text import Pix2Text
from pdf2image import convert_from_path
import tempfile


def get_poppler_path():
    """
    Get the poppler path based on the operating system.
    Returns None if poppler is in PATH or path to poppler binaries.
    """
    system = platform.system()

    if system == "Darwin":  # macOS
        # Check common Homebrew locations
        homebrew_paths = [
            "/opt/homebrew/bin",  # Apple Silicon
            "/usr/local/bin",      # Intel
        ]
        for path in homebrew_paths:
            if os.path.exists(os.path.join(path, "pdfinfo")):
                return path

    # For Linux and Windows, assume poppler is in PATH
    return None


class Pix2TextProcessor:
    """
    Handles PDF processing using pix2text for OCR and formula recognition.
    """

    def __init__(self):
        """Initialize the pix2text model and poppler path."""
        try:
            # Initialize pix2text with multilingual support
            # Use CPU by default to avoid CoreML issues on macOS (sequence length resizing error)
            # Can be overridden by PIX2TEXT_DEVICE environment variable
            device = os.getenv("PIX2TEXT_DEVICE", "cpu")
            print(f"Initializing Pix2Text with device: {device}")
            self.p2t = Pix2Text.from_config(device=device)
            # Get poppler path
            self.poppler_path = get_poppler_path()
            print(f"Pix2Text initialized successfully")
            if self.poppler_path:
                print(f"Using poppler from: {self.poppler_path}")
        except Exception as e:
            print(f"Error initializing Pix2Text: {e}")
            self.p2t = None
            self.poppler_path = None

    def process_pdf(self, pdf_path: str, dpi: int = 300) -> List[Dict[str, any]]:
        """
        Process a PDF file and extract text and formulas from each page.

        Args:
            pdf_path: Path to the PDF file
            dpi: Resolution for PDF to image conversion (default: 300)

        Returns:
            List of dictionaries containing page data with extracted text and formulas
        """
        if not self.p2t:
            raise RuntimeError("Pix2Text not initialized properly")

        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        results = []

        try:
            # Convert PDF pages to images
            print(f"Converting PDF to images: {pdf_path}")
            images = convert_from_path(
                pdf_path,
                dpi=dpi,
                poppler_path=self.poppler_path
            )

            # Process each page
            for page_num, image in enumerate(images, start=1):
                print(f"Processing page {page_num}/{len(images)}")

                # Save image temporarily
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
                    tmp_path = tmp_file.name
                    image.save(tmp_path, 'PNG')

                try:
                    # Extract text and formulas using pix2text
                    result = self.p2t.recognize_page(tmp_path)

                    # Extract text from result (handle both dict and object)
                    if hasattr(result, 'to_markdown'):
                        # Best way for Page objects in recent versions
                        # Requires an output directory for images in version 1.1.x+
                        with tempfile.TemporaryDirectory() as out_dir:
                            raw_text = result.to_markdown(out_dir)
                        latex_formulas = []
                        if hasattr(result, 'latex'):
                            latex_formulas = result.latex if isinstance(result.latex, list) else [result.latex]
                    elif hasattr(result, 'text'):
                        # It's a Page object or similar
                        raw_text = str(result.text) if result.text else ''
                        latex_formulas = []
                        # Try to extract LaTeX if available
                        if hasattr(result, 'latex'):
                            latex_formulas = result.latex if isinstance(result.latex, list) else [result.latex]
                    elif isinstance(result, dict):
                        # It's a dictionary
                        raw_text = result.get('text', '')
                        latex_formulas = result.get('latex', [])
                    else:
                        # Fallback: convert to string
                        raw_text = str(result)
                        latex_formulas = []

                    page_data = {
                        'page_number': page_num,
                        'raw_text': raw_text,
                        'latex_formulas': latex_formulas if isinstance(latex_formulas, list) else [],
                        'width': image.width,
                        'height': image.height
                    }

                    results.append(page_data)

                except Exception as e:
                    print(f"Error processing page {page_num}: {e}")
                    results.append({
                        'page_number': page_num,
                        'error': str(e),
                        'raw_text': '',
                        'latex_formulas': []
                    })
                finally:
                    # Clean up temporary file
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)

            return results

        except Exception as e:
            raise RuntimeError(f"Error processing PDF: {e}")

    def process_pdf_segment(
        self,
        pdf_path: str,
        page_start: int,
        page_end: int,
        dpi: int = 300
    ) -> List[Dict[str, any]]:
        """
        Process a specific segment (page range) of a PDF.

        Args:
            pdf_path: Path to the PDF file
            page_start: Starting page number (1-indexed)
            page_end: Ending page number (1-indexed, inclusive)
            dpi: Resolution for PDF to image conversion

        Returns:
            List of dictionaries containing page data for the specified range
        """
        if not self.p2t:
            raise RuntimeError("Pix2Text not initialized properly")

        if page_start < 1 or page_end < page_start:
            raise ValueError("Invalid page range")

        try:
            # Convert only the specified pages
            images = convert_from_path(
                pdf_path,
                dpi=dpi,
                first_page=page_start,
                last_page=page_end,
                poppler_path=self.poppler_path
            )

            results = []

            for idx, image in enumerate(images):
                page_num = page_start + idx
                print(f"Processing page {page_num}")

                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
                    tmp_path = tmp_file.name
                    image.save(tmp_path, 'PNG')

                try:
                    result = self.p2t.recognize_page(tmp_path)

                    # Extract text from result (handle both dict and object)
                    if hasattr(result, 'to_markdown'):
                        # Best way for Page objects in recent versions
                        # Requires an output directory for images in version 1.1.x+
                        with tempfile.TemporaryDirectory() as out_dir:
                            raw_text = result.to_markdown(out_dir)
                        latex_formulas = []
                        if hasattr(result, 'latex'):
                            latex_formulas = result.latex if isinstance(result.latex, list) else [result.latex]
                    elif hasattr(result, 'text'):
                        # It's a Page object or similar
                        raw_text = str(result.text) if result.text else ''
                        latex_formulas = []
                        # Try to extract LaTeX if available
                        if hasattr(result, 'latex'):
                            latex_formulas = result.latex if isinstance(result.latex, list) else [result.latex]
                    elif isinstance(result, dict):
                        # It's a dictionary
                        raw_text = result.get('text', '')
                        latex_formulas = result.get('latex', [])
                    else:
                        # Fallback: convert to string
                        raw_text = str(result)
                        latex_formulas = []

                    page_data = {
                        'page_number': page_num,
                        'raw_text': raw_text,
                        'latex_formulas': latex_formulas if isinstance(latex_formulas, list) else [],
                        'width': image.width,
                        'height': image.height
                    }

                    results.append(page_data)

                except Exception as e:
                    print(f"Error processing page {page_num}: {e}")
                    results.append({
                        'page_number': page_num,
                        'error': str(e),
                        'raw_text': '',
                        'latex_formulas': []
                    })
                finally:
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)

            return results

        except Exception as e:
            raise RuntimeError(f"Error processing PDF segment: {e}")

    def extract_formulas(self, page_data: Dict[str, any]) -> List[str]:
        """
        Extract LaTeX formulas from processed page data.

        Args:
            page_data: Dictionary containing page processing results

        Returns:
            List of LaTeX formula strings
        """
        return page_data.get('latex_formulas', [])

    def combine_segment_text(self, segment_results: List[Dict[str, any]]) -> str:
        """
        Combine text from multiple pages into a single string.

        Args:
            segment_results: List of page processing results

        Returns:
            Combined text from all pages
        """
        combined_text = []

        for page_data in segment_results:
            if 'error' not in page_data:
                combined_text.append(f"--- Page {page_data['page_number']} ---")
                combined_text.append(page_data.get('raw_text', ''))
                combined_text.append('')

        return '\n'.join(combined_text)


# Global instance (singleton pattern)
_processor_instance = None


def get_pix2text_processor() -> Pix2TextProcessor:
    """
    Get the global Pix2Text processor instance (singleton).

    Returns:
        Pix2TextProcessor instance
    """
    global _processor_instance

    if _processor_instance is None:
        _processor_instance = Pix2TextProcessor()

    return _processor_instance
