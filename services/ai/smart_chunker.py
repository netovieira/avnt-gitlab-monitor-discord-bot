import re
from typing import List
import logging

from services.ai.text_analyzer import TextAnalyzer
from .config import SmartChunkConfig

logger = logging.getLogger('AIService.SmartChunker')

class SmartChunker:
    def __init__(self, config: SmartChunkConfig):
        self.config = config
        self.analyzer = TextAnalyzer(config)
    
    def chunk_text(self, text: str, max_size: int) -> List[str]:
        analysis = self.analyzer.analyze_text(text)
        
        if analysis['has_code']:
            chunks = self._split_respecting_code(text, max_size)
        elif analysis['has_tables']:
            chunks = self._split_respecting_tables(text, max_size)
        elif analysis['has_lists']:
            chunks = self._split_respecting_lists(text, max_size)
        else:
            chunks = self._split_by_natural_breaks(text, max_size)
            
        # Otimiza os chunks resultantes
        return self._optimize_chunks(chunks, max_size)
    
    def _split_respecting_code(self, text: str, max_size: int) -> List[str]:
        chunks = []
        current_chunk = ""
        in_code_block = False
        
        for line in text.split('\n'):
            if line.startswith('```'):
                in_code_block = not in_code_block
                
            new_chunk = current_chunk + ('\n' if current_chunk else '') + line
            
            if len(new_chunk) > max_size and not in_code_block:
                chunks.append(current_chunk)
                current_chunk = line
            else:
                current_chunk = new_chunk
        
        if current_chunk:
            chunks.append(current_chunk)
            
        return chunks
    
    def _split_respecting_tables(self, text: str, max_size: int) -> List[str]:
        chunks = []
        current_chunk = ""
        in_table = False
        
        for line in text.split('\n'):
            if '|' in line:
                in_table = True
            elif in_table and not line.strip():
                in_table = False
                
            if len(current_chunk) + len(line) + 1 > max_size and not in_table:
                chunks.append(current_chunk)
                current_chunk = line
            else:
                current_chunk += ('\n' if current_chunk else '') + line
        
        if current_chunk:
            chunks.append(current_chunk)
            
        return chunks
    
    def _split_respecting_lists(self, text: str, max_size: int) -> List[str]:
        chunks = []
        current_chunk = ""
        in_list = False
        list_indent = 0
        
        for line in text.split('\n'):
            # Detecta início de lista
            list_match = re.match(r'^(\s*)([-*+]|\d+\.)\s', line)
            if list_match:
                in_list = True
                list_indent = len(list_match.group(1))
            # Detecta fim de lista
            elif in_list and (not line.strip() or len(line) - len(line.lstrip()) != list_indent):
                in_list = False
                
            if len(current_chunk) + len(line) + 1 > max_size and not in_list:
                chunks.append(current_chunk)
                current_chunk = line
            else:
                current_chunk += ('\n' if current_chunk else '') + line
        
        if current_chunk:
            chunks.append(current_chunk)
            
        return chunks
    
    def _split_by_natural_breaks(self, text: str, max_size: int) -> List[str]:
        if len(text) <= max_size:
            return [text]
            
        # Tenta parágrafos primeiro
        paragraphs = text.split('\n\n')
        if all(len(p) <= max_size for p in paragraphs):
            return paragraphs
            
        # Depois sentenças
        sentences = sent_tokenize(text)
        if all(len(s) <= max_size for s in sentences):
            return sentences
            
        # Por fim, caracteres
        return [text[i:i+max_size] for i in range(0, len(text), max_size)]
    
    def _optimize_chunks(self, chunks: List[str], max_size: int) -> List[str]:
        """Otimiza os chunks combinando os muito pequenos e garantindo tamanho máximo"""
        optimized = []
        current = ""
        
        for chunk in chunks:
            if len(current) + len(chunk) + 1 <= max_size:
                current += ('\n' if current else '') + chunk
            else:
                if current:
                    optimized.append(current)
                current = chunk
        
        if current:
            optimized.append(current)
            
        return optimized