import os
import logging
from pathlib import Path
from typing import Optional, Tuple, List
from PIL import Image, ImageEnhance, ImageFilter
from app.services.parsers.base import BaseParser, ParsedDocument, ParsedPage, ParsedTable
from app.core.logging.timing import timed_operation

logger = logging.getLogger(__name__)


class OCRParser(BaseParser):
    def __init__(self):
        self._tesseract_available = None
        self._available_languages = None

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

    def get_available_languages(self, force_refresh: bool = False) -> List[str]:
        """
        Retrieves installed language packs from Tesseract.
        Caches the result on the instance unless force_refresh is True.
        """
        if self._available_languages is not None and not force_refresh:
            return self._available_languages
        try:
            import pytesseract
            langs = pytesseract.get_languages()
            self._available_languages = langs or []
        except Exception as e:
            logger.warning(f"Failed to query available Tesseract languages: {e}")
            self._available_languages = []
        return self._available_languages

    def resolve_ocr_languages(self, requested_langs: Optional[str] = None) -> Tuple[str, bool]:
        """
        Resolves effective Tesseract OCR languages based on configuration and available system data.
        Returns: (effective_lang_str, is_fallback)

        Cases:
        - Case A: Requested languages (e.g. eng+hin) available -> returns ("eng+hin", False)
        - Case B: Hindi (or non-eng) unavailable -> falls back to ("eng", True) with warning
        - Case C: English unavailable -> raises RuntimeError configuration error
        """
        from app.core.config import settings
        requested = requested_langs or getattr(settings, "OCR_LANGUAGES", "eng+hin")
        req_list = [l.strip() for l in requested.split("+") if l.strip()]
        avail = self.get_available_languages()

        # Case C: English requested but unavailable
        if "eng" in req_list and "eng" not in avail:
            raise RuntimeError(
                "OCR configuration error: Tesseract English language data ('eng') is unavailable."
            )

        # Case A: All requested languages available
        if all(l in avail for l in req_list):
            return ("+".join(req_list), False)

        # Case B: Hindi requested but unavailable -> fallback to 'eng'
        if "hin" in req_list and "hin" not in avail:
            logger.warning(
                "Hindi OCR language data ('hin') is unavailable; falling back to English OCR ('eng').",
                extra={
                    "event": "ocr_language_fallback",
                    "requested": requested,
                    "selected": "eng",
                    "available": avail,
                },
            )
            return ("eng", True)

        # General fallback: filter to available
        valid = [l for l in req_list if l in avail]
        if valid:
            return ("+".join(valid), True)

        if "eng" in avail:
            return ("eng", True)

        raise RuntimeError(
            f"OCR configuration error: None of the requested languages ({requested}) are available in Tesseract ({avail})."
        )

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

    def ocr_image(
        self,
        image: Image.Image,
        lang: Optional[str] = None,
        raise_on_error: bool = False,
    ) -> Tuple[str, float, bool]:
        """
        Performs OCR on a PIL Image with bilingual support and graceful fallback.
        Returns: (text, confidence, success)
        """
        with timed_operation(
            logger,
            "ocr_extraction",
            extra={
                "width": getattr(image, "width", 0),
                "height": getattr(image, "height", 0),
            },
        ) as metrics:
            if not self.check_tesseract_available():
                metrics["status"] = "SKIPPED_UNAVAILABLE"
                metrics["success"] = False
                return (
                    "[OCR Notice: Tesseract engine not found on system PATH. OCR processing skipped for this image/scan.]",
                    0.0,
                    False,
                )

            try:
                import pytesseract
                from app.core.config import settings

                selected_lang, is_fallback = self.resolve_ocr_languages(requested_langs=lang)
                effective_requested = lang or getattr(settings, "OCR_LANGUAGES", "eng+hin")
                metrics["requested_lang"] = effective_requested
                metrics["selected_lang"] = selected_lang
                metrics["fallback_occurred"] = is_fallback

                logger.info(
                    f"Executing OCR extraction (lang='{selected_lang}', fallback={is_fallback})",
                    extra={
                        "event": "ocr_extraction_started",
                        "requested_lang": effective_requested,
                        "selected_lang": selected_lang,
                        "fallback_occurred": is_fallback,
                    },
                )

                preprocessed = self.preprocess_image(image)
                data = pytesseract.image_to_data(
                    preprocessed,
                    lang=selected_lang,
                    output_type=pytesseract.Output.DICT,
                )

                # Calculate average confidence for valid words
                confidences = [
                    int(c)
                    for c in data.get("conf", [])
                    if str(c).isdigit() and int(c) >= 0
                ]
                avg_conf = (
                    (sum(confidences) / len(confidences)) / 100.0
                    if confidences
                    else 0.85
                )

                text = pytesseract.image_to_string(preprocessed, lang=selected_lang).strip()
                metrics["engine"] = "tesseract"
                metrics["confidence"] = round(avg_conf, 4)
                metrics["text_length"] = len(text)
                metrics["success"] = True
                return text, avg_conf, True
            except Exception as e:
                metrics["error"] = str(e)
                metrics["success"] = False
                logger.error(
                    f"Error during OCR extraction: {e}",
                    exc_info=True,
                    extra={"event": "ocr_extraction_error", "error": str(e)},
                )
                if raise_on_error:
                    raise
                return f"[OCR Error: {str(e)}]", 0.0, False

    def _classify_image(
        self, filename: str, ocr_text: str
    ) -> Tuple[Optional[str], Optional[str], str, float]:
        """
        Classifies direct image using filename and OCR text against the 14-class taxonomy.
        """
        from app.services.parsers.visual_detector import (
            CLASSIFICATION_RULES,
            FIGURE_NUMBER_PATTERNS,
        )

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
            selected_lang, is_fallback = self.resolve_ocr_languages()
            text, conf, success = self.ocr_image(img, lang=selected_lang)

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
                metadata={"filename": filename, "format": img.format, "mode": img.mode},
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
                    "ocr_language": selected_lang if success else None,
                    "ocr_fallback": is_fallback if success else False,
                    "visual_type": vtype,
                    "classification_confidence": vconf,
                },
            )

            return ParsedDocument(
                pages=[page],
                total_pages=1,
                tables=[],
                metadata={
                    "file_path": file_path,
                    "type": "image",
                    "visual_type": vtype,
                    "ocr_language": selected_lang,
                },
                ocr_applied=True,
            )


ocr_parser = OCRParser()
