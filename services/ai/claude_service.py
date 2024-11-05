from playwright.async_api import async_playwright, TimeoutError
from .config import AIServiceConfig, ResponseMode, ChunkMode, SmartChunkConfig
from .response_models import Chunk, CompleteResponse
from .smart_chunker import SmartChunker
import logging
import asyncio
from typing import List, AsyncGenerator, Optional

logger = logging.getLogger('AIService.Claude')

class ClaudeService:
    def __init__(self, config: Optional[AIServiceConfig] = None):
        self.config = config or AIServiceConfig()
        self.browser = None
        self.page = None
        self.is_ready = False
        self.lock = asyncio.Lock()
        self.smart_chunker = SmartChunker(self.config.smart_chunk_config or SmartChunkConfig())
    
    async def initialize(self, **kwargs) -> bool:
        try:
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.launch(headless=kwargs.get('headless', True))
            self.page = await self.browser.new_page()
            
            # Login
            await self._login(
                email=kwargs.get('email'),
                password=kwargs.get('password')
            )
            
            self.is_ready = True
            logger.info(f"Claude service initialized with {self.config.response_mode.value} mode")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Claude service: {e}")
            self.is_ready = False
            return False
    
    async def get_response(self, message: str, project: Optional[str] = None) -> CompleteResponse:
        async with self.lock:
            try:
                if not self.is_ready:
                    return CompleteResponse([], 0, error="Service not initialized")
                    
                # Envia mensagem
                await self.page.get_by_role('textbox').fill(message)
                await self.page.keyboard.press('Enter')
                
                # Coleta resposta completa
                full_response = ""
                async for new_content in self._observe_response():
                    full_response += new_content
                
                # Processa chunks usando o modo apropriado
                if self.config.chunk_mode == ChunkMode.SMART:
                    chunk_texts = self.smart_chunker.chunk_text(
                        full_response,
                        self.config.max_chunk_size
                    )
                else:
                    chunk_texts = self._split_into_chunks(full_response)
                
                # Cria objetos Chunk
                chunks = [
                    Chunk(
                        content=text,
                        index=i,
                        is_last=(i == len(chunk_texts) - 1),
                        metadata={
                            "length": len(text),
                            "chunk_number": i + 1,
                            "total_chunks": len(chunk_texts)
                        }
                    )
                    for i, text in enumerate(chunk_texts)
                ]
                
                return CompleteResponse(
                    chunks=chunks,
                    total_length=len(full_response),
                    metadata={
                        "chunk_count": len(chunks),
                        "response_mode": self.config.response_mode.value,
                        "chunk_mode": self.config.chunk_mode.value
                    }
                )
                
            except Exception as e:
                logger.error(f"Error getting response: {e}")
                return CompleteResponse([], 0, error=str(e))