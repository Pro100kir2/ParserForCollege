from typing import List, Optional
from src.domain.interfaces import DocumentReader
from src.readers.docx_reader import DocxReader
from src.readers.doc_reader import DocReader
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ReaderFactory:
    _readers: List[DocumentReader] = [
        DocxReader(),
        DocReader()
    ]
    
    @classmethod
    def get_reader(cls, file_path: str) -> Optional[DocumentReader]:
        for reader in cls._readers:
            if reader.supports_format(file_path):
                logger.debug(f"Selected reader for {file_path}: {reader.__class__.__name__}")
                return reader
        logger.warning(f"No reader found for file: {file_path}")
        return None
    
    @classmethod
    def register_reader(cls, reader: DocumentReader):
        cls._readers.append(reader)
        logger.info(f"Registered reader: {reader.__class__.__name__}")
