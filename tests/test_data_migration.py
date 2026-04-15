"""
Property tests for data migration from Agentic-Bug-Hunter to secure-code-ai.

Feature: agentic-bug-hunter-integration
Property 15: Data Migration Preservation

Validates: Requirements 15.2
"""

import pytest
import csv
import os
from pathlib import Path
from hypothesis import given, strategies as st, settings, HealthCheck


# Define paths - relative to workspace root
WORKSPACE_ROOT = Path(__file__).parent.parent.parent
SOURCE_PATH = WORKSPACE_ROOT / "Agentic-Bug-Hunter" / "samples.csv"
DEST_PATH = WORKSPACE_ROOT / "secure-code-ai" / "data" / "knowledge_base" / "samples.csv"


class TestDataMigrationPreservation:
    """
    Property 15: Data Migration Preservation
    
    For any bug pattern in the original samples.csv, after migration,
    the pattern should exist in the new knowledge base with identical
    explanation, context, buggy_code, and correct_code fields.
    
    Validates: Requirements 15.2
    """
    
    def load_csv_as_dict(self, file_path: Path) -> dict:
        """Load CSV file and return as dictionary keyed by ID."""
        patterns = {}
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                patterns[row['ID']] = {
                    'Explanation': row['Explanation'],
                    'Context': row['Context'],
                    'Code': row['Code'],
                    'Correct Code': row['Correct Code']
                }
        return patterns
    
    @pytest.mark.skipif(
        not SOURCE_PATH.exists() or not DEST_PATH.exists(),
        reason="Source or destination file not found"
    )
    def test_all_patterns_migrated(self):
        """
        Test that all patterns from source exist in destination.
        
        Property: For all patterns in source, pattern exists in destination.
        """
        source_patterns = self.load_csv_as_dict(SOURCE_PATH)
        dest_patterns = self.load_csv_as_dict(DEST_PATH)
        
        # Check all source IDs exist in destination
        source_ids = set(source_patterns.keys())
        dest_ids = set(dest_patterns.keys())
        
        missing_ids = source_ids - dest_ids
        assert len(missing_ids) == 0, f"Missing pattern IDs in destination: {missing_ids}"
    
    @pytest.mark.skipif(
        not SOURCE_PATH.exists() or not DEST_PATH.exists(),
        reason="Source or destination file not found"
    )
    def test_pattern_fields_preserved(self):
        """
        Test that all fields are preserved exactly during migration.
        
        Property: For all patterns, explanation, context, code, and correct_code
        fields are identical between source and destination.
        """
        source_patterns = self.load_csv_as_dict(SOURCE_PATH)
        dest_patterns = self.load_csv_as_dict(DEST_PATH)
        
        mismatches = []
        
        for pattern_id, source_data in source_patterns.items():
            if pattern_id not in dest_patterns:
                mismatches.append(f"Pattern {pattern_id} missing in destination")
                continue
            
            dest_data = dest_patterns[pattern_id]
            
            # Check each field
            for field in ['Explanation', 'Context', 'Code', 'Correct Code']:
                source_value = source_data[field].strip()
                dest_value = dest_data[field].strip()
                
                if source_value != dest_value:
                    mismatches.append(
                        f"Pattern {pattern_id}, field '{field}' mismatch:\n"
                        f"  Source: {source_value[:100]}...\n"
                        f"  Dest:   {dest_value[:100]}..."
                    )
        
        assert len(mismatches) == 0, f"Field mismatches found:\n" + "\n".join(mismatches)
    
    @pytest.mark.skipif(
        not SOURCE_PATH.exists() or not DEST_PATH.exists(),
        reason="Source or destination file not found"
    )
    def test_pattern_count_preserved(self):
        """
        Test that the total number of patterns is preserved.
        
        Property: The count of patterns in destination equals count in source.
        """
        source_patterns = self.load_csv_as_dict(SOURCE_PATH)
        dest_patterns = self.load_csv_as_dict(DEST_PATH)
        
        assert len(source_patterns) == len(dest_patterns), (
            f"Pattern count mismatch: source has {len(source_patterns)}, "
            f"destination has {len(dest_patterns)}"
        )
    
    @pytest.mark.skipif(
        not SOURCE_PATH.exists() or not DEST_PATH.exists(),
        reason="Source or destination file not found"
    )
    def test_no_extra_patterns_in_destination(self):
        """
        Test that destination doesn't have patterns not in source.
        
        Property: All pattern IDs in destination exist in source.
        """
        source_patterns = self.load_csv_as_dict(SOURCE_PATH)
        dest_patterns = self.load_csv_as_dict(DEST_PATH)
        
        source_ids = set(source_patterns.keys())
        dest_ids = set(dest_patterns.keys())
        
        extra_ids = dest_ids - source_ids
        assert len(extra_ids) == 0, f"Extra pattern IDs in destination: {extra_ids}"
    
    @pytest.mark.skipif(
        not SOURCE_PATH.exists() or not DEST_PATH.exists(),
        reason="Source or destination file not found"
    )
    def test_csv_structure_preserved(self):
        """
        Test that CSV structure (columns) is preserved.
        
        Property: Destination CSV has same columns as source CSV.
        """
        with open(SOURCE_PATH, 'r', encoding='utf-8') as f:
            source_reader = csv.DictReader(f)
            source_columns = source_reader.fieldnames
        
        with open(DEST_PATH, 'r', encoding='utf-8') as f:
            dest_reader = csv.DictReader(f)
            dest_columns = dest_reader.fieldnames
        
        assert source_columns == dest_columns, (
            f"Column mismatch:\n"
            f"  Source: {source_columns}\n"
            f"  Dest:   {dest_columns}"
        )
    
    @pytest.mark.skipif(
        not SOURCE_PATH.exists() or not DEST_PATH.exists(),
        reason="Source or destination file not found"
    )
    @settings(max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(pattern_id=st.sampled_from([
        "16", "32", "25", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"
    ]))
    def test_individual_pattern_preservation(self, pattern_id: str):
        """
        Property-based test: For any pattern ID, if it exists in source,
        it must exist in destination with identical fields.
        
        Feature: agentic-bug-hunter-integration
        Property 15: Data Migration Preservation
        
        Validates: Requirements 15.2
        """
        source_patterns = self.load_csv_as_dict(SOURCE_PATH)
        dest_patterns = self.load_csv_as_dict(DEST_PATH)
        
        # If pattern exists in source, it must exist in destination
        if pattern_id in source_patterns:
            assert pattern_id in dest_patterns, (
                f"Pattern {pattern_id} exists in source but not in destination"
            )
            
            # All fields must match
            source_data = source_patterns[pattern_id]
            dest_data = dest_patterns[pattern_id]
            
            for field in ['Explanation', 'Context', 'Code', 'Correct Code']:
                assert source_data[field].strip() == dest_data[field].strip(), (
                    f"Pattern {pattern_id}, field '{field}' mismatch"
                )


class TestDataMigrationIntegrity:
    """Test data integrity after migration."""
    
    @pytest.mark.skipif(
        not DEST_PATH.exists(),
        reason="Destination file not found"
    )
    def test_destination_file_readable(self):
        """Test that destination file is readable and valid CSV."""
        try:
            with open(DEST_PATH, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                assert len(rows) > 0, "Destination file is empty"
        except Exception as e:
            pytest.fail(f"Failed to read destination file: {e}")
    
    @pytest.mark.skipif(
        not DEST_PATH.exists(),
        reason="Destination file not found"
    )
    def test_no_empty_required_fields(self):
        """Test that required fields are not empty."""
        with open(DEST_PATH, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader, start=1):
                assert row['ID'].strip(), f"Row {i}: ID is empty"
                assert row['Explanation'].strip(), f"Row {i}: Explanation is empty"
                assert row['Code'].strip(), f"Row {i}: Code is empty"
                assert row['Correct Code'].strip(), f"Row {i}: Correct Code is empty"
    
    @pytest.mark.skipif(
        not DEST_PATH.exists(),
        reason="Destination file not found"
    )
    def test_unique_pattern_ids(self):
        """Test that all pattern IDs are unique."""
        with open(DEST_PATH, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            ids = [row['ID'] for row in reader]
        
        duplicates = [id for id in ids if ids.count(id) > 1]
        assert len(set(duplicates)) == 0, f"Duplicate IDs found: {set(duplicates)}"
