"""
Tests for Knowledge Base Manager

This module contains unit tests and property-based tests for the KnowledgeBase
component of the Agentic Bug Hunter integration.
"""

import pytest
import os
import tempfile
import csv
from pathlib import Path
from hypothesis import given, strategies as st, settings, HealthCheck

from agent.knowledge import KnowledgeBase, BugPattern, KnowledgeBaseStats


# ============================================================================
# Property-Based Tests
# ============================================================================

@settings(
    max_examples=10,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    deadline=None
)
@given(load_count=st.integers(min_value=2, max_value=5))
def test_knowledge_base_loading_idempotence(load_count):
    """
    Feature: agentic-bug-hunter-integration
    Property 4: Knowledge Base Loading Idempotence
    
    For any knowledge base file, loading it multiple times should produce
    identical vector embeddings and the same number of patterns.
    
    Validates: Requirements 2.1, 2.2
    """
    # Create a temporary CSV file with test data
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['ID', 'Explanation', 'Context', 'Code', 'Correct Code'])
        writer.writeheader()
        
        # Write some test patterns
        for i in range(5):
            writer.writerow({
                'ID': str(i),
                'Explanation': f'Bug explanation {i}',
                'Context': f'Context {i}',
                'Code': f'buggy_code_{i}',
                'Correct Code': f'correct_code_{i}'
            })
        
        temp_path = f.name
    
    try:
        # Load the knowledge base multiple times
        results = []
        for _ in range(load_count):
            kb = KnowledgeBase(temp_path)
            patterns = kb.load_patterns()
            results.append({
                'pattern_count': len(patterns),
                'pattern_ids': sorted([p.id for p in patterns]),
                'pattern_explanations': sorted([p.explanation for p in patterns]),
                'pattern_contexts': sorted([p.context for p in patterns]),
                'pattern_buggy_codes': sorted([p.buggy_code for p in patterns]),
                'pattern_correct_codes': sorted([p.correct_code for p in patterns])
            })
        
        # Property: All loads should produce identical results
        first_result = results[0]
        for result in results[1:]:
            assert result['pattern_count'] == first_result['pattern_count'], \
                "Pattern count should be identical across loads"
            assert result['pattern_ids'] == first_result['pattern_ids'], \
                "Pattern IDs should be identical across loads"
            assert result['pattern_explanations'] == first_result['pattern_explanations'], \
                "Pattern explanations should be identical across loads"
            assert result['pattern_contexts'] == first_result['pattern_contexts'], \
                "Pattern contexts should be identical across loads"
            assert result['pattern_buggy_codes'] == first_result['pattern_buggy_codes'], \
                "Pattern buggy codes should be identical across loads"
            assert result['pattern_correct_codes'] == first_result['pattern_correct_codes'], \
                "Pattern correct codes should be identical across loads"
    
    finally:
        # Clean up
        os.unlink(temp_path)


# ============================================================================
# Unit Tests
# ============================================================================

def test_csv_parsing_with_valid_data():
    """
    Test CSV parsing with valid data.
    
    Requirements: 2.1
    """
    # Create a temporary CSV file with valid data
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['ID', 'Explanation', 'Context', 'Code', 'Correct Code', 'Category', 'Severity'])
        writer.writeheader()
        writer.writerow({
            'ID': '1',
            'Explanation': 'Use correct mode',
            'Context': 'Hardware configuration',
            'Code': 'set_mode(WRONG)',
            'Correct Code': 'set_mode(CORRECT)',
            'Category': 'hardware',
            'Severity': 'high'
        })
        writer.writerow({
            'ID': '2',
            'Explanation': 'Check lifecycle order',
            'Context': 'RDI lifecycle',
            'Code': 'RDI_END(); RDI_BEGIN();',
            'Correct Code': 'RDI_BEGIN(); RDI_END();',
            'Category': 'lifecycle',
            'Severity': 'medium'
        })
        temp_path = f.name
    
    try:
        kb = KnowledgeBase(temp_path)
        patterns = kb.load_patterns()
        
        # Verify correct number of patterns loaded
        assert len(patterns) == 2
        
        # Verify first pattern
        pattern1 = kb.get_pattern('1')
        assert pattern1 is not None
        assert pattern1.id == '1'
        assert pattern1.explanation == 'Use correct mode'
        assert pattern1.context == 'Hardware configuration'
        assert pattern1.buggy_code == 'set_mode(WRONG)'
        assert pattern1.correct_code == 'set_mode(CORRECT)'
        assert pattern1.category == 'hardware'
        assert pattern1.severity == 'high'
        
        # Verify second pattern
        pattern2 = kb.get_pattern('2')
        assert pattern2 is not None
        assert pattern2.id == '2'
        assert pattern2.category == 'lifecycle'
        assert pattern2.severity == 'medium'
    
    finally:
        os.unlink(temp_path)


