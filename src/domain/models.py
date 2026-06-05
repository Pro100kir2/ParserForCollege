from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class SectionType(Enum):
    MAIN_LITERATURE = "main_literature"
    ADDITIONAL_LITERATURE = "additional_literature"
    MATERIAL_RESOURCES = "material_resources"


@dataclass
class SectionContent:
    section_type: SectionType
    entries: List[str] = field(default_factory=list)
    raw_text: Optional[str] = None
    confidence_score: float = 1.0
    extractor_version: str = "1.0.0"


@dataclass
class Document:
    file_path: str
    file_name: str
    sections: dict[SectionType, SectionContent] = field(default_factory=dict)
    parse_errors: List[str] = field(default_factory=list)
    content_hash: Optional[str] = None
    extractor_version: str = "1.0.0"


@dataclass
class ParseResult:
    main_literature: List[str] = field(default_factory=list)
    additional_literature: List[str] = field(default_factory=list)
    material_resources: List[str] = field(default_factory=list)
    processed_files: int = 0
    failed_files: int = 0
    failed_file_list: List[str] = field(default_factory=list)
    low_confidence_files: List[str] = field(default_factory=list)
    extractor_version: str = "1.0.0"


@dataclass
class ExportConfig:
    single_workbook: bool = True
    output_dir: str = "./output"
    filename_main: str = "main_literature.docx"
    filename_additional: str = "additional_literature.docx"
    filename_material: str = "material_resources.docx"
    combined_filename: str = "rpd_consolidated.docx"
    extractor_version: str = "1.0.0"
    confidence_threshold: float = 0.7
