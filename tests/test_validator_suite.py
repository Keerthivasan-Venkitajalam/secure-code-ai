"""
Tests for validator suite.

This module contains unit tests for the ValidatorSuite that coordinates
all specialized validators.
"""

import pytest

from agent.validators.validator_suite import ValidatorSuite, ValidationResults


class TestValidatorSuite:
    """Unit tests for ValidatorSuite."""
    
    def test_all_validators_enabled(self):
        """Test suite with all validators enabled."""
        suite = ValidatorSuite(
            enable_hardware=True,
            enable_lifecycle=True,
            enable_api_typo=True
        )
        
        code = """
set_voltage(35)
RDI_BEGIN()
RDI_END()
set_voltag(25)
"""
        results = suite.validate(code)
        
        assert isinstance(results, ValidationResults)
        assert len(results.hardware_violations) >= 1  # voltage exceeds limit
        assert len(results.lifecycle_violations) == 0  # correct ordering
        assert len(results.api_typo_suggestions) >= 1  # typo in set_voltag
    
    def test_hardware_validator_disabled(self):
        """Test suite with hardware validator disabled."""
        suite = ValidatorSuite(
            enable_hardware=False,
            enable_lifecycle=True,
            enable_api_typo=True
        )
        
        code = "set_voltage(35)"
        results = suite.validate(code)
        
        assert len(results.hardware_violations) == 0
    
    def test_lifecycle_validator_disabled(self):
        """Test suite with lifecycle validator disabled."""
        suite = ValidatorSuite(
            enable_hardware=True,
            enable_lifecycle=False,
            enable_api_typo=True
        )
        
        code = """
RDI_END()
RDI_BEGIN()
"""
        results = suite.validate(code)
        
        assert len(results.lifecycle_violations) == 0
    
    def test_api_typo_detector_disabled(self):
        """Test suite with API typo detector disabled."""
        suite = ValidatorSuite(
            enable_hardware=True,
            enable_lifecycle=True,
            enable_api_typo=False
        )
        
        code = "set_voltag(25)"
        results = suite.validate(code)
        
        assert len(results.api_typo_suggestions) == 0
    
    def test_conditional_hardware_validation(self):
        """Test that hardware validator only runs when hardware calls present."""
        suite = ValidatorSuite(enable_hardware=True)
        
        # Code without hardware calls
        code = """
def my_function():
    x = 10
    return x * 2
"""
        results = suite.validate(code)
        
        assert len(results.hardware_violations) == 0
    
    def test_conditional_lifecycle_validation(self):
        """Test that lifecycle validator only runs when lifecycle calls present."""
        suite = ValidatorSuite(enable_lifecycle=True)
        
        # Code without lifecycle calls
        code = """
def my_function():
    x = 10
    return x * 2
"""
        results = suite.validate(code)
        
        assert len(results.lifecycle_violations) == 0
    
    def test_empty_code(self):
        """Test suite with empty code."""
        suite = ValidatorSuite()
        results = suite.validate("")
        
        assert len(results.hardware_violations) == 0
        assert len(results.lifecycle_violations) == 0
        assert len(results.api_typo_suggestions) == 0
    
    def test_custom_hardware_rules(self):
        """Test suite with custom hardware rules."""
        suite = ValidatorSuite(
            hardware_rules={"max_voltage": 20, "max_sample_count": 4096}
        )
        
        code = "set_voltage(25)"
        results = suite.validate(code)
        
        # Should flag voltage of 25 with custom limit of 20
        assert len(results.hardware_violations) >= 1
    
    def test_custom_known_apis(self):
        """Test suite with custom known APIs."""
        suite = ValidatorSuite(
            known_apis=['my_custom_api', 'another_api']
        )
        
        code = "my_custom_api()"
        results = suite.validate(code)
        
        # Should not flag exact match
        assert len(results.api_typo_suggestions) == 0
        
        code = "my_custom_ap()"  # Typo
        results = suite.validate(code)
        
        # Should flag typo
        assert len(results.api_typo_suggestions) >= 1
    
    def test_multiple_violations_same_code(self):
        """Test detection of multiple types of violations in same code."""
        suite = ValidatorSuite()
        
        code = """
set_voltage(35)
set_sample_count(10000)
RDI_END()
RDI_BEGIN()
set_voltag(25)
"""
        results = suite.validate(code)
        
        # Should have hardware violations
        assert len(results.hardware_violations) >= 2
        
        # Should have lifecycle violations
        assert len(results.lifecycle_violations) >= 1
        
        # Should have API typo suggestions
        assert len(results.api_typo_suggestions) >= 1
    
    def test_validation_results_structure(self):
        """Test that ValidationResults has correct structure."""
        suite = ValidatorSuite()
        results = suite.validate("set_voltage(35)")
        
        assert hasattr(results, 'hardware_violations')
        assert hasattr(results, 'lifecycle_violations')
        assert hasattr(results, 'api_typo_suggestions')
        assert isinstance(results.hardware_violations, list)
        assert isinstance(results.lifecycle_violations, list)
        assert isinstance(results.api_typo_suggestions, list)
