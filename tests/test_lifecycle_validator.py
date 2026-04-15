"""
Tests for lifecycle validator.

This module contains unit tests and property-based tests for the LifecycleValidator.
"""

import pytest
from hypothesis import given, settings, strategies as st

from agent.validators.lifecycle_validator import LifecycleValidator, LifecycleViolation


class TestLifecycleValidator:
    """Unit tests for LifecycleValidator."""
    
    def test_correct_ordering(self):
        """Test that correct BEGIN->END ordering is not flagged."""
        validator = LifecycleValidator()
        code = """
RDI_BEGIN()
# some code
RDI_END()
"""
        violations = validator.validate(code)
        assert len(violations) == 0
    
    def test_wrong_ordering(self):
        """Test that END before BEGIN is flagged."""
        validator = LifecycleValidator()
        code = """
RDI_END()
# some code
RDI_BEGIN()
"""
        violations = validator.validate(code)
        
        assert len(violations) >= 1
        # Should have a wrong_order violation
        wrong_order_violations = [v for v in violations if v.issue == "wrong_order"]
        assert len(wrong_order_violations) >= 1
        assert wrong_order_violations[0].end_line == 2
        assert wrong_order_violations[0].begin_line == 4
    
    def test_missing_end(self):
        """Test that BEGIN without END is flagged."""
        validator = LifecycleValidator()
        code = """
RDI_BEGIN()
# some code
"""
        violations = validator.validate(code)
        
        assert len(violations) >= 1
        missing_end_violations = [v for v in violations if v.issue == "missing_end"]
        assert len(missing_end_violations) >= 1
        assert missing_end_violations[0].begin_line == 2
    
    def test_missing_begin(self):
        """Test that END without BEGIN is flagged."""
        validator = LifecycleValidator()
        code = """
# some code
RDI_END()
"""
        violations = validator.validate(code)
        
        assert len(violations) >= 1
        missing_begin_violations = [v for v in violations if v.issue == "missing_begin"]
        assert len(missing_begin_violations) >= 1
        assert missing_begin_violations[0].end_line == 3
    
    def test_multiple_correct_pairs(self):
        """Test multiple correct BEGIN->END pairs."""
        validator = LifecycleValidator()
        code = """
RDI_BEGIN()
# code block 1
RDI_END()

RDI_BEGIN()
# code block 2
RDI_END()
"""
        violations = validator.validate(code)
        assert len(violations) == 0
    
    def test_empty_code(self):
        """Test validator with empty code."""
        validator = LifecycleValidator()
        violations = validator.validate("")
        assert len(violations) == 0
    
    def test_no_lifecycle_calls(self):
        """Test validator with code containing no lifecycle calls."""
        validator = LifecycleValidator()
        code = """
def my_function():
    x = 10
    return x * 2
"""
        violations = validator.validate(code)
        assert len(violations) == 0
    
    def test_case_insensitive_matching(self):
        """Test that lifecycle call matching is case-insensitive."""
        validator = LifecycleValidator()
        code = """
rdi_begin()
# some code
rdi_end()
"""
        violations = validator.validate(code)
        assert len(violations) == 0


class TestLifecycleValidatorProperties:
    """Property-based tests for LifecycleValidator."""
    
    @settings(max_examples=100)
    @given(
        num_lines_before=st.integers(min_value=0, max_value=10),
        num_lines_between=st.integers(min_value=0, max_value=10),
        num_lines_after=st.integers(min_value=0, max_value=10)
    )
    def test_property_correct_ordering_not_flagged(
        self,
        num_lines_before,
        num_lines_between,
        num_lines_after
    ):
        """
        Feature: agentic-bug-hunter-integration
        Property 9: Lifecycle Ordering Detection
        
        For any code with RDI_BEGIN before RDI_END, the validator should not
        flag an ordering violation.
        
        Validates: Requirements 5.2
        """
        validator = LifecycleValidator()
        
        # Build code with correct ordering
        lines = []
        lines.extend(['# line before'] * num_lines_before)
        lines.append('RDI_BEGIN()')
        lines.extend(['# line between'] * num_lines_between)
        lines.append('RDI_END()')
        lines.extend(['# line after'] * num_lines_after)
        
        code = '\n'.join(lines)
        violations = validator.validate(code)
        
        # Property: No wrong_order violations for correct ordering
        wrong_order_violations = [v for v in violations if v.issue == "wrong_order"]
        assert len(wrong_order_violations) == 0, \
            f"Correct ordering should not be flagged as wrong_order"
    
    @settings(max_examples=100)
    @given(
        num_lines_before=st.integers(min_value=0, max_value=10),
        num_lines_between=st.integers(min_value=0, max_value=10),
        num_lines_after=st.integers(min_value=0, max_value=10)
    )
    def test_property_wrong_ordering_flagged(
        self,
        num_lines_before,
        num_lines_between,
        num_lines_after
    ):
        """
        Feature: agentic-bug-hunter-integration
        Property 9: Lifecycle Ordering Detection
        
        For any code with RDI_END before RDI_BEGIN, the validator should
        flag an ordering violation.
        
        Validates: Requirements 5.2
        """
        validator = LifecycleValidator()
        
        # Build code with wrong ordering
        lines = []
        lines.extend(['# line before'] * num_lines_before)
        lines.append('RDI_END()')
        lines.extend(['# line between'] * num_lines_between)
        lines.append('RDI_BEGIN()')
        lines.extend(['# line after'] * num_lines_after)
        
        code = '\n'.join(lines)
        violations = validator.validate(code)
        
        # Property: Should have wrong_order violation
        wrong_order_violations = [v for v in violations if v.issue == "wrong_order"]
        assert len(wrong_order_violations) >= 1, \
            f"Wrong ordering should be flagged"
        
        # Property: END line should be before BEGIN line
        for violation in wrong_order_violations:
            assert violation.end_line < violation.begin_line, \
                f"Violation should indicate END before BEGIN"
