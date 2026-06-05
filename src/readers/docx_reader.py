import os
import zipfile
from docx import Document as DocxDocument
from src.readers.base import BaseDocumentReader
from src.domain.models import Document, SectionType, SectionContent
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DocxReader(BaseDocumentReader):
    def supports_format(self, file_path: str) -> bool:
        return file_path.lower().endswith('.docx')

    def _is_valid_docx(self, file_path: str) -> bool:
        """Check if file is a valid DOCX by verifying it's a zip and contains document.xml"""
        try:
            if not zipfile.is_zipfile(file_path):
                logger.warning(f"File is not a valid zip archive: {file_path}")
                return False
            
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                # Check for document.xml in word/ directory
                if 'word/document.xml' not in zip_ref.namelist():
                    logger.warning(f"File does not contain word/document.xml: {file_path}")
                    return False
            
            return True
        except Exception as e:
            logger.error(f"Error validating DOCX file {file_path}: {str(e)}")
            return False

    def read(self, file_path: str) -> Document:
        document = super().read(file_path)
        
        # Validate DOCX file before attempting to read
        if not self._is_valid_docx(file_path):
            error_msg = f"Invalid DOCX file: {file_path}"
            logger.error(error_msg)
            document.parse_errors.append(error_msg)
            return document
        
        try:
            doc = DocxDocument(file_path)
            full_text = []
            
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    full_text.append(paragraph.text)
            
            # Ensure raw_text attribute exists
            if not hasattr(document, 'raw_text'):
                document.raw_text = ""
            
            document.raw_text = "\n".join(full_text)
            logger.info(f"Successfully read DOCX file: {file_path}")
            
        except Exception as e:
            error_msg = f"Failed to read DOCX file {file_path}: {str(e)}"
            logger.error(error_msg)
            document.parse_errors.append(error_msg)
            # Ensure raw_text attribute exists even on error
            if not hasattr(document, 'raw_text'):
                document.raw_text = ""
        
        return document
