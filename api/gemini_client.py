"""
SecureCodeAI - Gemini Cloud Client
Wrapper for Google Gemini API to enable cloud-based inference.
"""

import asyncio
import os
import logging
from typing import Optional, Dict, Any, Tuple, Callable

from .config import config

logger = logging.getLogger(__name__)

class GeminiClientError(Exception):
    """Exception raised when Gemini inference fails."""
    pass

class GeminiClient:
    """
    Client wrapper for Google Gemini API.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Gemini client.
        
        Args:
            api_key: Google API Key (defaults to config)
        """
        self.api_key = "AIzaSyBM1PQ7DpoZuVr0ShVBdDyaRcaPW3RU99U"
        self.model_name = "gemini-flash-latest" # Fast and capable default
        self.model = None
        self._initialized = False
        
        # Sampling params
        self.temperature = 0.2
        self.max_tokens = 2048
        self.top_p = 0.95
        
    def initialize(self) -> None:
        """
        Initialize Gemini API client.
        """
        if self._initialized:
            return
            
        if not self.api_key:
            raise GeminiClientError("Gemini API Key is missing. Set SECUREAI_GEMINI_API_KEY environment variable.")
            
        try:
            import google.generativeai as genai
            
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(self.model_name)
            
            self._initialized = True
            logger.info(f"Gemini client initialized with model: {self.model_name}")
            
        except ImportError:
            raise GeminiClientError("google-generativeai not installed. Please pip install google-generativeai")
        except Exception as e:
            raise GeminiClientError(f"Failed to initialize Gemini: {e}")

    def update_params(self, temperature: Optional[float] = None, max_tokens: Optional[int] = None) -> None:
        """Update sampling parameters."""
        if temperature is not None:
            self.temperature = temperature
        if max_tokens is not None:
            self.max_tokens = max_tokens

    def generate(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> str:
        """Generate text from prompt."""
        if not self._initialized:
            self.initialize()
            
        try:
            logger.info("Gemini: Generating content...")
            import google.generativeai as genai
            
            # Use provided params or defaults
            temp = temperature if temperature is not None else self.temperature
            tokens = max_tokens if max_tokens is not None else self.max_tokens
            
            generation_config = genai.types.GenerationConfig(
                temperature=temp,
                max_output_tokens=tokens,
                top_p=self.top_p,
            )
            
            response = self.model.generate_content(
                prompt,
                generation_config=generation_config
            )
            
            if response.text:
                return response.text
            else:
                return ""
                
        except Exception as e:
            raise GeminiClientError(f"Gemini generation failed: {e}")

    async def generate_async(self, prompt: str) -> str:
        """Asynchronous generation."""
        # For compatibility with agents calling without kwargs, this simple wrapper works
        # but for true parity we rely on the sync generate() which handles kwargs
        # If agents call this with kwargs, we need to update signature, but usually they call standard generate
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.generate, prompt)

    def validate_python_syntax(self, code: str) -> Tuple[bool, Optional[str]]:
        """Validate Python code syntax."""
        import ast
        try:
            ast.parse(code)
            return (True, None)
        except SyntaxError as e:
            error_msg = f"Syntax error at line {e.lineno}: {e.msg}"
            return (False, error_msg)
        except Exception as e:
            error_msg = f"Parse error: {str(e)}"
            return (False, error_msg)

    def generate_with_self_correction(
        self,
        prompt_builder: Callable[[Optional[str]], str],
        validator: Callable[[str], Tuple[bool, Optional[str]]],
        max_retries: int = 3,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> Optional[str]:
        """Generate with self-correction (copied from LLMClient)."""
        error_feedback = None
        
        for attempt in range(max_retries):
            try:
                prompt = prompt_builder(error_feedback)
                output = self.generate(prompt, max_tokens=max_tokens, temperature=temperature)
                is_valid, error_message = validator(output)
                
                if is_valid:
                    if attempt > 0:
                        logger.info(f"Self-correction succeeded after {attempt + 1} attempts")
                    return output
                else:
                    error_feedback = error_message
                    logger.warning(f"Self-correction attempt {attempt + 1}/{max_retries} failed: {error_message}")
            
            except Exception as e:
                error_feedback = f"Generation error: {str(e)}"
                logger.error(f"Self-correction attempt {attempt + 1}/{max_retries} error: {e}")
        
        return None
