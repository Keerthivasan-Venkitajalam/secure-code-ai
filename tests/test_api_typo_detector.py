"""
Tests for API typo detector.

This module contains unit tests and property-based tests for the APITypoDetector.
"""

import pytest
from hypothesis import given, settings, strategies as st, assume

from agent.validators.api_typo_detector import APITypoDetector, APITypoSuggestion


class TestAPITypoDetector:
    """Unit tests for APITypoDetector."""
    
    def test_exact_match_not_flagged(self):
        """Test that exact API name matches are not flagged."""
        known_apis = ['set_voltage', 'get_voltage', 'set_sample_count']
        detector = APITypoDetector(known_apis=known_apis)
        
        code = "set_voltage(25)"
        suggestions = detector.detect_typos(code)
        
        assert len(suggestions) == 0
    
    def test_typo_detected(self):
        """Test that typos are detected and suggestions provided."""
        known_apis = ['set_voltage', 'get_voltage', 'set_sample_count']
        detector = APITypoDetector(known_apis=known_apis)
        
        code = "set_voltag(25)"  # Missing 'e'
        suggestions = detector.detect_typos(code)
        
        assert len(suggestions) >= 1
        assert suggestions[0].found_api == "set_voltag"
        assert "set_voltage" in suggestions[0].suggested_apis
    
    def test_similarity_threshold(self):
        """Test that only high similarity suggestions are returned."""
        known_apis = ['set_voltage', 'get_voltage', 'set_sample_count']
        detector = APITypoDetector(known_apis=known_apis)
        
        code = "set_voltag(25)"
        suggestions = detector.detect_typos(code)
        
        # All suggestions should have similarity > 0.8
        for suggestion in suggestions:
            for score in suggestion.similarity_scores:
                assert score > 0.8
    
    def test_max_suggestions(self):
        """Test that at most 3 suggestions are returned per typo."""
        known_apis = ['set_voltage', 'get_voltage', 'set_sample_count', 
                      'set_value', 'set_volt', 'set_volume']
        detector = APITypoDetector(known_apis=known_apis)
        
        code = "set_voltag(25)"
        suggestions = detector.detect_typos(code)
        
        assert len(suggestions) >= 1
        # Each suggestion should have at most 3 suggested APIs
        for suggestion in suggestions:
            assert len(suggestion.suggested_apis) <= 3
    
    def test_multiple_typos(self):
        """Test detection of multiple typos in same code."""
        known_apis = ['set_voltage', 'get_voltage', 'set_sample_count']
        detector = APITypoDetector(known_apis=known_apis)
        
        code = """
set_voltag(25)
get_voltag()
set_sampl_count(100)
"""
        suggestions = detector.detect_typos(code)
        
        # Should detect multiple typos
        assert len(suggestions) >= 2
    
    def test_empty_code(self):
        """Test detector with empty code."""
        known_apis = ['set_voltage']
        detector = APITypoDetector(known_apis=known_apis)
        
        suggestions = detector.detect_typos("")
        assert len(suggestions) == 0
    
    def test_no_api_calls(self):
        """Test detector with code containing no API calls."""
        known_apis = ['set_voltage']
        detector = APITypoDetector(known_apis=known_apis)
        
        code = """
x = 10
y = 20
z = x + y
"""
        suggestions = detector.detect_typos(code)
        assert len(suggestions) == 0
    
    def test_line_numbers(self):
        """Test that suggestions report correct line numbers."""
        known_apis = ['set_voltage']
        detector = APITypoDetector(known_apis=known_apis)
        
        code = """line 1
set_voltag(25)
line 3
"""
        suggestions = detector.detect_typos(code)
        
        assert len(suggestions) >= 1
        assert suggestions[0].location == "2"
    
    def test_suggestions_ordered_by_similarity(self):
        """Test that suggestions are ordered by descending similarity."""
        known_apis = ['set_voltage', 'set_value', 'get_voltage']
        detector = APITypoDetector(known_apis=known_apis)
        
        code = "set_voltag(25)"
        suggestions = detector.detect_typos(code)
        
        if len(suggestions) > 0 and len(suggestions[0].similarity_scores) > 1:
            scores = suggestions[0].similarity_scores
            # Scores should be in descending order
            for i in range(len(scores) - 1):
                assert scores[i] >= scores[i + 1]


