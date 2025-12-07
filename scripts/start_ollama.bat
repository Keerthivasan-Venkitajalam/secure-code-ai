@echo off
REM Start Ollama with memory-constrained settings for DeepSeek stability
set OLLAMA_MAX_LOADED_MODELS=1
set OLLAMA_NUM_PARALLEL=1
set OLLAMA_FLASH_ATTENTION=0
ollama serve
