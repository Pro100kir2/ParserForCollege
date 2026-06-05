from typing import List, Set
from src.domain.interfaces import Deduplicator
from src.processors.normalizer import TextNormalizer
from src.utils.logger import get_logger

logger = get_logger(__name__)


class Deduplicator(Deduplicator):
    def __init__(self):
        self.normalizer = TextNormalizer()
    
    def deduplicate(self, items: List[str]) -> List[str]:
        if not items:
            return []
        
        # Normalize all items for comparison
        normalized_items = [self.normalizer.normalize(item) for item in items]
        
        # Track seen items (case-insensitive)
        seen: Set[str] = set()
        unique_items = []
        
        for original, normalized in zip(items, normalized_items):
            normalized_lower = normalized.lower()
            if normalized_lower not in seen:
                seen.add(normalized_lower)
                unique_items.append(original)
        
        removed_count = len(items) - len(unique_items)
        if removed_count > 0:
            logger.info(f"Removed {removed_count} duplicate items")
        
        return unique_items
    
    def deduplicate_multiple(self, *item_lists: List[str]) -> List[List[str]]:
        return [self.deduplicate(items) for items in item_lists]
    
    def fuzzy_deduplicate(self, items: List[str], threshold: int = 85) -> List[str]:
        """Fuzzy deduplication using RapidFuzz"""
        try:
            from rapidfuzz import process, fuzz
            
            if not items:
                return []
            
            unique_items = []
            seen_signatures = set()
            
            for item in items:
                # Create a signature for fuzzy matching
                normalized = self.normalizer.normalize(item)
                signature = normalized.lower().replace(" ", "")
                
                # Check for similar items
                if seen_signatures:
                    match = process.extractOne(
                        signature,
                        list(seen_signatures),
                        scorer=fuzz.ratio,
                        score_cutoff=threshold
                    )
                    
                    if match:
                        # Similar item found, skip
                        continue
                
                seen_signatures.add(signature)
                unique_items.append(item)
            
            removed_count = len(items) - len(unique_items)
            if removed_count > 0:
                logger.info(f"Fuzzy deduplication removed {removed_count} similar items")
            
            return unique_items
            
        except ImportError:
            logger.warning("RapidFuzz not installed, falling back to exact deduplication")
            return self.deduplicate(items)
        except Exception as e:
            logger.error(f"Fuzzy deduplication failed: {str(e)}")
            return self.deduplicate(items)
