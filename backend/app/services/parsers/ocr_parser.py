import os
from pathlib import Path
from typing import Optional, Tuple
from PIL import Image, ImageEnhance, ImageFilter
from app.services.parsers.base import BaseParser, ParsedDocument, ParsedPage, ParsedTable

class OCRParser(BaseParser):
    def __init__(self):
        self._tesseract_available = None

    def check_tesseract_available(self) -> bool:
        if self._tesseract_available is not None:
            return self._tesseract_available
        try:
            import pytesseract
            pytesseract.get_tesseract_version()
            self._tesseract_available = True
        except Exception:
            self._tesseract_available = False
        return self._tesseract_available

    def can_handle(self, mime_type: str, filename: str) -> bool:
        ext = Path(filename).suffix.lower()
        return ext in [".jpg", ".jpeg", ".png"] or mime_type.startswith("image/")

    def preprocess_image(self, image: Image.Image) -> Image.Image:
        """
        Preprocesses image for OCR: grayscale and contrast enhancement.
        """
        # Convert to grayscale
        gray = image.convert("L")
        # Enhance contrast
        enhancer = ImageEnhance.Contrast(gray)
        enhanced = enhancer.enhance(1.8)
        return enhanced

    def ocr_image(self, image: Image.Image) -> Tuple[str, float, bool]:
        """
        Performs OCR on a PIL Image.
        Returns: (text, confidence, success)
        """
        if not self.check_tesseract_available():
            return (
                "[OCR Notice: Tesseract engine not found on system PATH. OCR processing skipped for this image/scan.]",
                0.0,
                False
            )
        
        try:
            import pytesseract
            preprocessed = self.preprocess_image(image)
            data = pytesseract.image_to_data(preprocessed, output_type=pytesseract.Output.DICT)
            
            # Calculate average confidence for valid words
            confidences = [int(c) for c in data.get("conf", []) if str(c).isdigit() and int(c) >= 0]
            avg_conf = (sum(confidences) / len(confidences)) / 100.0 if confidences else 0.85
            
            text = pytesseract.image_to_string(preprocessed).strip()
            return text, avg_conf, True
        except Exception as e:
            return f"[OCR Error: {str(e)}]", 0.0, False

    def parse(self, file_path: str) -> ParsedDocument:
        with Image.open(file_path) as img:
            width, height = img.size
            text, conf, success = self.ocr_image(img)
            
            page = ParsedPage(
                page_number=1,
                text=text,
                ocr_applied=True,
                confidence=conf,
                width=width,
                height=height,
                metadata={
                    "format": img.format,
                    "mode": img.mode,
                    "ocr_engine": "tesseract" if success else "unavailable"
                }
            )
            
            return ParsedDocument(
                pages=[page],
                total_pages=1,
                tables=[],
                metadata={"file_path": file_path, "type": "image"},
                ocr_applied=True
            )

ocr_parser = OCRParser()
