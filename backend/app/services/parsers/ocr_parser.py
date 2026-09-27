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

    def _classify_image(self, filename: str, ocr_text: str) -> Tuple[Optional[str], Optional[str], str, float]:
        """
        Classifies direct image using filename and OCR text against the 14-class taxonomy.
        """
        from app.services.parsers.visual_detector import CLASSIFICATION_RULES, FIGURE_NUMBER_PATTERNS
        combined_text = f"{Path(filename).stem} {ocr_text}"
        
        figure_number = None
        for pattern in FIGURE_NUMBER_PATTERNS:
            m = pattern.search(combined_text)
            if m:
                figure_number = m.group(0).strip()
                break

        type_scores = {}
        for pattern, vtype, base_conf in CLASSIFICATION_RULES:
            if pattern.search(combined_text):
                current = type_scores.get(vtype, 0.0)
                type_scores[vtype] = min(1.0, current + base_conf * 0.6)

        if type_scores:
            best_type = max(type_scores, key=type_scores.get)
            best_conf = min(0.95, type_scores[best_type] + 0.15)
            caption = f"{best_type.replace('_', ' ').title()}: {Path(filename).name}"
            return figure_number, caption, best_type, best_conf
        
        # Default fallback
        fn_lower = filename.lower()
        if any(x in fn_lower for x in ["photo", "pic", "img"]):
            return figure_number, f"Photograph: {Path(filename).name}", "PHOTOGRAPH", 0.6
        return figure_number, f"Figure: {Path(filename).name}", "UNKNOWN", 0.3

    def parse(self, file_path: str) -> ParsedDocument:
        with open(file_path, "rb") as f:
            raw_bytes = f.read()

        with Image.open(file_path) as img:
            width, height = img.size
            text, conf, success = self.ocr_image(img)
            
            filename = Path(file_path).name
            fig_num, caption, vtype, vconf = self._classify_image(filename, text)

            from app.services.parsers.base import ParsedVisual
            direct_visual = ParsedVisual(
                page_number=1,
                bbox={"x0": 0.0, "y0": 0.0, "x1": float(width), "y1": float(height)},
                image_bytes=raw_bytes,
                width_px=width,
                height_px=height,
                visual_type=vtype,
                classification_confidence=vconf,
                classification_method="direct_image_multimodal",
                extraction_method="direct_upload",
                figure_number=fig_num or f"Direct: {filename}",
                caption=caption,
                metadata={"filename": filename, "format": img.format, "mode": img.mode}
            )

            page = ParsedPage(
                page_number=1,
                text=text or f"[Image Evidence: {filename} - {vtype}]",
                ocr_applied=True,
                confidence=conf,
                width=width,
                height=height,
                visuals=[direct_visual],
                metadata={
                    "format": img.format,
                    "mode": img.mode,
                    "ocr_engine": "tesseract" if success else "unavailable",
                    "visual_type": vtype,
                    "classification_confidence": vconf
                }
            )
            
            return ParsedDocument(
                pages=[page],
                total_pages=1,
                tables=[],
                metadata={"file_path": file_path, "type": "image", "visual_type": vtype},
                ocr_applied=True
            )

ocr_parser = OCRParser()
