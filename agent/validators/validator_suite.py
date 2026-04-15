"""
Validator suite that coordinates all specialized validators.

This module provides a unified interface for running all validators
(hardware, lifecycle, API typo) on code and aggregating their results.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from .hardware_validator import HardwareValidator, HardwareViolation
from .lifecycle_validator import LifecycleValidator, LifecycleViolation
from .api_typo_detector import APITypoDetector, APITypoSuggestion


@dataclass
class ValidationResults:
    """Aggregated results from all validators.
    
    Attributes:
        hardware_violations: List of hardware constraint violations
        lifecycle_violations: List of lifecycle ordering violations
        api_typo_suggestions: List of API typo suggestions
    """
    hardware_violations: List[HardwareViolation]
    lifecycle_violations: List[LifecycleViolation]
    api_typo_suggestions: List[APITypoSuggestion]


class ValidatorSuite:
    """Coordinates all specialized validators.
    
    This suite:
    - Runs validators conditionally based on code content
    - Aggregates results from all validators
    - Provides a unified interface for validation
    """
    
    def __init__(
        self,
        hardware_rules: Optional[Dict[str, Any]] = None,
        known_apis: Optional[List[str]] = None,
        enable_hardware: bool = True,
        enable_lifecycle: bool = True,
        enable_api_typo: bool = True
    ):
        """Initialize validator suite.
        
        Args:
            hardware_rules: Rules for hardware validator (None uses defaults)
            known_apis: List of known API names for typo detection (None uses defaults)
            enable_hardware: Whether to enable hardware validation
            enable_lifecycle: Whether to enable lifecycle validation
            enable_api_typo: Whether to enable API typo detection
        """
        self.enable_hardware = enable_hardware
        self.enable_lifecycle = enable_lifecycle
        self.enable_api_typo = enable_api_typo
        
        # Initialize validators
        if self.enable_hardware:
            self.hardware_validator = HardwareValidator(rules=hardware_rules)
        
        if self.enable_lifecycle:
            self.lifecycle_validator = LifecycleValidator()
        
        if self.enable_api_typo:
            # Use default known APIs if none provided
            if known_apis is None:
                known_apis = self._get_default_known_apis()
            self.api_typo_detector = APITypoDetector(known_apis=known_apis)
    
    def validate(self, code: str) -> ValidationResults:
        """Run all enabled validators on code.
        
        Args:
            code: Source code to validate
            
        Returns:
            ValidationResults containing all violations and suggestions
        """
        hardware_violations = []
        lifecycle_violations = []
        api_typo_suggestions = []
        
        # Run hardware validator if enabled and code contains hardware calls
        if self.enable_hardware and self._has_hardware_calls(code):
            hardware_violations = self.hardware_validator.validate(code)
        
        # Run lifecycle validator if enabled and code contains lifecycle calls
        if self.enable_lifecycle and self._has_lifecycle_calls(code):
            lifecycle_violations = self.lifecycle_validator.validate(code)
        
        # Run API typo detector if enabled
        if self.enable_api_typo:
            api_typo_suggestions = self.api_typo_detector.detect_typos(code)
        
        return ValidationResults(
            hardware_violations=hardware_violations,
            lifecycle_violations=lifecycle_violations,
            api_typo_suggestions=api_typo_suggestions
        )
    
    def _has_hardware_calls(self, code: str) -> bool:
        """Check if code contains hardware API calls.
        
        Args:
            code: Source code to check
            
        Returns:
            True if hardware calls are present
        """
        hardware_keywords = ['set_voltage', 'set_sample', 'set_samples', 'set_sample_count']
        code_lower = code.lower()
        return any(keyword in code_lower for keyword in hardware_keywords)
    
    def _has_lifecycle_calls(self, code: str) -> bool:
        """Check if code contains lifecycle calls.
        
        Args:
            code: Source code to check
            
        Returns:
            True if lifecycle calls are present
        """
        lifecycle_keywords = ['rdi_begin', 'rdi_end']
        code_lower = code.lower()
        return any(keyword in code_lower for keyword in lifecycle_keywords)
    
    def _get_default_known_apis(self) -> List[str]:
        """Get default list of known API names.
        
        Returns:
            List of common API names
        """
        return [
            # Hardware APIs
            'set_voltage',
            'get_voltage',
            'set_sample_count',
            'get_sample_count',
            'set_samples',
            'get_samples',
            'configure_hardware',
            'initialize_hardware',
            'shutdown_hardware',
            
            # Lifecycle APIs
            'RDI_BEGIN',
            'RDI_END',
            'RDI_INIT',
            'RDI_CLEANUP',
            
            # Common Python APIs
            'print',
            'input',
            'open',
            'close',
            'read',
            'write',
            'append',
            'range',
            'len',
            'str',
            'int',
            'float',
            'list',
            'dict',
            'set',
            'tuple',
        ]
