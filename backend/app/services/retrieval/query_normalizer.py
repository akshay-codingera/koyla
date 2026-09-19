import re
from typing import List, Dict, Any, Optional

class NormalizedQuery:
    def __init__(
        self,
        original_query: str,
        clean_query: str,
        entities: List[str],
        metrics: List[str],
        fiscal_years: List[str],
        period_start: Optional[str] = None,
        period_end: Optional[str] = None,
        topics: List[str] = None,
        suggested_filters: Dict[str, Any] = None
    ):
        self.original_query = original_query
        self.clean_query = clean_query
        self.entities = entities
        self.metrics = metrics
        self.fiscal_years = fiscal_years
        self.period_start = period_start
        self.period_end = period_end
        self.topics = topics or []
        self.suggested_filters = suggested_filters or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_query": self.original_query,
            "clean_query": self.clean_query,
            "entities": self.entities,
            "metrics": self.metrics,
            "fiscal_years": self.fiscal_years,
            "period_start": self.period_start,
            "period_end": self.period_end,
            "topics": self.topics,
            "suggested_filters": self.suggested_filters
        }

class QueryNormalizer:
    """
    Deterministic Query Normalization service for mining & geological intelligence.
    Extracts entities (subsidiaries, mines, boreholes, seams), metrics (production, stripping ratio),
    and temporal fiscal periods without fabricating facts.
    """

    KNOWN_SUBSIDIARIES = ["CIL", "CMPDI", "BCCL", "CCL", "ECL", "WCL", "SECL", "MCL", "NCL", "NEC"]
    
    KNOWN_MINES_BLOCKS = [
        "Moonidih", "Rajmahal", "Dipka", "Gevra", "Kusmunda", "Jharia", "Raniganj",
        "Singrauli", "Korba", "Talcher", "Ib Valley", "Wardha", "Pench", "Piprawar",
        "Ashok", "Kalyani", "Bhilai", "North Karanpura", "South Karanpura"
    ]

    METRIC_KEYWORDS = {
        "production": ["production", "output", "tonnage", "extracted", "yield"],
        "stripping ratio": ["stripping ratio", "strip ratio", "sr", "ob to coal"],
        "overburden": ["overburden", "ob removal", "ob excavation"],
        "reserve": ["reserve", "geological reserve", "proved reserve", "indicated reserve"],
        "ash content": ["ash content", "ash percentage", "ash %"],
        "calorific value": ["calorific value", "gcv", "heat value"],
        "thickness": ["thickness", "seam thickness"],
        "safety": ["safety", "accident", "incident", "dgms"],
    }

    TOPIC_KEYWORDS = {
        "drilling": ["drill", "drilling", "borehole", "coring", "strata"],
        "exploration": ["exploration", "survey", "geological survey", "reconnaissance"],
        "environment": ["environment", "forestry", "clearance", "air quality", "water"],
        "dispatch": ["dispatch", "offtake", "rake", "loading"],
    }

    def normalize(self, query: str) -> NormalizedQuery:
        if not query:
            return NormalizedQuery("", "", [], [], [], None, None, [], {})

        original = query.strip()
        entities: List[str] = []
        metrics: List[str] = []
        fiscal_years: List[str] = []
        topics: List[str] = []

        # 1. Extract Fiscal Years: e.g. FY2024-25, FY 2024-25, 2024-25, 2024-2025
        fy_matches = re.findall(r'\b(?:FY\s*[-_]?)?((?:19|20)\d{2}[-/]\d{2,4})\b', original, flags=re.IGNORECASE)
        for m in fy_matches:
            # Canonicalize to FYYYYY-YY
            parts = re.split(r'[-/]', m)
            if len(parts) == 2:
                y1 = parts[0]
                y2 = parts[1][-2:] # take last 2 digits
                canonical_fy = f"FY{y1}-{y2}"
                if canonical_fy not in fiscal_years:
                    fiscal_years.append(canonical_fy)

        period_start = None
        period_end = None
        if len(fiscal_years) >= 2:
            sorted_fys = sorted(fiscal_years)
            period_start = sorted_fys[0]
            period_end = sorted_fys[-1]

        # 2. Extract Entities
        # 2.1 Known Subsidiaries
        for sub in self.KNOWN_SUBSIDIARIES:
            if re.search(r'\b' + re.escape(sub) + r'\b', original, flags=re.IGNORECASE):
                if sub not in entities:
                    entities.append(sub)

        # 2.2 Mine / Block / Colliery / Area patterns
        named_patterns = [
            r'\b(Mine\s+[A-Za-z0-9_\-]+)\b',
            r'\b(Block\s+[A-Za-z0-9_\-]+)\b',
            r'\b(Area\s+[A-Za-z0-9_\-]+)\b',
            r'\b(Colliery\s+[A-Za-z0-9_\-]+)\b',
            r'\b(Seam\s+[A-Za-z0-9_\-IVX]+)\b',
            r'\b(BH[-_\s]*\d+[A-Za-z]?)\b',
            r'\b(Borehole[-_\s]*\d+[A-Za-z]?)\b',
        ]
        for pat in named_patterns:
            matches = re.findall(pat, original, flags=re.IGNORECASE)
            for match in matches:
                clean_match = re.sub(r'\s+', ' ', match).strip()
                if clean_match and clean_match not in entities:
                    entities.append(clean_match)

        # 2.3 Known Mine Names
        for mine in self.KNOWN_MINES_BLOCKS:
            if re.search(r'\b' + re.escape(mine) + r'\b', original, flags=re.IGNORECASE):
                if mine not in entities:
                    entities.append(mine)

        # 3. Extract Metrics
        lower_query = original.lower()
        for metric_name, keywords in self.METRIC_KEYWORDS.items():
            for kw in keywords:
                if re.search(r'\b' + re.escape(kw) + r'\b', lower_query):
                    if metric_name not in metrics:
                        metrics.append(metric_name)
                    break

        # 4. Extract Topics
        for topic_name, keywords in self.TOPIC_KEYWORDS.items():
            for kw in keywords:
                if re.search(r'\b' + re.escape(kw) + r'\b', lower_query):
                    if topic_name not in topics:
                        topics.append(topic_name)
                    break

        # 5. Clean Query for Full-Text Search
        # Strip generic conversational words while keeping meaningful technical and query terms
        clean_text = re.sub(r'^(what\s+was|what\s+is|what\s+are|compare|tell\s+me\s+about|find|search\s+for|show\s+me)\s+', '', original, flags=re.IGNORECASE)
        clean_text = re.sub(r'[^\w\s\-\.\/]', ' ', clean_text)
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()

        suggested_filters: Dict[str, Any] = {}
        if fiscal_years and len(fiscal_years) == 1:
            suggested_filters["fiscal_year"] = fiscal_years[0]
        if period_start and period_end:
            suggested_filters["period_start"] = period_start
            suggested_filters["period_end"] = period_end

        return NormalizedQuery(
            original_query=original,
            clean_query=clean_text or original,
            entities=entities,
            metrics=metrics,
            fiscal_years=fiscal_years,
            period_start=period_start,
            period_end=period_end,
            topics=topics,
            suggested_filters=suggested_filters
        )

query_normalizer = QueryNormalizer()
