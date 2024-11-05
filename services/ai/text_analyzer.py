import re
from nltk.tokenize import sent_tokenize
import logging

from services.ai.config import SmartChunkConfig

logger = logging.getLogger('AIService.TextAnalyzer')

class TextAnalyzer:
    def __init__(self, config: 'SmartChunkConfig'):
        self.config = config
    
    def analyze_text(self, text: str) -> dict:
        return {
            'has_code': self._check_code_blocks(text),
            'has_tables': self._check_tables(text),
            'has_lists': self._check_lists(text),
            'avg_sentence_length': self._calculate_avg_sentence_length(text),
            'markdown_density': self._calculate_markdown_density(text),
            'open_tags': self._find_open_tags(text)
        }
    
    def _check_code_blocks(self, text: str) -> bool:
        return '```' in text or bool(re.search(r'`[^`]+`', text))
    
    def _check_tables(self, text: str) -> bool:
        return '|' in text and '-|-' in text
    
    def _check_lists(self, text: str) -> bool:
        return bool(re.search(r'^\s*[-*+]\s|^\s*\d+\.\s', text, re.MULTILINE))
    
    def _calculate_avg_sentence_length(self, text: str) -> float:
        sentences = sent_tokenize(text)
        return sum(len(s) for s in sentences) / len(sentences) if sentences else 0
    
    def _calculate_markdown_density(self, text: str) -> float:
        markdown_chars = sum(text.count(tag) for pair in self.config.markdown_pairs 
                           for tag in pair)
        return markdown_chars / len(text) if text else 0
    
    def _find_open_tags(self, text: str) -> dict:
        open_tags = {}
        for start_tag, end_tag in self.config.markdown_pairs:
            count_start = text.count(start_tag)
            count_end = text.count(end_tag)
            if count_start > count_end:
                open_tags[start_tag] = count_start - count_end
        return open_tags