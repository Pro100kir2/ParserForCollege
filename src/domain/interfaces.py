from abc import ABC, abstractmethod
from typing import List
from src.domain.models import Document, SectionType, ParseResult, ExportConfig


class DocumentReader(ABC):
    @abstractmethod
    def read(self, file_path: str) -> Document:
        pass

    @abstractmethod
    def supports_format(self, file_path: str) -> bool:
        pass


class SectionExtractor(ABC):
    @abstractmethod
    def extract_sections(self, document: Document) -> Document:
        pass

    @abstractmethod
    def get_section_aliases(self) -> dict[SectionType, List[str]]:
        pass


class TextNormalizer(ABC):
    @abstractmethod
    def normalize(self, text: str) -> str:
        pass


class Deduplicator(ABC):
    @abstractmethod
    def deduplicate(self, items: List[str]) -> List[str]:
        pass


class Exporter(ABC):
    @abstractmethod
    def export(self, result: ParseResult, config: ExportConfig) -> List[str]:
        pass