def test_error_handling_missing_file():
    """
    Test error handling for missing CSV file.
    
    Requirements: 2.5
    """
    kb = KnowledgeBase('/nonexistent/path/to/file.csv')
    
    with pytest.raises(FileNotFoundError) as exc_info:
        kb.load_patterns()
    
    assert 'Knowledge base file not found' in str(exc_info.value)


def test_error_handling_corrupted_file():
    """
    Test error handling for corrupted CSV file (missing required columns).
    
    Requirements: 2.5
    """
    # Create a CSV file with missing required columns
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['ID', 'Explanation'])  # Missing required columns
        writer.writeheader()
        writer.writerow({'ID': '1', 'Explanation': 'Test'})
        temp_path = f.name
    
    try:
        kb = KnowledgeBase(temp_path)
        
        with pytest.raises(ValueError) as exc_info:
            kb.load_patterns()
        
        assert 'missing required columns' in str(exc_info.value).lower()
    
    finally:
        os.unlink(temp_path)


def test_error_handling_invalid_csv_format():
    """
    Test error handling for invalid CSV format.
    
    Requirements: 2.5
    """
    # Create a file with invalid CSV format
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
        f.write("This is not a valid CSV file\n")
        f.write("It has no proper structure\n")
        temp_path = f.name
    
    try:
        kb = KnowledgeBase(temp_path)
        
        with pytest.raises(ValueError) as exc_info:
            kb.load_patterns()
        
        # Should raise ValueError due to missing required columns
        assert 'missing required columns' in str(exc_info.value).lower()
    
    finally:
        os.unlink(temp_path)


def test_pattern_retrieval_by_id():
    """
    Test pattern retrieval by ID.
    
    Requirements: 2.1
    """
    # Create a temporary CSV file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['ID', 'Explanation', 'Context', 'Code', 'Correct Code'])
        writer.writeheader()
        writer.writerow({
            'ID': 'test-123',
            'Explanation': 'Test pattern',
            'Context': 'Test context',
            'Code': 'buggy',
            'Correct Code': 'fixed'
        })
        temp_path = f.name
    
    try:
        kb = KnowledgeBase(temp_path)
        
        # Test retrieval of existing pattern
        pattern = kb.get_pattern('test-123')
        assert pattern is not None
        assert pattern.id == 'test-123'
        assert pattern.explanation == 'Test pattern'
        
        # Test retrieval of non-existent pattern
        pattern = kb.get_pattern('nonexistent')
        assert pattern is None
    
    finally:
        os.unlink(temp_path)


def test_get_stats():
    """
    Test getting statistics about the knowledge base.
    
    Requirements: 2.1, 2.2
    """
    # Create a temporary CSV file with multiple categories
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['ID', 'Explanation', 'Context', 'Code', 'Correct Code', 'Category'])
        writer.writeheader()
        writer.writerow({
            'ID': '1',
            'Explanation': 'Hardware bug',
            'Context': 'Test',
            'Code': 'bug',
            'Correct Code': 'fix',
            'Category': 'hardware'
        })
        writer.writerow({
            'ID': '2',
            'Explanation': 'Lifecycle bug',
            'Context': 'Test',
            'Code': 'bug',
            'Correct Code': 'fix',
            'Category': 'lifecycle'
        })
        writer.writerow({
            'ID': '3',
            'Explanation': 'Another hardware bug',
            'Context': 'Test',
            'Code': 'bug',
            'Correct Code': 'fix',
            'Category': 'hardware'
        })
        temp_path = f.name
    
    try:
        kb = KnowledgeBase(temp_path)
        stats = kb.get_stats()
        
        # Verify stats
        assert stats.pattern_count == 3
        assert stats.categories['hardware'] == 2
        assert stats.categories['lifecycle'] == 1
        assert stats.last_updated is not None
    
    finally:
        os.unlink(temp_path)


