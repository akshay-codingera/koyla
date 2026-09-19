from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field

@dataclass
class FieldCandidate:
    field_name: str
    field_category: str  # 'IDENTIFICATION', 'GEOLOGY', 'MINING'
    data_type: str       # 'STRING', 'NUMBER', 'DATE'
    raw_value: str
    normalized_value: Optional[str] = None
    numeric_value: Optional[float] = None
    unit: Optional[str] = None
    page_number: Optional[int] = None
    table_id: Optional[str] = None
    row_id: Optional[str] = None
    chunk_id: Optional[str] = None
    source_text: Optional[str] = None
    extraction_method: str = "RULE_BASED"
    confidence_score: float = 1.0
    confidence_level: str = "HIGH"  # 'HIGH' >= 0.85, 'MEDIUM' 0.60-0.84, 'LOW' < 0.60
    metadata: Dict[str, Any] = field(default_factory=dict)

class BaseExtractionProvider(ABC):
    @abstractmethod
    def extract(
        self,
        chunks: List[Any],
        tables: List[Any],
        pages: List[Any]
    ) -> List[FieldCandidate]:
        """Extract domain field candidates from document chunks, tables, and pages."""
        pass
