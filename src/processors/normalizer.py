import re
from typing import List
from src.domain.interfaces import TextNormalizer
from src.utils.logger import get_logger

logger = get_logger(__name__)


class TextNormalizer(TextNormalizer):
    def normalize(self, text: str) -> str:
        if not text:
            return text
        
        # Trim leading/trailing spaces
        text = text.strip()
        
        # Collapse multiple spaces into single space
        text = re.sub(r'\s+', ' ', text)
        
        # Normalize line endings
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        
        # Remove trailing punctuation (.,;:!?)
        text = re.sub(r'[.,;:!?]+$', '', text)
        
        # Remove trailing dashes
        text = re.sub(r'-+$', '', text)
        
        return text.strip()
    
    def normalize_list(self, items: List[str]) -> List[str]:
        return [self.normalize(item) for item in items if item and item.strip()]
