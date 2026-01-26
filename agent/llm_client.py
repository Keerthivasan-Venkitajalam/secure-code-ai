"""
SecureCodeAI - LLM Client for Agent Intelligence
Provides LLM inference capabilities for Scanner, Speculator, and Patcher agents.
"""

import ast
import asyncio
import logging
from typing import Optional, Tuple, Callable, Any
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)

from api.vllm_client import VLLMClient, VLLMInferenceError
# Optional imports to allow running without vLLM
try:
    from vllm import SamplingParams
except ImportError:
    SamplingParams = None

# Optional imports to allow running without vLLM
try:
    from vllm import SamplingParams
except ImportError:
    SamplingParams = None



logger = logging.getLogger(__name__)


class LLMClient:
    """
    LLM client for agent intelligence operations.
    
    Provides high-level interface for LLM-powered reasoning in agents:
    - Text generation with configurable parameters
    - Python syntax validation
    - Retry logic with exponential backoff
    - Async support for concurrent operations
    """
    
    def __init__(self, vllm_client: VLLMClient):
        """
        Initialize LLM client.
        
        Args:
            vllm_client: Initialized VLLMClient instance
        """
        self.vllm_client = vllm_client
        
        # Default parameters (Requirements 10.1, 10.2)
        self.default_max_tokens = 2048
        self.default_temperature = 0.2
        self.default_top_p = 0.95
        
        # Ensure vLLM client is initialized
        if not self.vllm_client.is_initialized():
            self.vllm_client.initialize()
    
    def generate(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> str:
        """
        Generate text from prompt.
        
        Args:
            prompt: Input prompt for generation
            max_tokens: Maximum tokens to generate (default: 2048)
            temperature: Sampling temperature (default: 0.2)
            
        Returns:
            Generated text
            
        Raises:
            VLLMInferenceError: If generation fails
        """
        # Use defaults if not specified (but allow 0 values)
        if max_tokens is None:
            max_tokens = self.default_max_tokens
        if temperature is None:
            temperature = self.default_temperature
        
        # Update sampling parameters temporarily
        original_params = None
        if hasattr(self.vllm_client, "sampling_params"):
            original_params = self.vllm_client.sampling_params
        
        try:
            # Handle vLLM client
            if hasattr(self.vllm_client, "sampling_params") and SamplingParams is not None:
                # Create new sampling params with specified values
                self.vllm_client.sampling_params = SamplingParams(
                    temperature=temperature,
                    top_p=self.default_top_p,
                    max_tokens=max_tokens,
                    stop=None
                )
            # Handle Local/LlamaCpp client (duck typing)
            elif hasattr(self.vllm_client, "update_params"):
                self.vllm_client.update_params(
                    temperature=temperature,
                    max_tokens=max_tokens
                )

            
            # Generate using vLLM client
            result = self.vllm_client.generate(prompt)
            
            return result
            
        finally:
            # Restore original sampling parameters
            if hasattr(self.vllm_client, "sampling_params") and SamplingParams is not None and original_params is not None:
                self.vllm_client.sampling_params = original_params
    
    async def generate_async(self, prompt: str) -> str:
        """
        Asynchronous wrapper for generate().
        
        Args:
            prompt: Input prompt for generation
            
        Returns:
            Generated text
            
        Raises:
            VLLMInferenceError: If generation fails
        """
        # Run synchronous generate in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.generate, prompt)
    
    def validate_python_syntax(self, code: str) -> Tuple[bool, Optional[str]]:
        """
        Validate Python code syntax using ast.parse().
        
        Args:
            code: Python code to validate
            
        Returns:
            Tuple of (is_valid, error_message)
            - is_valid: True if code is syntactically valid
            - error_message: Error description if invalid, None otherwise
        """
        try:
            ast.parse(code)
            return (True, None)
        except SyntaxError as e:
            error_msg = f"Syntax error at line {e.lineno}: {e.msg}"
            return (False, error_msg)
        except Exception as e:
            error_msg = f"Parse error: {str(e)}"
            return (False, error_msg)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=8),
        retry=retry_if_exception_type(VLLMInferenceError),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True
    )
    def generate_with_retry(
        self,
        prompt: str,
        max_retries: int = 3
    ) -> str:
        """
        Generate text with automatic retry on failures.
        
        Uses exponential backoff: 2s, 4s, 8s between retries.
        
        Args:
            prompt: Input prompt for generation
            max_retries: Maximum number of retry attempts (default: 3)
            
        Returns:
            Generated text
            
        Raises:
            VLLMInferenceError: If generation fails after all retries
        """
        logger.info(f"Generating with retry (max_retries={max_retries})")
        
        try:
            result = self.generate(prompt)
            logger.info("Generation successful")
            return result
        except VLLMInferenceError as e:
            logger.error(f"Generation failed: {e}")
            raise
    
    def get_config(self) -> dict:
        """
        Get current LLM configuration.
        
        Returns:
            Dictionary with configuration parameters
        """
        return {
            "max_tokens": self.default_max_tokens,
            "temperature": self.default_temperature,
            "top_p": self.default_top_p,
            "vllm_initialized": self.vllm_client.is_initialized()
        }
    
    def generate_with_self_correction(
        self,
        prompt_builder: Callable[[Optional[str]], str],
        validator: Callable[[str], Tuple[bool, Optional[str]]],
        max_retries: int = 3,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> Optional[str]:
        """
        Generate text with self-correction loop.
        
        Implements the self-correction pattern:
        1. Generate output using prompt_builder
        2. Validate output using validator
        3. If invalid, retry with error feedback in prompt
        4. Repeat until valid or max_retries exceeded
        
        Args:
            prompt_builder: Function that builds prompt, accepts error_feedback (Optional[str])
            validator: Function that validates output, returns (is_valid, error_message)
            max_retries: Maximum number of retry attempts (default: 3)
            max_tokens: Maximum tokens to generate (default: 2048)
            temperature: Sampling temperature (default: 0.2)
            
        Returns:
            Valid generated output, or None if max retries exceeded
            
        Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5
        """
        error_feedback = None
        
        for attempt in range(max_retries):
            try:
                # Build prompt with error feedback from previous attempt
                prompt = prompt_builder(error_feedback)
                
                # Generate output
                output = self.generate(prompt, max_tokens=max_tokens, temperature=temperature)
                
                # Validate output
                is_valid, error_message = validator(output)
                
                if is_valid:
                    # Success!
                    if attempt > 0:
                        logger.info(f"Self-correction succeeded after {attempt + 1} attempts")
                    return output
                else:
                    # Validation failed, prepare error feedback for next attempt
                    error_feedback = error_message
                    logger.warning(
                        f"Self-correction attempt {attempt + 1}/{max_retries} failed: {error_message}"
                    )
                    
                    # If this was the last attempt, log failure
                    if attempt == max_retries - 1:
                        logger.error(
                            f"Self-correction failed after {max_retries} attempts. "
                            f"Last error: {error_message}"
                        )
            
            except Exception as e:
                # Generation error
                error_feedback = f"Generation error: {str(e)}"
                logger.error(f"Self-correction attempt {attempt + 1}/{max_retries} error: {e}")
                
                # If this was the last attempt, log failure
                if attempt == max_retries - 1:
                    logger.error(f"Self-correction failed after {max_retries} attempts due to errors")
        
        # All retries exhausted
        return None
