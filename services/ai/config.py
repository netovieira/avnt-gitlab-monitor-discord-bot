from enum import Enum
from dataclasses import dataclass
from typing import Set, Optional

class ResponseMode(Enum):
    STREAM = "stream"
    COMPLETE = "complete"
    CHUNKS = "chunks"

class ChunkMode(Enum):
    BY_SENTENCES = "sentences"
    BY_CHARACTERS = "characters"
    BY_PARAGRAPHS = "paragraphs"
    SMART = "smart"

@dataclass
class SmartChunkConfig:
    markdown_pairs: Set[tuple] = None
    code_blocks: bool = True
    list_items: bool = True
    table_rows: bool = True
    
    def __post_init__(self):
        if self.markdown_pairs is None:
            self.markdown_pairs = {
                ('**', '**'),
                ('*', '*'),
                ('`', '`'),
                ('```', '```'),
                ('---', '---'),
                ('|', '|'),
            }

@dataclass
class AIServiceConfig:
    response_mode: ResponseMode = ResponseMode.COMPLETE
    chunk_mode: ChunkMode = ChunkMode.SMART
    chunk_size: int = 1500
    min_chunk_size: int = 50
    max_chunk_size: int = 2000
    stream_delay: float = 0.1
    typing_simulation: bool = True
    clear_after_response: bool = False
    smart_chunk_config: Optional[SmartChunkConfig] = None