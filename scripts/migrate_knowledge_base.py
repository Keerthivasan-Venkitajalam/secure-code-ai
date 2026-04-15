#!/usr/bin/env python3
"""
Migration script for Agentic-Bug-Hunter knowledge base.

This script migrates samples.csv from Agentic-Bug-Hunter to secure-code-ai,
validates the data format, transforms data if needed, and generates a migration report.

Usage:
    python scripts/migrate_knowledge_base.py --source ../Agentic-Bug-Hunter/samples.csv --dest data/knowledge_base/samples.csv --validate
"""

import argparse
import csv
import json
import os
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional


@dataclass
class BugPattern:
    """Bug pattern data model matching the knowledge base format."""
    id: str
    explanation: str
    context: str
    buggy_code: str
    correct_code: str
    category: str = "general"
    severity: str = "medium"


@dataclass
class MigrationReport:
    """Report of migration results."""
    source_file: str
    dest_file: str
    timestamp: str
    total_patterns: int
    valid_patterns: int
    invalid_patterns: int
    skipped_patterns: int
    errors: List[str]
    warnings: List[str]
    success: bool


class KnowledgeBaseMigrator:
    """Migrates knowledge base from Agentic-Bug-Hunter to secure-code-ai."""
    
    def __init__(self, source_path: str, dest_path: str, validate: bool = True):
        """
        Initialize migrator.
        
        Args:
            source_path: Path to source samples.csv
            dest_path: Path to destination samples.csv
            validate: Whether to validate data during migration
        """
        self.source_path = Path(source_path)
        self.dest_path = Path(dest_path)
        self.validate = validate
        self.errors: List[str] = []
        self.warnings: List[str] = []
        
    def migrate(self) -> MigrationReport:
        """
        Perform migration.
        
        Returns:
            Migration report with results
        """
        print(f"Starting migration from {self.source_path} to {self.dest_path}")
        
        # Validate source file exists
        if not self.source_path.exists():
            error = f"Source file not found: {self.source_path}"
            self.errors.append(error)
            return self._create_report(0, 0, 0, 0, False)
        
        # Create destination directory if needed
        self.dest_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Read and validate source data
        patterns = self._read_source_data()
        if patterns is None:
            return self._create_report(0, 0, 0, 0, False)
        
        total_patterns = len(patterns)
        print(f"Read {total_patterns} patterns from source")
        
        # Validate patterns if requested
        valid_patterns = []
        invalid_patterns = 0
        skipped_patterns = 0
        
        for i, pattern in enumerate(patterns):
            if self.validate:
                is_valid, validation_errors = self._validate_pattern(pattern, i + 1)
                if not is_valid:
                    invalid_patterns += 1
                    self.errors.extend(validation_errors)
                    continue
            
            valid_patterns.append(pattern)
        
        print(f"Validated {len(valid_patterns)} patterns")
        
        # Write to destination
        success = self._write_destination_data(valid_patterns)
        
        if success:
            print(f"Successfully migrated {len(valid_patterns)} patterns to {self.dest_path}")
        else:
            print(f"Migration failed. Check errors in report.")
        
        return self._create_report(
            total_patterns,
            len(valid_patterns),
            invalid_patterns,
            skipped_patterns,
            success
        )
    
    def _read_source_data(self) -> Optional[List[BugPattern]]:
        """
        Read source CSV file.
        
        Returns:
            List of bug patterns or None if read fails
        """
        try:
            patterns = []
            with open(self.source_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                # Check required columns
                required_columns = {'ID', 'Explanation', 'Context', 'Code', 'Correct Code'}
                if not required_columns.issubset(set(reader.fieldnames or [])):
                    missing = required_columns - set(reader.fieldnames or [])
                    self.errors.append(f"Missing required columns: {missing}")
                    return None
                
                for row in reader:
                    pattern = BugPattern(
                        id=row['ID'].strip(),
                        explanation=row['Explanation'].strip(),
                        context=row['Context'].strip(),
                        buggy_code=row['Code'].strip(),
                        correct_code=row['Correct Code'].strip(),
                        category=row.get('Category', 'general').strip(),
                        severity=row.get('Severity', 'medium').strip()
                    )
                    patterns.append(pattern)
            
            return patterns
        
        except Exception as e:
            self.errors.append(f"Error reading source file: {str(e)}")
            return None
    
    def _validate_pattern(self, pattern: BugPattern, row_num: int) -> tuple[bool, List[str]]:
        """
        Validate a bug pattern.
        
        Args:
            pattern: Pattern to validate
            row_num: Row number for error reporting
            
        Returns:
            Tuple of (is_valid, list of errors)
        """
        errors = []
        
        # Check ID is not empty
        if not pattern.id:
            errors.append(f"Row {row_num}: Empty ID")
        
        # Check explanation is not empty
        if not pattern.explanation:
            errors.append(f"Row {row_num}: Empty explanation")
        
        # Check context is not empty
        if not pattern.context:
            errors.append(f"Row {row_num}: Empty context")
        
        # Check buggy code is not empty
        if not pattern.buggy_code:
            errors.append(f"Row {row_num}: Empty buggy code")
        
        # Check correct code is not empty
        if not pattern.correct_code:
            errors.append(f"Row {row_num}: Empty correct code")
        
        # Validate category
        valid_categories = {'general', 'hardware', 'lifecycle', 'api', 'security', 'performance'}
        if pattern.category and pattern.category not in valid_categories:
            self.warnings.append(f"Row {row_num}: Unknown category '{pattern.category}', using 'general'")
            pattern.category = 'general'
        
        # Validate severity
        valid_severities = {'low', 'medium', 'high', 'critical'}
        if pattern.severity and pattern.severity not in valid_severities:
            self.warnings.append(f"Row {row_num}: Unknown severity '{pattern.severity}', using 'medium'")
            pattern.severity = 'medium'
        
        return len(errors) == 0, errors
    
    def _write_destination_data(self, patterns: List[BugPattern]) -> bool:
        """
        Write patterns to destination CSV file.
        
        Args:
            patterns: List of patterns to write
            
        Returns:
            True if write succeeds, False otherwise
        """
        try:
            with open(self.dest_path, 'w', encoding='utf-8', newline='') as f:
                fieldnames = ['ID', 'Explanation', 'Context', 'Code', 'Correct Code', 'Category', 'Severity']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                
                writer.writeheader()
                for pattern in patterns:
                    writer.writerow({
                        'ID': pattern.id,
                        'Explanation': pattern.explanation,
                        'Context': pattern.context,
                        'Code': pattern.buggy_code,
                        'Correct Code': pattern.correct_code,
                        'Category': pattern.category,
                        'Severity': pattern.severity
                    })
            
            return True
        
        except Exception as e:
            self.errors.append(f"Error writing destination file: {str(e)}")
            return False
    
    def _create_report(
        self,
        total: int,
        valid: int,
        invalid: int,
        skipped: int,
        success: bool
    ) -> MigrationReport:
        """Create migration report."""
        return MigrationReport(
            source_file=str(self.source_path),
            dest_file=str(self.dest_path),
            timestamp=datetime.now().isoformat(),
            total_patterns=total,
            valid_patterns=valid,
            invalid_patterns=invalid,
            skipped_patterns=skipped,
            errors=self.errors,
            warnings=self.warnings,
            success=success
        )


def save_report(report: MigrationReport, output_path: str) -> None:
    """
    Save migration report to JSON file.
    
    Args:
        report: Migration report
        output_path: Path to save report
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(asdict(report), f, indent=2)
    print(f"Report saved to {output_path}")


def print_report(report: MigrationReport) -> None:
    """
    Print migration report to console.
    
    Args:
        report: Migration report
    """
    print("\n" + "=" * 80)
    print("MIGRATION REPORT")
    print("=" * 80)
    print(f"Source: {report.source_file}")
    print(f"Destination: {report.dest_file}")
    print(f"Timestamp: {report.timestamp}")
    print(f"Status: {'SUCCESS' if report.success else 'FAILED'}")
    print("-" * 80)
    print(f"Total patterns: {report.total_patterns}")
    print(f"Valid patterns: {report.valid_patterns}")
    print(f"Invalid patterns: {report.invalid_patterns}")
    print(f"Skipped patterns: {report.skipped_patterns}")
    
    if report.warnings:
        print("-" * 80)
        print(f"Warnings ({len(report.warnings)}):")
        for warning in report.warnings[:10]:  # Show first 10
            print(f"  - {warning}")
        if len(report.warnings) > 10:
            print(f"  ... and {len(report.warnings) - 10} more")
    
    if report.errors:
        print("-" * 80)
        print(f"Errors ({len(report.errors)}):")
        for error in report.errors[:10]:  # Show first 10
            print(f"  - {error}")
        if len(report.errors) > 10:
            print(f"  ... and {len(report.errors) - 10} more")
    
    print("=" * 80)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Migrate Agentic-Bug-Hunter knowledge base to secure-code-ai"
    )
    parser.add_argument(
        '--source',
        required=True,
        help='Path to source samples.csv'
    )
    parser.add_argument(
        '--dest',
        required=True,
        help='Path to destination samples.csv'
    )
    parser.add_argument(
        '--validate',
        action='store_true',
        default=True,
        help='Validate data during migration (default: True)'
    )
    parser.add_argument(
        '--no-validate',
        action='store_false',
        dest='validate',
        help='Skip validation during migration'
    )
    parser.add_argument(
        '--report',
        help='Path to save migration report (JSON)'
    )
    
    args = parser.parse_args()
    
    # Perform migration
    migrator = KnowledgeBaseMigrator(args.source, args.dest, args.validate)
    report = migrator.migrate()
    
    # Print report
    print_report(report)
    
    # Save report if requested
    if args.report:
        save_report(report, args.report)
    
    # Exit with appropriate code
    sys.exit(0 if report.success else 1)


if __name__ == '__main__':
    main()
