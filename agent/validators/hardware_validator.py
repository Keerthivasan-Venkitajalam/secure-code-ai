"""
Hardware constraint validator for checking voltage and sample count limits.

This module provides validation for hardware API calls to ensure they comply
with hardware constraints such as voltage limits and sample count limits.
"""

import re
from dataclasses import dataclass
from typing import List, Any, Dict, Optional


@dataclass
class HardwareViolation:
    """Represents a hardware constraint violation.
    
    Attributes:
        location: Line number where violation occurs
        rule: Name of the rule violated (e.g., "voltage_limit", "sample_count_limit")
        actual_value: The actual value found in the code
        expected_value: The expected value or range
        severity: Severity level (high, medium, low)
        message: Human-readable description of the violation
    """
    location: str
    rule: str
    actual_value: Any
    expected_value: Any
    severity: str
    message: str


class HardwareValidator:
    """Validates code for hardware constraint violations.
    
    This validator checks for:
    - Voltage values exceeding 30V
    - Sample counts exceeding 8192
    
    The validator parses code for hardware API calls and checks their parameters
    against configured rules.
    """
    
    # Default hardware constraint rules
    DEFAULT_RULES = {
        "max_voltage": 30,
        "max_sample_count": 8192
    }
    
    # Patterns for detecting hardware API calls
    VOLTAGE_PATTERN = re.compile(
        r'set_voltage\s*\(\s*([0-9]+(?:\.[0-9]+)?)\s*\)',
        re.IGNORECASE
    )
    
    SAMPLE_COUNT_PATTERN = re.compile(
        r'set_sample(?:_count|s)?\s*\(\s*([0-9]+)\s*\)',
        re.IGNORECASE
    )
    
    def __init__(self, rules: Optional[Dict[str, Any]] = None):
        """Initialize hardware validator with constraint rules.
        
        Args:
            rules: Dictionary of hardware constraint rules. If None, uses DEFAULT_RULES.
                   Expected keys: "max_voltage", "max_sample_count"
        """
        self.rules = rules if rules is not None else self.DEFAULT_RULES.copy()
    
    def validate(self, code: str) -> List[HardwareViolation]:
        """Check code for hardware constraint violations.
        
        Args:
            code: Source code to validate
            
        Returns:
            List of HardwareViolation objects, empty if no violations found
        """
        violations = []
        
        # Check for voltage violations
        violations.extend(self._check_voltage_violations(code))
        
        # Check for sample count violations
        violations.extend(self._check_sample_count_violations(code))
        
        return violations
    
    def _check_voltage_violations(self, code: str) -> List[HardwareViolation]:
        """Check for voltage limit violations.
        
        Args:
            code: Source code to check
            
        Returns:
            List of voltage violations
        """
        violations = []
        max_voltage = self.rules.get("max_voltage", 30)
        
        lines = code.split('\n')
        for line_num, line in enumerate(lines, start=1):
            matches = self.VOLTAGE_PATTERN.finditer(line)
            for match in matches:
                voltage_str = match.group(1)
                voltage = float(voltage_str)
                
                if voltage > max_voltage:
                    violations.append(HardwareViolation(
                        location=str(line_num),
                        rule="voltage_limit",
                        actual_value=voltage,
                        expected_value=f"<= {max_voltage}V",
                        severity="high",
                        message=f"Voltage {voltage}V exceeds maximum limit of {max_voltage}V"
                    ))
        
        return violations
    
    def _check_sample_count_violations(self, code: str) -> List[HardwareViolation]:
        """Check for sample count limit violations.
        
        Args:
            code: Source code to check
            
        Returns:
            List of sample count violations
        """
        violations = []
        max_sample_count = self.rules.get("max_sample_count", 8192)
        
        lines = code.split('\n')
        for line_num, line in enumerate(lines, start=1):
            matches = self.SAMPLE_COUNT_PATTERN.finditer(line)
            for match in matches:
                sample_count_str = match.group(1)
                sample_count = int(sample_count_str)
                
                if sample_count > max_sample_count:
                    violations.append(HardwareViolation(
                        location=str(line_num),
                        rule="sample_count_limit",
                        actual_value=sample_count,
                        expected_value=f"<= {max_sample_count}",
                        severity="high",
                        message=f"Sample count {sample_count} exceeds maximum limit of {max_sample_count}"
                    ))
        
        return violations
