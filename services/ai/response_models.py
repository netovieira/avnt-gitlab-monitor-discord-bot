from dataclasses import dataclass
from typing import List, Dict, Any, Optional

@dataclass
class Chunk:
    content: str
    index: int
    is_last: bool
    metadata: Dict[str, Any] = None

@dataclass
class CompleteResponse:
    chunks: List[Chunk]
    total_length: int
    metadata: Dict[str, Any] = None
    error: Optional[str] = None