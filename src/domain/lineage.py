from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime


@dataclass
class LineageRecord:
    """Data lineage information for each extracted entry"""
    value: str
    source_document: str
    source_section: str
    source_page: Optional[int] = None
    extractor_version: str = "1.0.0"
    extraction_timestamp: datetime = field(default_factory=datetime.now)
    confidence_score: float = 1.0
    content_hash: Optional[str] = None


@dataclass
class LineageTracker:
    """Track data lineage for all extracted entries"""
    records: List[LineageRecord] = field(default_factory=list)
    
    def add_record(self, record: LineageRecord):
        """Add a lineage record"""
        self.records.append(record)
    
    def get_lineage_for_value(self, value: str) -> List[LineageRecord]:
        """Get all lineage records for a specific value"""
        return [r for r in self.records if r.value == value]
    
    def get_records_by_document(self, document: str) -> List[LineageRecord]:
        """Get all lineage records from a specific document"""
        return [r for r in self.records if r.source_document == document]
    
    def get_records_by_version(self, version: str) -> List[LineageRecord]:
        """Get all lineage records extracted by a specific version"""
        return [r for r in self.records if r.extractor_version == version]
    
    def export_lineage(self) -> List[dict]:
        """Export lineage records as dictionaries"""
        return [
            {
                "value": r.value,
                "source_document": r.source_document,
                "source_section": r.source_section,
                "source_page": r.source_page,
                "extractor_version": r.extractor_version,
                "extraction_timestamp": r.extraction_timestamp.isoformat(),
                "confidence_score": r.confidence_score,
                "content_hash": r.content_hash
            }
            for r in self.records
        ]
