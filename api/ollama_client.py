"""
SecureCodeAI - Ollama Client
Client for local Ollama LLM inference.
"""

import requests
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class OllamaClient:
    """
    Ollama client for local LLM inference.
    
    Connects to a local Ollama server for code generation and patching.
    """
    
    def __init__(
        self,
        model: str = "deepseek-coder-v2-lite-instruct:latest",
        base_url: str = "http://localhost:11434",
        timeout: int = 120
    ):
        """
        Initialize Ollama client.
        
        Args:
            model: Model name to use (default: deepseek-coder-v2-lite-instruct)
            base_url: Ollama API base URL
            timeout: Request timeout in seconds
        """
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._initialized = False
    
    def initialize(self) -> None:
        """
        Initialize and verify Ollama connection.
        
        Raises:
            Exception: If Ollama server is not reachable
        """
        if self._initialized:
            return
        
        try:
            # Check if Ollama is running
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            response.raise_for_status()
            
            # Check if model is available
            models = response.json().get("models", [])
            model_names = [m.get("name", "") for m in models]
            
            if self.model not in model_names:
                # Try without :latest suffix
                base_model = self.model.replace(":latest", "")
                if not any(base_model in name for name in model_names):
                    logger.warning(f"Model {self.model} not found. Available: {model_names}")
                    # Still continue - model might work anyway
            
            self._initialized = True
            logger.info(f"Ollama client initialized with model: {self.model}")
            
        except requests.exceptions.ConnectionError:
            raise Exception(f"Cannot connect to Ollama at {self.base_url}. Is Ollama running?")
        except Exception as e:
            raise Exception(f"Failed to initialize Ollama client: {e}")
    
    def is_initialized(self) -> bool:
        """Check if client is initialized."""
        return self._initialized
    
    def generate(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> str:
        """
        Generate text from prompt using Ollama.
        
        Args:
            prompt: Input prompt for generation
            max_tokens: Maximum tokens to generate (default: 2048)
            temperature: Sampling temperature (default: 0.2)
            
        Returns:
            Generated text
        """
        if not self._initialized:
            self.initialize()
        
        # Build options
        options = {}
        if temperature is not None:
            options["temperature"] = temperature
        else:
            options["temperature"] = 0.2
        
        if max_tokens is not None:
            options["num_predict"] = max_tokens
        else:
            options["num_predict"] = 2048
        
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": options
                },
                timeout=self.timeout
            )
            
            if response.status_code == 500:
                # Ollama internal error (likely OOM)
                logger.warning("Ollama returned 500 - likely out of memory")
                raise Exception("Ollama out of memory - try a smaller model or CPU mode")
            
            response.raise_for_status()
            
            result = response.json()
            return result.get("response", "")
            
        except requests.exceptions.Timeout:
            logger.error(f"Ollama request timed out after {self.timeout}s")
            raise Exception("Ollama request timed out")
        except Exception as e:
            logger.error(f"Ollama generation failed: {e}")
            raise Exception(f"Ollama generation failed: {e}")
    
    async def generate_async(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> str:
        """
        Async version of generate (uses sync under the hood for Ollama).
        
        Args:
            prompt: Input prompt for generation
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            
        Returns:
            Generated text
        """
        # Ollama's Python API is sync, so we just call generate
        # For true async, consider using aiohttp
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.generate(prompt, max_tokens, temperature)
        )
    
    def generate_patch(self, code: str, vulnerability: dict) -> str:
        """
        Generate a security patch for vulnerable code.
        
        Args:
            code: Original vulnerable code
            vulnerability: Vulnerability information dict
            
        Returns:
            Patched code
        """
        vuln_type = vulnerability.get("vuln_type", "Security Vulnerability")
        location = vulnerability.get("location", "unknown")
        description = vulnerability.get("description", "")
        
        prompt = f"""You are a security expert. Fix the following security vulnerability in this Python code.

VULNERABILITY TYPE: {vuln_type}
LOCATION: {location}
DESCRIPTION: {description}

ORIGINAL CODE:
```python
{code}
```

INSTRUCTIONS:
1. Fix the security vulnerability while preserving functionality
2. Use secure coding practices
3. Return ONLY the fixed Python code, no explanations
4. Do not include markdown code blocks in your response

FIXED CODE:
"""
        
        response = self.generate(prompt, temperature=0.1)
        
        # Clean up the response - remove any markdown code blocks
        response = response.strip()
        if response.startswith("```python"):
            response = response[9:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        
        return response.strip()
    
    def cleanup(self) -> None:
        """Cleanup resources (no-op for Ollama)."""
        self._initialized = False
    
    def validate_python_syntax(self, code: str) -> tuple:
        """
        Validate Python code syntax.
        
        Args:
            code: Python code to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        import ast
        try:
            ast.parse(code)
            return (True, None)
        except SyntaxError as e:
            return (False, f"Syntax error at line {e.lineno}: {e.msg}")
