import re
import hashlib
from typing import List, Optional
from src.domain.interfaces import SectionExtractor
from src.domain.models import Document, SectionType, SectionContent
from src.config.settings import get_settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class SectionExtractor(SectionExtractor):
    def __init__(self):
        self.settings = get_settings()
        self.extractor_version = self.settings.extractor_version
    
    def get_section_aliases(self) -> dict[SectionType, List[str]]:
        return {
            SectionType.MAIN_LITERATURE: self.settings.section_aliases.main_literature,
            SectionType.ADDITIONAL_LITERATURE: self.settings.section_aliases.additional_literature,
            SectionType.MATERIAL_RESOURCES: self.settings.section_aliases.material_resources
        }
    
    def extract_sections(self, document: Document) -> Document:
        if not document.raw_text:
            logger.warning(f"No raw text in document: {document.file_name}")
            return document
        
        # Calculate content hash
        document.content_hash = hashlib.sha256(document.raw_text.encode('utf-8')).hexdigest()
        document.extractor_version = self.extractor_version
        
        aliases = self.get_section_aliases()
        text = document.raw_text
        
        for section_type, section_aliases in aliases.items():
            for alias in section_aliases:
                content = self._extract_section_content(text, alias)
                if content:
                    confidence = self._calculate_confidence(text, alias, content)
                    section_content = SectionContent(
                        section_type=section_type,
                        entries=content,
                        confidence_score=confidence,
                        extractor_version=self.extractor_version
                    )
                    document.sections[section_type] = section_content
                    logger.info(f"Extracted {section_type.value} from {document.file_name} (confidence: {confidence:.2f})")
                    
                    if confidence < self.settings.confidence_threshold:
                        logger.warning(f"Low confidence for {section_type.value} in {document.file_name}: {confidence:.2f}")
                    break
        
        return document
    
    def _calculate_confidence(self, text: str, section_title: str, content: List[str]) -> float:
        """Calculate confidence score for section extraction"""
        if not content:
            return 0.0
        
        # Base score - if we found the section and have content, start high
        base_score = 0.7  # Base confidence for finding any content
        
        # Boost based on content length (more content = higher confidence)
        length_boost = min(len(content) / 10.0, 0.3)
        base_score += length_boost
        
        # Boost if section title is exact match in text
        if section_title.lower() in text.lower():
            base_score += 0.1
        
        # Check if entries look like literature (have typical patterns)
        literature_patterns = 0
        narrative_indicators = 0
        
        for entry in content:
            # Check for typical literature patterns: author names, years, publishers
            if re.search(r'\d{4}', entry):  # Year
                literature_patterns += 1
            if re.search(r'[А-ЯA-Z]\.\s*[А-ЯA-Z]\.', entry):  # Initials
                literature_patterns += 1
            if re.search(r'(издательство|изд-во|пресс|университет)', entry, re.IGNORECASE):
                literature_patterns += 1
            
            # Check for narrative text indicators (common in material resources)
            if re.search(r'(аудитория|помещение|оборудование|компьютер|интернет|доступ)', entry, re.IGNORECASE):
                narrative_indicators += 1
        
        # Boost confidence based on detected patterns
        if literature_patterns > 0:
            pattern_ratio = literature_patterns / len(content)
            base_score += min(pattern_ratio * 0.2, 0.2)
        elif narrative_indicators > 0:
            # For narrative sections (like material resources), use different scoring
            pattern_ratio = narrative_indicators / len(content)
            base_score += min(pattern_ratio * 0.2, 0.2)
        
        return min(base_score, 1.0)
    
    def _extract_section_content(self, text: str, section_title: str) -> Optional[List[str]]:
        pattern = self._build_section_pattern(section_title)
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        
        if not match:
            return None
        
        start_pos = match.end()
        
        # Look for next section header (numbered like "6.2", "6.3", "7.", etc.)
        next_section_pattern = r'\n\s*\d+\.\d+\s+|\n\s*\d+\.\s+'
        next_match = re.search(next_section_pattern, text[start_pos:])
        
        if next_match:
            end_pos = start_pos + next_match.start()
        else:
            end_pos = len(text)
        
        section_text = text[start_pos:end_pos].strip()
        entries = self._parse_entries(section_text)
        
        return entries if entries else None
    
    def _build_section_pattern(self, section_title: str) -> str:
        escaped_title = re.escape(section_title)
        # Allow for optional numbering like "6.3." before the section title
        return rf'(?:^|\n)\s*(?:\d+\.\d+\.\s+)?(?:\d+\.\s+)?{escaped_title}\s*[:\-.]?\s*\n'
    
    def _parse_entries(self, section_text: str) -> List[str]:
        entries = []
        lines = section_text.split('\n')
        
        current_entry = []
        
        for line in lines:
            line = line.strip()
            if not line:
                if current_entry:
                    entry = ' '.join(current_entry).strip()
                    if entry:
                        entries.append(entry)
                    current_entry = []
                continue
            
            # Skip lines that look like section headers (all caps or numbered)
            if re.match(r'^[А-ЯA-Z]{5,}$', line):
                if current_entry:
                    entry = ' '.join(current_entry).strip()
                    if entry:
                        entries.append(entry)
                    current_entry = []
                continue
            
            # Skip lines that are just numbers or numbered section headers
            if re.match(r'^\d+\.\d+\s+', line) or re.match(r'^\d+\.\s+[А-ЯA-Z]', line):
                if current_entry:
                    entry = ' '.join(current_entry).strip()
                    if entry:
                        entries.append(entry)
                    current_entry = []
                continue
            
            # Skip lines that are just numbers
            if re.match(r'^[\d\.\-]+$', line):
                continue
            
            # Check if this line starts a new entry (starts with a pattern like "1.", "2.", or author name)
            # Literature entries often start with author name or number
            if re.match(r'^\d+\.', line) or re.match(r'^[А-ЯA-Z][а-яa-z]+\s+[А-ЯA-Z]\.', line):
                if current_entry:
                    entry = ' '.join(current_entry).strip()
                    if entry:
                        entries.append(entry)
                current_entry = [line]
            else:
                current_entry.append(line)
        
        # Don't forget the last entry
        if current_entry:
            entry = ' '.join(current_entry).strip()
            if entry:
                entries.append(entry)
        
        # If no structured entries found, treat entire text as single entry (for narrative sections)
        if not entries and section_text.strip():
            # Split by common punctuation for narrative text
            sentences = re.split(r'[;:]\s*', section_text.strip())
            entries = [s.strip() for s in sentences if s.strip()]
        
        return entries
    
    def _is_section_header(self, line: str) -> bool:
        header_indicators = ['литература', 'обеспечение', 'база', 'ресурс']
        line_lower = line.lower()
        return any(indicator in line_lower for indicator in header_indicators)
