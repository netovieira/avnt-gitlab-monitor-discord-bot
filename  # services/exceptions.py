class AIServiceException(Exception):
    """Base exception for AI service"""
    pass

class ServiceNotInitializedException(AIServiceException):
    """Raised when trying to use service before initialization"""
    pass

class ChunkingException(AIServiceException):
    """Raised when there's an error during text chunking"""
    pass

class ResponseTimeoutException(AIServiceException):
    """Raised when response takes too long"""
    pass