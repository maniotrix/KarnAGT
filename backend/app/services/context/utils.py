import tiktoken
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
from app.logging.logger import get_logger

logger = get_logger(__name__)

@dataclass
class TokenUsage:
    """Represents token usage statistics"""
    input_tokens: int
    output_tokens_reserved: int
    total_tokens: int
    available_tokens: int
    context_limit: int

class TokenizerManager:
    """Manages tiktoken encoders for different models"""
    
    _encoders = {}
    
    @classmethod
    def get_encoder(cls, model: str) -> tiktoken.Encoding:
        """Get or create a tiktoken encoder for the specified model"""
        if model not in cls._encoders:
            try:
                # Handle different model naming conventions
                if model.startswith("gpt-4"):
                    encoding_name = "cl100k_base"
                elif model.startswith("gpt-3.5"):
                    encoding_name = "cl100k_base"
                elif model.startswith("text-"):
                    encoding_name = "p50k_base"
                else:
                    # Default to cl100k_base for newer models
                    encoding_name = "cl100k_base"
                
                cls._encoders[model] = tiktoken.get_encoding(encoding_name)
                logger.debug(f"Created tiktoken encoder for model: {model} using {encoding_name}")
            except Exception as e:
                logger.warning(f"Failed to get specific encoder for {model}, using default: {e}")
                cls._encoders[model] = tiktoken.get_encoding("cl100k_base")
        
        return cls._encoders[model]

def count_tokens(text: str, model: str = "gpt-4o-mini-2024-07-18") -> int:
    """
    Count the number of tokens in a text string for a specific model.
    
    Args:
        text: The text to count tokens for
        model: The model to use for tokenization
        
    Returns:
        int: Number of tokens
    """
    if not text:
        return 0
    
    try:
        encoder = TokenizerManager.get_encoder(model)
        return len(encoder.encode(text))
    except Exception as e:
        logger.error(f"Error counting tokens: {e}")
        # Fallback to rough estimation
        return len(text) // 4