class TestAPITypoDetectorProperties:
    """Property-based tests for APITypoDetector."""
    
    @settings(max_examples=100)
    @given(
        api_name=st.sampled_from(['set_voltage', 'get_voltage', 'set_sample_count', 
                                   'configure_hardware', 'initialize_hardware'])
    )
    def test_property_exact_match_not_flagged(self, api_name):
        """
        Feature: agentic-bug-hunter-integration
        Property 10: API Typo Suggestion Quality
        
        For any exact match to a known API, the detector should not flag it.
        
        Validates: Requirements 6.2, 6.3
        """
        known_apis = ['set_voltage', 'get_voltage', 'set_sample_count',
                      'configure_hardware', 'initialize_hardware']
        detector = APITypoDetector(known_apis=known_apis)
        
        code = f"{api_name}()"
        suggestions = detector.detect_typos(code)
        
        # Property: No suggestions for exact matches
        assert len(suggestions) == 0, \
            f"Exact match '{api_name}' should not be flagged"
    
    @settings(max_examples=100)
    @given(
        typo=st.sampled_from([
            'set_voltag',      # Missing 'e'
            'set_voltagee',    # Extra 'e'
            'set_voltaeg',     # Transposed 'g' and 'e'
            'get_voltag',      # Missing 'e'
            'set_sampl_count', # Missing 'e'
        ])
    )
    def test_property_typo_suggestions_above_threshold(self, typo):
        """
        Feature: agentic-bug-hunter-integration
        Property 10: API Typo Suggestion Quality
        
        For any detected typo, all suggested APIs should have similarity > 0.8.
        
        Validates: Requirements 6.2, 6.3
        """
        known_apis = ['set_voltage', 'get_voltage', 'set_sample_count',
                      'configure_hardware', 'initialize_hardware']
        detector = APITypoDetector(known_apis=known_apis)
        
        code = f"{typo}()"
        suggestions = detector.detect_typos(code)
        
        # Property: All suggestions should have similarity > 0.8
        for suggestion in suggestions:
            for score in suggestion.similarity_scores:
                assert score > 0.8, \
                    f"Suggestion score {score} should be > 0.8"
    
    @settings(max_examples=100)
    @given(
        typo=st.sampled_from([
            'set_voltag',
            'set_voltagee',
            'get_voltag',
            'set_sampl_count',
        ])
    )
    def test_property_suggestions_ordered_descending(self, typo):
        """
        Feature: agentic-bug-hunter-integration
        Property 10: API Typo Suggestion Quality
        
        For any detected typo, suggestions should be ordered by descending similarity.
        
        Validates: Requirements 6.2, 6.3
        """
        known_apis = ['set_voltage', 'get_voltage', 'set_sample_count',
                      'configure_hardware', 'initialize_hardware']
        detector = APITypoDetector(known_apis=known_apis)
        
        code = f"{typo}()"
        suggestions = detector.detect_typos(code)
        
        # Property: Suggestions should be ordered by descending similarity
        for suggestion in suggestions:
            scores = suggestion.similarity_scores
            if len(scores) > 1:
                for i in range(len(scores) - 1):
                    assert scores[i] >= scores[i + 1], \
                        f"Scores should be in descending order: {scores}"
    
    @settings(max_examples=100)
    @given(
        typo=st.sampled_from([
            'set_voltag',
            'set_voltagee',
            'get_voltag',
            'set_sampl_count',
        ])
    )
    def test_property_max_three_suggestions(self, typo):
        """
        Feature: agentic-bug-hunter-integration
        Property 10: API Typo Suggestion Quality
        
        For any detected typo, at most 3 suggestions should be returned.
        
        Validates: Requirements 6.2, 6.3
        """
        # Use many similar APIs to test the limit
        known_apis = ['set_voltage', 'get_voltage', 'set_sample_count',
                      'set_value', 'set_volt', 'set_volume', 'set_voltmeter',
                      'configure_hardware', 'initialize_hardware']
        detector = APITypoDetector(known_apis=known_apis)
        
        code = f"{typo}()"
        suggestions = detector.detect_typos(code)
        
        # Property: At most 3 suggestions per typo
        for suggestion in suggestions:
            assert len(suggestion.suggested_apis) <= 3, \
                f"Should have at most 3 suggestions, got {len(suggestion.suggested_apis)}"