def test_add_pattern():
    """
    Test adding a new pattern to the knowledge base.
    
    Requirements: 2.2
    """
    # Create a temporary CSV file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['ID', 'Explanation', 'Context', 'Code', 'Correct Code'])
        writer.writeheader()
        writer.writerow({
            'ID': '1',
            'Explanation': 'Original pattern',
            'Context': 'Test',
            'Code': 'bug',
            'Correct Code': 'fix'
        })
        temp_path = f.name
    
    try:
        kb = KnowledgeBase(temp_path)
        kb.load_patterns()
        
        # Add a new pattern
        new_pattern = BugPattern(
            id='2',
            explanation='New pattern',
            context='New context',
            buggy_code='new_bug',
            correct_code='new_fix',
            category='test',
            severity='low'
        )
        kb.add_pattern(new_pattern)
        
        # Verify the pattern was added
        retrieved = kb.get_pattern('2')
        assert retrieved is not None
        assert retrieved.id == '2'
        assert retrieved.explanation == 'New pattern'
        
        # Verify stats reflect the new pattern
        stats = kb.get_stats()
        assert stats.pattern_count == 2
    
    finally:
        os.unlink(temp_path)


def test_rebuild_index():
    """
    Test rebuilding the pattern index.
    
    Requirements: 2.2
    """
    # Create a temporary CSV file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['ID', 'Explanation', 'Context', 'Code', 'Correct Code'])
        writer.writeheader()
        writer.writerow({
            'ID': '1',
            'Explanation': 'Pattern 1',
            'Context': 'Test',
            'Code': 'bug',
            'Correct Code': 'fix'
        })
        temp_path = f.name
    
    try:
        kb = KnowledgeBase(temp_path)
        kb.load_patterns()
        
        # Verify initial state
        assert len(kb.patterns) == 1
        
        # Modify the CSV file externally
        with open(temp_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['ID', 'Explanation', 'Context', 'Code', 'Correct Code'])
            writer.writeheader()
            writer.writerow({
                'ID': '1',
                'Explanation': 'Pattern 1',
                'Context': 'Test',
                'Code': 'bug',
                'Correct Code': 'fix'
            })
            writer.writerow({
                'ID': '2',
                'Explanation': 'Pattern 2',
                'Context': 'Test',
                'Code': 'bug2',
                'Correct Code': 'fix2'
            })
        
        # Rebuild index
        kb.rebuild_index()
        
        # Verify the index was rebuilt
        assert len(kb.patterns) == 2
        assert kb.get_pattern('2') is not None
    
    finally:
        os.unlink(temp_path)


def test_default_category_and_severity():
    """
    Test that default values are used for category and severity when not provided.
    
    Requirements: 2.1
    """
    # Create a CSV file without Category and Severity columns
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['ID', 'Explanation', 'Context', 'Code', 'Correct Code'])
        writer.writeheader()
        writer.writerow({
            'ID': '1',
            'Explanation': 'Test pattern',
            'Context': 'Test',
            'Code': 'bug',
            'Correct Code': 'fix'
        })
        temp_path = f.name
    
    try:
        kb = KnowledgeBase(temp_path)
        patterns = kb.load_patterns()
        
        # Verify default values
        pattern = patterns[0]
        assert pattern.category == 'general'
        assert pattern.severity == 'medium'
    
    finally:
        os.unlink(temp_path)


def test_empty_csv_file():
    """
    Test handling of empty CSV file (only headers).
    
    Requirements: 2.5
    """
    # Create an empty CSV file with only headers
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['ID', 'Explanation', 'Context', 'Code', 'Correct Code'])
        writer.writeheader()
        temp_path = f.name
    
    try:
        kb = KnowledgeBase(temp_path)
        patterns = kb.load_patterns()
        
        # Should successfully load with zero patterns
        assert len(patterns) == 0
        assert kb.get_stats().pattern_count == 0
    
    finally:
        os.unlink(temp_path)
