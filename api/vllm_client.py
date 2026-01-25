"""
SecureCodeAI - vLLM Client Wrapper
Wrapper for vLLM inference engine with retry logic and async support.
"""

import asyncio
from typing import Optional, Dict, Any
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

from .config import config


class VLLMInferenceError(Exception):
    """Exception raised when vLLM inference fails."""
    pass


class VLLMClient:
    """
    vLLM client wrapper for LLM inference.
    
    Provides synchronous and asynchronous inference with automatic retry logic.
    """
    
    def __init__(
        self,
        model_path: Optional[str] = None,
        quantization: Optional[str] = None,
        gpu_memory_utilization: Optional[float] = None,
        tensor_parallel_size: Optional[int] = None,
        enable_gpu: Optional[bool] = None
    ):
        """
        Initialize vLLM client.
        
        Args:
            model_path: Path to model weights (defaults to config)
            quantization: Quantization method (awq, gptq, none)
            gpu_memory_utilization: GPU memory utilization (0.1 to 1.0)
            tensor_parallel_size: Number of GPUs for tensor parallelism
            enable_gpu: Enable GPU acceleration
        """
        self.model_path = model_path or config.model_path
        self.quantization = quantization or config.model_quantization
        self.gpu_memory_utilization = gpu_memory_utilization or config.gpu_memory_utilization
        self.tensor_parallel_size = tensor_parallel_size or config.tensor_parallel_size
        self.enable_gpu = enable_gpu if enable_gpu is not None else config.enable_gpu
        
        self.llm = None
        self.sampling_params = None
        self._initialized = False
    
    def initialize(self) -> None:
        """
        Initialize vLLM engine and sampling parameters.
        
        Raises:
            VLLMInferenceError: If initialization fails
        """
        if self._initialized:
            return
        
        try:
            # Import vLLM here to avoid import errors if not installed
            from vllm import LLM, SamplingParams
            
            # Initialize LLM
            self.llm = LLM(
                model=self.model_path,
                quantization=self.quantization if self.quantization != "none" else None,
                gpu_memory_utilization=self.gpu_memory_utilization,
                tensor_parallel_size=self.tensor_parallel_size,
                trust_remote_code=True,
                dtype="auto",
                device="cuda" if self.enable_gpu else "cpu"
            )
            
            # Configure sampling parameters
            self.sampling_params = SamplingParams(
                temperature=0.2,
                top_p=0.95,
                max_tokens=2048,
                stop=None
            )
            
            self._initialized = True
            
        except ImportError as e:
            raise VLLMInferenceError(f"vLLM not installed: {e}")
        except Exception as e:
            raise VLLMInferenceError(f"Failed to initialize vLLM: {e}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=8),
        retry=retry_if_exception_type(VLLMInferenceError),
        reraise=True
    )
    def generate(self, prompt: str) -> str:
        """
        Generate text from prompt with retry logic.
        
        Args:
            prompt: Input prompt for generation
            
        Returns:
            Generated text
            
        Raises:
            VLLMInferenceError: If generation fails after retries
        """
        if not self._initialized:
            self.initialize()
        
        try:
            # Generate with vLLM
            outputs = self.llm.generate([prompt], self.sampling_params)
            
            if not outputs or len(outputs) == 0:
                raise VLLMInferenceError("No output generated")
            
            # Extract generated text
            generated_text = outputs[0].outputs[0].text
            
            return generated_text
            
        except VLLMInferenceError:
            raise
        except Exception as e:
            raise VLLMInferenceError(f"Generation failed: {e}")
    
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
    
    def is_initialized(self) -> bool:
        """Check if vLLM engine is initialized."""
        return self._initialized
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get model configuration information.
        
        Returns:
            Dictionary with model configuration
        """
        return {
            "model_path": self.model_path,
            "quantization": self.quantization,
            "gpu_memory_utilization": self.gpu_memory_utilization,
            "tensor_parallel_size": self.tensor_parallel_size,
            "enable_gpu": self.enable_gpu,
            "initialized": self._initialized
        }
    
    def cleanup(self) -> None:
        """Cleanup vLLM resources."""
        if self.llm is not None:
            # vLLM cleanup
            del self.llm
            self.llm = None
        
        self._initialized = False


# Global vLLM client instance
_vllm_client: Optional[VLLMClient] = None


def get_vllm_client() -> VLLMClient:
    """
    Get or create global vLLM client instance.
    
    Returns:
        Global VLLMClient instance
    """
    global _vllm_client
    
    if _vllm_client is None:
        _vllm_client = VLLMClient()
    
    return _vllm_client


def initialize_vllm() -> VLLMClient:
    """
    Initialize global vLLM client.
    
    Returns:
        Initialized VLLMClient instance
        
    Raises:
        VLLMInferenceError: If initialization fails
    """
    client = get_vllm_client()
    client.initialize()
    return client
