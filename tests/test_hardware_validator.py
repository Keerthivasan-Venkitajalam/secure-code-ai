"""
Tests for hardware constraint validator.

This module contains unit tests and property-based tests for the HardwareValidator.
"""

import pytest
from hypothesis import given, settings, strategies as st

from agent.validators.hardware_validator import HardwareValidator, HardwareViolation


class TestHardwareValidator:
    """Unit tests for HardwareValidator."""
    
    def test_voltage_within_limit(self):
        """Test that voltages within limit are not flagged."""
        validator = HardwareValidator()
        code = "set_voltage(25)"
        violations = validator.validate(code)
        assert len(violations) == 0
    
    def test_voltage_at_limit(self):
        """Test that voltage exactly at limit is not flagged."""
        validator = HardwareValidator()
        code = "set_voltage(30)"
        violations = validator.validate(code)
        assert len(violations) == 0
    
    def test_voltage_exceeds_limit(self):
        """Test that voltage exceeding limit is flagged."""
        validator = HardwareValidator()
        code = "set_voltage(35)"
        violations = validator.validate(code)
        
        assert len(violations) == 1
        assert violations[0].rule == "voltage_limit"
        assert violations[0].actual_value == 35
        assert violations[0].severity == "high"
    
    def test_multiple_voltage_violations(self):
        """Test detection of multiple voltage violations."""
        validator = HardwareValidator()
        code = """
set_voltage(35)
set_voltage(40)
set_voltage(25)
"""
        violations = validator.validate(code)
        
        assert len(violations) == 2
        assert all(v.rule == "voltage_limit" for v in violations)
        assert violations[0].actual_value == 35
        assert violations[1].actual_value == 40
    
    def test_sample_count_within_limit(self):
        """Test that sample counts within limit are not flagged."""
        validator = HardwareValidator()
        code = "set_sample_count(8000)"
        violations = validator.validate(code)
        assert len(violations) == 0
    
    def test_sample_count_at_limit(self):
        """Test that sample count exactly at limit is not flagged."""
        validator = HardwareValidator()
        code = "set_sample_count(8192)"
        violations = validator.validate(code)
        assert len(violations) == 0
    
    def test_sample_count_exceeds_limit(self):
        """Test that sample count exceeding limit is flagged."""
        validator = HardwareValidator()
        code = "set_sample_count(10000)"
        violations = validator.validate(code)
        
        assert len(violations) == 1
        assert violations[0].rule == "sample_count_limit"
        assert violations[0].actual_value == 10000
        assert violations[0].severity == "high"
    
    def test_custom_rules(self):
        """Test validator with custom rules."""
        validator = HardwareValidator(rules={"max_voltage": 20, "max_sample_count": 4096})
        
        code = "set_voltage(25)"
        violations = validator.validate(code)
        assert len(violations) == 1
        assert violations[0].actual_value == 25
    
    def test_empty_code(self):
        """Test validator with empty code."""
        validator = HardwareValidator()
        violations = validator.validate("")
        assert len(violations) == 0
    
    def test_no_hardware_calls(self):
        """Test validator with code containing no hardware API calls."""
        validator = HardwareValidator()
        code = """
def my_function():
    x = 10
    return x * 2
"""
        violations = validator.validate(code)
        assert len(violations) == 0
    
    def test_case_insensitive_matching(self):
        """Test that API call matching is case-insensitive."""
        validator = HardwareValidator()
        code = "SET_VOLTAGE(35)"
        violations = validator.validate(code)
        assert len(violations) == 1
    
    def test_decimal_voltage(self):
        """Test voltage with decimal values."""
        validator = HardwareValidator()
        code = "set_voltage(35.5)"
        violations = validator.validate(code)
        
        assert len(violations) == 1
        assert violations[0].actual_value == 35.5
    
    def test_line_numbers(self):
        """Test that violations report correct line numbers."""
        validator = HardwareValidator()
        code = """line 1
set_voltage(35)
line 3
set_voltage(40)
"""
        violations = validator.validate(code)
        
        assert len(violations) == 2
        assert violations[0].location == "2"
        assert violations[1].location == "4"


class TestHardwareValidatorProperties:
    """Property-based tests for HardwareValidator."""
    
    @settings(max_examples=100)
    @given(voltage=st.floats(min_value=0, max_value=30, allow_nan=False, allow_infinity=False))
    def test_property_voltage_within_limit_not_flagged(self, voltage):
        """
        Feature: agentic-bug-hunter-integration
        Property 8: Hardware Constraint Validation Accuracy
        
        For any voltage value <= 30V, the hardware validator should not flag it.
        
        Validates: Requirements 4.2
        """
        validator = HardwareValidator()
        code = f"set_voltage({voltage})"
        violations = validator.validate(code)
        
        # Property: No violations for voltages at or below limit
        assert len(violations) == 0, f"Voltage {voltage}V should not be flagged"
    
    @settings(max_examples=100)
    @given(voltage=st.floats(min_value=30.01, max_value=1000, allow_nan=False, allow_infinity=False))
    def test_property_voltage_exceeds_limit_flagged(self, voltage):
        """
        Feature: agentic-bug-hunter-integration
        Property 8: Hardware Constraint Validation Accuracy
        
        For any voltage value > 30V, the hardware validator should flag it.
        
        Validates: Requirements 4.2
        """
        validator = HardwareValidator()
        code = f"set_voltage({voltage})"
        violations = validator.validate(code)
        
        # Property: All violations for voltages above limit
        assert len(violations) == 1, f"Voltage {voltage}V should be flagged"
        assert violations[0].rule == "voltage_limit"
        assert violations[0].actual_value == voltage
        assert violations[0].severity == "high"
    
    @settings(max_examples=100)
    @given(sample_count=st.integers(min_value=1, max_value=8192))
    def test_property_sample_count_within_limit_not_flagged(self, sample_count):
        """
        Feature: agentic-bug-hunter-integration
        Property 8: Hardware Constraint Validation Accuracy
        
        For any sample count <= 8192, the hardware validator should not flag it.
        
        Validates: Requirements 4.2
        """
        validator = HardwareValidator()
        code = f"set_sample_count({sample_count})"
        violations = validator.validate(code)
        
        # Property: No violations for sample counts at or below limit
        assert len(violations) == 0, f"Sample count {sample_count} should not be flagged"
    
    @settings(max_examples=100)
    @given(sample_count=st.integers(min_value=8193, max_value=100000))
    def test_property_sample_count_exceeds_limit_flagged(self, sample_count):
        """
        Feature: agentic-bug-hunter-integration
        Property 8: Hardware Constraint Validation Accuracy
        
        For any sample count > 8192, the hardware validator should flag it.
        
        Validates: Requirements 4.2
        """
        validator = HardwareValidator()
        code = f"set_sample_count({sample_count})"
        violations = validator.validate(code)
        
        # Property: All violations for sample counts above limit
        assert len(violations) == 1, f"Sample count {sample_count} should be flagged"
        assert violations[0].rule == "sample_count_limit"
        assert violations[0].actual_value == sample_count
        assert violations[0].severity == "high"
