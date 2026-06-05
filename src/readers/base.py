from src.domain.interfaces import DocumentReader
from src.domain.models import Document


class BaseDocumentReader(DocumentReader):
    def read(self, file_path: str) -> Document:
        file_name = file_path.split("/")[-1]
        return Document(file_path=file_path, file_name=file_name)
