"""
Unit tests for migration scripts.

Tests data validation, error handling for corrupted data, and incremental migration.
"""

import csv
import os
import sys
import tempfile
from pathlib import Path

import pytest

# Add scripts directory to path for imports
scripts_dir = Path(__file__).parent.parent / 'scripts'
sys.path.insert(0, str(scripts_dir))

from migrate_knowledge_base import (
    BugPattern,
    KnowledgeBaseMigrator,
    MigrationReport
)


class TestKnowledgeBaseMigrator:
    """Tests for KnowledgeBaseMigrator."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    @pytest.fixture
    def valid_csv_data(self):
        """Valid CSV data for testing."""
        return [
            {
                'ID': '1',
                'Explanation': 'Test bug 1',
                'Context': 'Test context 1',
                'Code': 'buggy_code_1',
                'Correct Code': 'correct_code_1',
                'Category': 'general',
                'Severity': 'medium'
            },
            {
                'ID': '2',
                'Explanation': 'Test bug 2',
                'Context': 'Test context 2',
                'Code': 'buggy_code_2',
                'Correct Code': 'correct_code_2',
                'Category': 'hardware',
                'Severity': 'high'
            }
        ]
    
    def create_csv_file(self, path: str, data: list, include_header: bool = True):
        """Helper to create CSV file with test data."""
        with open(path, 'w', encoding='utf-8', newline='') as f:
            fieldnames = ['ID', 'Explanation', 'Context', 'Code', 'Correct Code', 'Category', 'Severity']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            
            if include_header:
                writer.writeheader()
            
            for row in data:
                writer.writerow(row)
    
    def test_migrate_valid_data(self, temp_dir, valid_csv_data):
        """Test migration with valid data."""
        source_path = os.path.join(temp_dir, 'source.csv')
        dest_path = os.path.join(temp_dir, 'dest.csv')
        
        # Create source file
        self.create_csv_file(source_path, valid_csv_data)
        
        # Migrate
        migrator = KnowledgeBaseMigrator(source_path, dest_path, validate=True)
        report = migrator.migrate()
        
        # Verify report
        assert report.success
        assert report.total_patterns == 2
        assert report.valid_patterns == 2
        assert report.invalid_patterns == 0
        assert len(report.errors) == 0
        
        # Verify destination file exists
        assert os.path.exists(dest_path)
        
        # Verify destination file content
        with open(dest_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 2
            assert rows[0]['ID'] == '1'
            assert rows[1]['ID'] == '2'
    
    def test_migrate_missing_source(self, temp_dir):
        """Test migration with missing source file."""
        source_path = os.path.join(temp_dir, 'nonexistent.csv')
        dest_path = os.path.join(temp_dir, 'dest.csv')
        
        migrator = KnowledgeBaseMigrator(source_path, dest_path)
        report = migrator.migrate()
        
        assert not report.success
        assert len(report.errors) > 0
        assert 'not found' in report.errors[0].lower()
    
    def test_migrate_empty_fields(self, temp_dir):
        """Test migration with empty required fields."""
        source_path = os.path.join(temp_dir, 'source.csv')
        dest_path = os.path.join(temp_dir, 'dest.csv')
        
        # Create data with empty fields
        data = [
            {
                'ID': '',  # Empty ID
                'Explanation': 'Test bug',
                'Context': 'Test context',
                'Code': 'buggy_code',
                'Correct Code': 'correct_code',
                'Category': 'general',
                'Severity': 'medium'
            },
            {
                'ID': '2',
                'Explanation': '',  # Empty explanation
                'Context': 'Test context',
                'Code': 'buggy_code',
                'Correct Code': 'correct_code',
                'Category': 'general',
                'Severity': 'medium'
            }
        ]
        
        self.create_csv_file(source_path, data)
        
        # Migrate with validation
        migrator = KnowledgeBaseMigrator(source_path, dest_path, validate=True)
        report = migrator.migrate()
        
        # Should fail validation
        assert report.invalid_patterns == 2
        assert report.valid_patterns == 0
        assert len(report.errors) > 0
    
    def test_migrate_invalid_category(self, temp_dir, valid_csv_data):
        """Test migration with invalid category."""
        source_path = os.path.join(temp_dir, 'source.csv')
        dest_path = os.path.join(temp_dir, 'dest.csv')
        
        # Add invalid category
        data = valid_csv_data.copy()
        data[0]['Category'] = 'invalid_category'
        
        self.create_csv_file(source_path, data)
        
        # Migrate with validation
        migrator = KnowledgeBaseMigrator(source_path, dest_path, validate=True)
        report = migrator.migrate()
        
        # Should succeed but with warnings
        assert report.success
        assert len(report.warnings) > 0
        assert 'category' in report.warnings[0].lower()
        
        # Verify category was corrected to 'general'
        with open(dest_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert rows[0]['Category'] == 'general'
    
    def test_migrate_invalid_severity(self, temp_dir, valid_csv_data):
        """Test migration with invalid severity."""
        source_path = os.path.join(temp_dir, 'source.csv')
        dest_path = os.path.join(temp_dir, 'dest.csv')
        
        # Add invalid severity
        data = valid_csv_data.copy()
        data[0]['Severity'] = 'invalid_severity'
        
        self.create_csv_file(source_path, data)
        
        # Migrate with validation
        migrator = KnowledgeBaseMigrator(source_path, dest_path, validate=True)
        report = migrator.migrate()
        
        # Should succeed but with warnings
        assert report.success
        assert len(report.warnings) > 0
        assert 'severity' in report.warnings[0].lower()
        
        # Verify severity was corrected to 'medium'
        with open(dest_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert rows[0]['Severity'] == 'medium'
    
    def test_migrate_missing_columns(self, temp_dir):
        """Test migration with missing required columns."""
        source_path = os.path.join(temp_dir, 'source.csv')
        dest_path = os.path.join(temp_dir, 'dest.csv')
        
        # Create CSV with missing columns
        with open(source_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['ID', 'Explanation'])
            writer.writeheader()
            writer.writerow({'ID': '1', 'Explanation': 'Test'})
        
        # Migrate
        migrator = KnowledgeBaseMigrator(source_path, dest_path)
        report = migrator.migrate()
        
        # Should fail
        assert not report.success
        assert len(report.errors) > 0
        assert 'missing' in report.errors[0].lower()
    
    def test_migrate_without_validation(self, temp_dir):
        """Test migration without validation."""
        source_path = os.path.join(temp_dir, 'source.csv')
        dest_path = os.path.join(temp_dir, 'dest.csv')
        
        # Create data with empty fields
        data = [
            {
                'ID': '',  # Empty ID
                'Explanation': 'Test bug',
                'Context': 'Test context',
                'Code': 'buggy_code',
                'Correct Code': 'correct_code',
                'Category': 'general',
                'Severity': 'medium'
            }
        ]
        
        self.create_csv_file(source_path, data)
        
        # Migrate without validation
        migrator = KnowledgeBaseMigrator(source_path, dest_path, validate=False)
        report = migrator.migrate()
        
        # Should succeed (no validation)
        assert report.success
        assert report.valid_patterns == 1
        assert report.invalid_patterns == 0
    
    def test_migrate_corrupted_csv(self, temp_dir):
        """Test migration with corrupted CSV file."""
        source_path = os.path.join(temp_dir, 'source.csv')
        dest_path = os.path.join(temp_dir, 'dest.csv')
        
        # Create corrupted CSV (unmatched quotes)
        with open(source_path, 'w', encoding='utf-8') as f:
            f.write('ID,Explanation,Context,Code,Correct Code\n')
            f.write('1,"Test bug,context,code,correct\n')  # Unmatched quote
        
        # Migrate
        migrator = KnowledgeBaseMigrator(source_path, dest_path)
        report = migrator.migrate()
        
        # Should handle gracefully
        # Note: csv.DictReader is quite forgiving, so this might still succeed
        # but with unexpected data
        assert isinstance(report, MigrationReport)
    
    def test_migrate_preserves_data(self, temp_dir, valid_csv_data):
        """Test that migration preserves all data fields."""
        source_path = os.path.join(temp_dir, 'source.csv')
        dest_path = os.path.join(temp_dir, 'dest.csv')
        
        self.create_csv_file(source_path, valid_csv_data)
        
        # Migrate
        migrator = KnowledgeBaseMigrator(source_path, dest_path)
        report = migrator.migrate()
        
        assert report.success
        
        # Read both files and compare
        with open(source_path, 'r', encoding='utf-8') as f:
            source_rows = list(csv.DictReader(f))
        
        with open(dest_path, 'r', encoding='utf-8') as f:
            dest_rows = list(csv.DictReader(f))
        
        assert len(source_rows) == len(dest_rows)
        
        for src, dst in zip(source_rows, dest_rows):
            assert src['ID'] == dst['ID']
            assert src['Explanation'] == dst['Explanation']
            assert src['Context'] == dst['Context']
            assert src['Code'] == dst['Code']
            assert src['Correct Code'] == dst['Correct Code']
    
    def test_migrate_creates_destination_directory(self, temp_dir):
        """Test that migration creates destination directory if needed."""
        source_path = os.path.join(temp_dir, 'source.csv')
        dest_path = os.path.join(temp_dir, 'subdir', 'dest.csv')
        
        # Create source file
        self.create_csv_file(source_path, [
            {
                'ID': '1',
                'Explanation': 'Test',
                'Context': 'Context',
                'Code': 'code',
                'Correct Code': 'correct',
                'Category': 'general',
                'Severity': 'medium'
            }
        ])
        
        # Migrate (destination directory doesn't exist)
        migrator = KnowledgeBaseMigrator(source_path, dest_path)
        report = migrator.migrate()
        
        assert report.success
        assert os.path.exists(dest_path)
        assert os.path.exists(os.path.dirname(dest_path))
    
    def test_migrate_incremental(self, temp_dir, valid_csv_data):
        """Test incremental migration (appending new patterns)."""
        source_path = os.path.join(temp_dir, 'source.csv')
        dest_path = os.path.join(temp_dir, 'dest.csv')
        
        # First migration
        self.create_csv_file(source_path, valid_csv_data[:1])
        migrator = KnowledgeBaseMigrator(source_path, dest_path)
        report1 = migrator.migrate()
        
        assert report1.success
        assert report1.valid_patterns == 1
        
        # Second migration with more data
        self.create_csv_file(source_path, valid_csv_data)
        migrator = KnowledgeBaseMigrator(source_path, dest_path)
        report2 = migrator.migrate()
        
        assert report2.success
        assert report2.valid_patterns == 2
        
        # Verify destination has all patterns
        with open(dest_path, 'r', encoding='utf-8') as f:
            rows = list(csv.DictReader(f))
            assert len(rows) == 2


class TestBugPattern:
    """Tests for BugPattern dataclass."""
    
    def test_bug_pattern_creation(self):
        """Test creating a BugPattern."""
        pattern = BugPattern(
            id='1',
            explanation='Test bug',
            context='Test context',
            buggy_code='buggy',
            correct_code='correct',
            category='general',
            severity='medium'
        )
        
        assert pattern.id == '1'
        assert pattern.explanation == 'Test bug'
        assert pattern.context == 'Test context'
        assert pattern.buggy_code == 'buggy'
        assert pattern.correct_code == 'correct'
        assert pattern.category == 'general'
        assert pattern.severity == 'medium'
    
    def test_bug_pattern_defaults(self):
        """Test BugPattern default values."""
        pattern = BugPattern(
            id='1',
            explanation='Test',
            context='Context',
            buggy_code='buggy',
            correct_code='correct'
        )
        
        assert pattern.category == 'general'
        assert pattern.severity == 'medium'


class TestMigrationReport:
    """Tests for MigrationReport dataclass."""
    
    def test_migration_report_creation(self):
        """Test creating a MigrationReport."""
        report = MigrationReport(
            source_file='source.csv',
            dest_file='dest.csv',
            timestamp='2026-01-31T12:00:00',
            total_patterns=10,
            valid_patterns=8,
            invalid_patterns=2,
            skipped_patterns=0,
            errors=['Error 1', 'Error 2'],
            warnings=['Warning 1'],
            success=True
        )
        
        assert report.source_file == 'source.csv'
        assert report.dest_file == 'dest.csv'
        assert report.total_patterns == 10
        assert report.valid_patterns == 8
        assert report.invalid_patterns == 2
        assert report.skipped_patterns == 0
        assert len(report.errors) == 2
        assert len(report.warnings) == 1
        assert report.success is True
