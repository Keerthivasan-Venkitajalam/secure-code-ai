"""
Knowledge Base Manager for Agentic Bug Hunter Integration

This module manages the knowledge base of bug patterns, providing functionality
to load, query, and manage bug patterns from CSV storage.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import csv
import os
from pathlib import Path
from loguru import logger


@dataclass
class BugPattern:
    """
    Represents a bug pattern in the knowledge base.
    
    Attributes:
        id: Unique identifier for the pattern
        explanation: Description of what the bug is
        context: Additional context about when this bug occurs
        buggy_code: Example of code with the bug
        correct_code: Example of corrected code
        category: Category of the bug (e.g., "hardware", "lifecycle")
        severity: Severity level (e.g., "high", "medium", "low")
    """
    id: str
    explanation: str
    context: str
    buggy_code: str
    correct_code: str
    category: str = "general"
    severity: str = "medium"


@dataclass
class KnowledgeBaseStats:
    """Statistics about the knowledge base"""
    pattern_count: int
    categories: Dict[str, int]
    last_updated: Optional[str] = None


class KnowledgeBase:
    """
    Manages the knowledge base of bug patterns.
    
    Provides functionality to load patterns from CSV, retrieve specific patterns,
    add new patterns, and get statistics about the knowledge base.
    """
    
    def __init__(self, data_path: str):
        """
        Initialize the knowledge base.
        
        Args:
            data_path: Path to the CSV file containing bug patterns
        """
        self.data_path = data_path
        self.patterns: Dict[str, BugPattern] = {}
        self._loaded = False
    
    def load_patterns(self) -> List[BugPattern]:
        """
        Load all bug patterns from CSV storage.
        
        Returns:
            List of BugPattern objects
            
        Raises:
            FileNotFoundError: If the CSV file doesn't exist
            ValueError: If the CSV file is corrupted or has invalid format
        """
        if not os.path.exists(self.data_path):
            raise FileNotFoundError(f"Knowledge base file not found: {self.data_path}")
        
        patterns = []
        
        try:
            with open(self.data_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                # Validate required columns
                required_columns = {'ID', 'Explanation', 'Context', 'Code', 'Correct Code'}
                if not required_columns.issubset(set(reader.fieldnames or [])):
                    raise ValueError(
                        f"CSV file missing required columns. "
                        f"Expected: {required_columns}, "
                        f"Found: {set(reader.fieldnames or [])}"
                    )
                
                for row in reader:
                    try:
                        pattern = BugPattern(
                            id=str(row['ID']).strip(),
                            explanation=row['Explanation'].strip(),
                            context=row['Context'].strip(),
                            buggy_code=row['Code'].strip(),
                            correct_code=row['Correct Code'].strip(),
                            category=row.get('Category', 'general').strip(),
                            severity=row.get('Severity', 'medium').strip()
                        )
                        patterns.append(pattern)
                        self.patterns[pattern.id] = pattern
                    except KeyError as e:
                        logger.warning(f"Skipping row due to missing field: {e}")
                        continue
                    except Exception as e:
                        logger.warning(f"Error parsing row: {e}")
                        continue
            
            self._loaded = True
            logger.info(f"Loaded {len(patterns)} patterns from knowledge base")
            return patterns
            
        except csv.Error as e:
            raise ValueError(f"Error reading CSV file: {e}")
        except Exception as e:
            raise ValueError(f"Unexpected error loading knowledge base: {e}")
    
    def get_pattern(self, pattern_id: str) -> Optional[BugPattern]:
        """
        Retrieve a specific pattern by ID.
        
        Args:
            pattern_id: The unique identifier of the pattern
            
        Returns:
            BugPattern if found, None otherwise
        """
        if not self._loaded:
            self.load_patterns()
        
        return self.patterns.get(pattern_id)
    
    def get_all_patterns(self) -> List[BugPattern]:
        """
        Get all patterns from the knowledge base.
        
        Returns:
            List of all BugPattern objects
        """
        if not self._loaded:
            self.load_patterns()
        
        return list(self.patterns.values())
    
    def get_stats(self) -> KnowledgeBaseStats:
        """
        Get statistics about the knowledge base.
        
        Returns:
            KnowledgeBaseStats object with pattern count and categories
        """
        if not self._loaded:
            self.load_patterns()
        
        # Count patterns by category
        categories: Dict[str, int] = {}
        for pattern in self.patterns.values():
            category = pattern.category
            categories[category] = categories.get(category, 0) + 1
        
        # Get last modified time of the CSV file
        last_updated = None
        if os.path.exists(self.data_path):
            mtime = os.path.getmtime(self.data_path)
            from datetime import datetime
            last_updated = datetime.fromtimestamp(mtime).isoformat()
        
        return KnowledgeBaseStats(
            pattern_count=len(self.patterns),
            categories=categories,
            last_updated=last_updated
        )
    
    def add_pattern(self, pattern: BugPattern) -> None:
        """
        Add a new pattern to the knowledge base.
        
        Note: This only adds to the in-memory cache. To persist,
        call save_patterns() or rebuild the CSV file.
        
        Args:
            pattern: The BugPattern to add
        """
        if not self._loaded:
            self.load_patterns()
        
        self.patterns[pattern.id] = pattern
        logger.info(f"Added pattern {pattern.id} to knowledge base")
    
    def rebuild_index(self) -> None:
        """
        Rebuild the pattern index from storage.
        
        This reloads all patterns from the CSV file, useful after
        external modifications to the knowledge base.
        """
        self.patterns.clear()
        self._loaded = False
        self.load_patterns()
        logger.info("Knowledge base index rebuilt")
