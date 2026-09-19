"""
Deterministic text preprocessing engine for topic modeling corpus preparation.
Ensures clean, structure-aware text without modifying original chunk raw_text in database.
"""

import re
from typing import Dict, Any, List
from app.services.topics.domain_vocabulary import (
    COAL_MINING_TERMS,
    STATUTORY_TERMS_PRESERVED,
    DOMAIN_STOPWORDS,
)

PREPROCESSOR_VERSION = "1.0.0"

class TextPreprocessor:
    """
    Deterministic text cleaning pipeline for statutory and mining technical documents.
    """

    def __init__(self):
        self.version = PREPROCESSOR_VERSION
        # Regex for page markers and headers/footers
        self.page_marker_pattern = re.compile(
            r"(?i)\b(?:page|pg\.?)\s*\d+\s*(?:of\s*\d+)?\b|\bpage\s*[-–—]\s*\d+\b"
        )
        # Regex for common repeated administrative header lines
        self.header_noise_pattern = re.compile(
            r"(?i)^(?:confidential|draft|internal use only|for official use only|government of india|ministry of coal)\s*$",
            re.MULTILINE
        )
        # Regex for OCR noise / isolated punctuation clusters
        self.ocr_noise_pattern = re.compile(r"[~^|\\]+|[-_=]{3,}")
        # Regex for excessive whitespace
        self.whitespace_pattern = re.compile(r"\s+")
        # Regex for isolated punctuation
        self.punct_pattern = re.compile(r"(?<=\s)[^\w\s](?=\s)|^[^\w\s]+|[^\w\s]+$")

    def clean_text(self, text: str) -> Dict[str, Any]:
        """
        Clean input text deterministically.
        Returns a dictionary containing cleaned_text, token_count, and metrics.
        """
        if not text or not text.strip():
            return {
                "cleaned_text": "",
                "token_count": 0,
                "original_char_count": len(text or ""),
                "cleaned_char_count": 0,
                "reduction_ratio": 0.0,
                "preprocessor_version": self.version,
            }

        original_char_count = len(text)
        s = text

        # 1. Strip repetitive page numbers and running page markers
        s = self.page_marker_pattern.sub(" ", s)

        # 2. Strip administrative header noise lines
        s = self.header_noise_pattern.sub(" ", s)

        # 3. Strip OCR punctuation clusters and visual divider rules
        s = self.ocr_noise_pattern.sub(" ", s)

        # 4. Normalize quotes, dashes, and special unicode spaces
        s = s.replace("\u2013", "-").replace("\u2014", "-")
        s = s.replace("\u2018", "'").replace("\u2019", "'")
        s = s.replace("\u201c", '"').replace("\u201d", '"')
        s = s.replace("\xa0", " ")

        # 5. Normalize whitespace and newlines to single space
        s = self.whitespace_pattern.sub(" ", s).strip()

        # 6. Token analysis and selective domain stopword filtering
        words = s.split()
        filtered_words: List[str] = []

        for word in words:
            w_lower = word.lower().strip(".,;:()[]{}'")
            # If word is a domain stopword, drop it UNLESS it forms part of a preserved compound term
            if w_lower in DOMAIN_STOPWORDS and w_lower not in STATUTORY_TERMS_PRESERVED:
                continue
            filtered_words.append(word)

        cleaned_str = " ".join(filtered_words)
        cleaned_str = self.whitespace_pattern.sub(" ", cleaned_str).strip()

        cleaned_char_count = len(cleaned_str)
        tokens = cleaned_str.split()
        token_count = len(tokens)
        reduction_ratio = (
            (original_char_count - cleaned_char_count) / original_char_count
            if original_char_count > 0
            else 0.0
        )

        return {
            "cleaned_text": cleaned_str,
            "token_count": token_count,
            "original_char_count": original_char_count,
            "cleaned_char_count": cleaned_char_count,
            "reduction_ratio": round(reduction_ratio, 4),
            "preprocessor_version": self.version,
        }


# Global preprocessor instance
_default_preprocessor = TextPreprocessor()

def preprocess_text(text: str) -> Dict[str, Any]:
    """Functional helper using the singleton preprocessor instance."""
    return _default_preprocessor.clean_text(text)
