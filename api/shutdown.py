"""
SecureCodeAI - Graceful Shutdown Handler
Handles SIGTERM and SIGINT signals for graceful container shutdown.
"""

import signal
import sys
from typing import Optional, Callable
from .logging_config import logger


class ShutdownHandler:
    """
    Handles graceful shutdown on SIGTERM/SIGINT signals.
    
    Ensures:
    - In-flight requests complete
    - Resources are cleaned up properly
    - vLLM engine is shutdown gracefully
    """
    
    def __init__(self):
        self.shutdown_requested = False
        self.shutdown_callback: Optional[Callable] = None
    
    def register_callback(self, callback: Callable) -> None:
        """
        Register a callback to be called on shutdown.
        
        Args:
            callback: Function to call during shutdown
        """
        self.shutdown_callback = callback
    
    def handle_signal(self, signum: int, frame) -> None:
        """
        Handle shutdown signals (SIGTERM, SIGINT).
        
        Args:
            signum: Signal number
            frame: Current stack frame
        """
        signal_name = signal.Signals(signum).name
        logger.info(f"Received {signal_name} signal, initiating graceful shutdown...")
        
        if self.shutdown_requested:
            logger.warning("Shutdown already in progress, forcing exit...")
            sys.exit(1)
        
        self.shutdown_requested = True
        
        # Call registered shutdown callback
        if self.shutdown_callback:
            try:
                logger.info("Executing shutdown callback...")
                self.shutdown_callback()
                logger.info("Shutdown callback completed")
            except Exception as e:
                logger.error(f"Error during shutdown callback: {e}", exc_info=True)
        
        logger.info("Graceful shutdown complete")
        sys.exit(0)
    
    def register_signals(self) -> None:
        """Register signal handlers for SIGTERM and SIGINT."""
        signal.signal(signal.SIGTERM, self.handle_signal)
        signal.signal(signal.SIGINT, self.handle_signal)
        logger.info("Registered signal handlers for graceful shutdown")
    
    def is_shutdown_requested(self) -> bool:
        """Check if shutdown has been requested."""
        return self.shutdown_requested


# Global shutdown handler instance
_shutdown_handler: Optional[ShutdownHandler] = None


def get_shutdown_handler() -> ShutdownHandler:
    """
    Get or create global shutdown handler instance.
    
    Returns:
        Global ShutdownHandler instance
    """
    global _shutdown_handler
    
    if _shutdown_handler is None:
        _shutdown_handler = ShutdownHandler()
    
    return _shutdown_handler


def register_shutdown_callback(callback: Callable) -> None:
    """
    Register a callback to be called on shutdown.
    
    Args:
        callback: Function to call during shutdown
    """
    handler = get_shutdown_handler()
    handler.register_callback(callback)


def setup_signal_handlers() -> None:
    """Setup signal handlers for graceful shutdown."""
    handler = get_shutdown_handler()
    handler.register_signals()
