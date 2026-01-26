"""
SecureCodeAI - Local LLM Client (GGUF)
Wrapper for llama-cpp-python or ctransformers to enable offline inference on Windows.
"""

import asyncio
import os
from typing import Optional, Dict, Any
import logging

from .config import config

logger = logging.getLogger(__name__)

class LocalLLMError(Exception):
    """Exception raised when local LLM inference fails."""
    pass

class LlamaCppClient:
    """
    Local GGUF-based client wrapper for LLM inference.
    Supports llama-cpp-python (preferred) and ctransformers (fallback).
    """
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize Local LLM client.
        
        Args:
            model_path: Path to GGUF model file
        """
        self.model_path = model_path or config.model_path
        self.llm = None
        self._initialized = False
        self._backend = None # 'llama_cpp' or 'ctransformers'
        
        # Sampling params
        self.temperature = 0.2
        self.max_tokens = 2048
        self.top_p = 0.95
        
    def initialize(self) -> None:
        """
        Initialize local LLM engine.
        """
        if self._initialized:
            return
            
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Model file not found at {self.model_path}")
            
        # Try llama-cpp-python first
        try:
            from llama_cpp import Llama
            logger.info(f"Loading local GGUF model (llama-cpp) from {self.model_path}...")
            
            self.llm = Llama(
                model_path=self.model_path,
                n_ctx=4096,
                n_gpu_layers=-1 if config.enable_gpu else 0,
                verbose=False
            )
            self._backend = 'llama_cpp'
            self._initialized = True
            logger.info("Local GGUF model loaded successfully (llama-cpp)")
            return
        except ImportError:
            logger.info("llama-cpp-python not found, trying ctransformers...")
        except Exception as e:
            logger.warning(f"Failed to load with llama-cpp: {e}")

        # Fallback to ctransformers
        try:
            from ctransformers import AutoModelForCausalLM
            logger.info(f"Loading local GGUF model (ctransformers) from {self.model_path}...")
            
            # Detect model type from filename or path, default to 'deepseek' or 'llama'
            model_type = "deepseek2" if "deepseek" in self.model_path.lower() else "llama"
            
            # Prepare model parameters
            model_params = {
                "model_path": os.path.abspath(self.model_path),
                "model_type": model_type,
                "context_length": 4096
            }
            
            if config.enable_gpu:
                model_params["gpu_layers"] = 50
                
            self.llm = AutoModelForCausalLM.from_pretrained(**model_params)
            self._backend = 'ctransformers'
            self._initialized = True
            logger.info("Local GGUF model loaded successfully (ctransformers)")
            return
        except ImportError:
            raise LocalLLMError("Neither llama-cpp-python nor ctransformers installed.")
        except Exception as e:
            raise LocalLLMError(f"Failed to initialize local model: {e}")

    def update_params(self, temperature: Optional[float] = None, max_tokens: Optional[int] = None) -> None:
        """Update sampling parameters."""
        if temperature is not None:
            self.temperature = temperature
        if max_tokens is not None:
            self.max_tokens = max_tokens

    def generate(self, prompt: str) -> str:
        """Generate text from prompt."""
        if not self._initialized:
            self.initialize()
            
        try:
            if self._backend == 'llama_cpp':
                output = self.llm(
                    prompt,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    top_p=self.top_p,
                    stop=["<|EOT|>", "Question:", "User:"]
                )
                return output['choices'][0]['text']
                
            elif self._backend == 'ctransformers':
                output = self.llm(
                    prompt,
                    max_new_tokens=self.max_tokens,
                    temperature=self.temperature,
                    top_p=self.top_p,
                    stop=["<|EOT|>", "Question:", "User:"]
                )
                return output
                
        except Exception as e:
            raise LocalLLMError(f"Generation failed: {e}")

    async def generate_async(self, prompt: str) -> str:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.generate, prompt)

    def is_initialized(self) -> bool:
        return self._initialized

    def cleanup(self) -> None:
        if self.llm:
            del self.llm
            self.llm = None
        self._initialized = False
