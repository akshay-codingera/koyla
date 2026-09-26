from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class ParsedTable(BaseModel):
    page_number: int
    table_index: int
    caption: Optional[str] = None
    headers: List[str] = Field(default_factory=list)
    rows: List[List[Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Logical table continuation metadata
    logical_table_id: Optional[str] = None
    is_continuation: bool = False
    continuation_of_idx: Optional[int] = None
    part_number: int = 1
    total_parts: int = 1
    has_repeated_headers: bool = False
    continuation_confidence: float = 1.0
    continuation_status: str = "STANDALONE"  # STANDALONE, AUTO_MERGED, REVIEW_REQUIRED
    row_pages: List[int] = Field(default_factory=list)

class ParsedVisual(BaseModel):
    """Represents a detected visual element from a document page.

    Coordinate convention: bbox uses PyMuPDF unrotated page coordinates
    {x0, y0, x1, y1} where origin is top-left, units are PDF points (1/72 inch).
    """
    page_number: int
    bbox: Optional[Dict[str, float]] = None  # {x0, y0, x1, y1} in PDF points
    image_bytes: Optional[bytes] = None
    width_px: Optional[int] = None
    height_px: Optional[int] = None
    visual_type: str = "UNKNOWN"
    classification_confidence: float = 0.0
    classification_method: str = "deterministic_heuristic"
    extraction_method: str = "pymupdf_raster"  # pymupdf_raster, pymupdf_vector, composite
    figure_number: Optional[str] = None
    caption: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        arbitrary_types_allowed = True

class ParsedPage(BaseModel):
    page_number: int
    text: str = ""
    ocr_applied: bool = False
    confidence: Optional[float] = 1.0
    width: Optional[int] = None
    height: Optional[int] = None
    tables: List[ParsedTable] = Field(default_factory=list)
    visuals: List[ParsedVisual] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ParsedDocument(BaseModel):
    pages: List[ParsedPage] = Field(default_factory=list)
    total_pages: int = 0
    tables: List[ParsedTable] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    ocr_applied: bool = False

class BaseParser(ABC):
    @abstractmethod
    def can_handle(self, mime_type: str, filename: str) -> bool:
        """Determines if parser can handle the given file."""
        pass

    @abstractmethod
    def parse(self, file_path: str) -> ParsedDocument:
        """Parses the file and returns structured document representation."""
        pass
