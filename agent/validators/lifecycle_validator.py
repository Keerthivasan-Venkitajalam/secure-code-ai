"""
Lifecycle validator for checking RDI_BEGIN/RDI_END ordering.

This module provides validation for RDI lifecycle calls to ensure proper
ordering and matching of BEGIN/END pairs.
"""

import re
from dataclasses import dataclass
from typing import List, Tuple, Optional


@dataclass
class LifecycleViolation:
    """Represents a lifecycle ordering violation.
    
    Attributes:
        location: Line number where violation occurs
        issue: Type of issue (e.g., "missing_end", "wrong_order", "missing_begin")
        begin_line: Line number with RDI_BEGIN (if present)
        end_line: Line number with RDI_END (if present)
        message: Human-readable description of the violation
    """
    location: str
    issue: str
    begin_line: int
    end_line: int
    message: str


class LifecycleValidator:
    """Validates code for RDI lifecycle ordering issues.
    
    This validator checks for:
    - RDI_END appearing before RDI_BEGIN (wrong order)
    - RDI_BEGIN without matching RDI_END (missing end)
    - RDI_END without matching RDI_BEGIN (missing begin)
    
    The validator parses code for RDI_BEGIN and RDI_END calls and verifies
    their ordering and pairing.
    """
    
    # Patterns for detecting lifecycle calls
    BEGIN_PATTERN = re.compile(r'RDI_BEGIN\s*\(', re.IGNORECASE)
    END_PATTERN = re.compile(r'RDI_END\s*\(', re.IGNORECASE)
    
    def validate(self, code: str) -> List[LifecycleViolation]:
        """Check code for lifecycle ordering violations.
        
        Args:
            code: Source code to validate
            
        Returns:
            List of LifecycleViolation objects, empty if no violations found
        """
        violations = []
        
        # Find all BEGIN and END calls with line numbers
        begin_calls = self._find_lifecycle_calls(code, self.BEGIN_PATTERN)
        end_calls = self._find_lifecycle_calls(code, self.END_PATTERN)
        
        # Check for ordering violations
        violations.extend(self._check_ordering(begin_calls, end_calls))
        
        # Check for missing END statements
        violations.extend(self._check_missing_end(begin_calls, end_calls))
        
        # Check for missing BEGIN statements
        violations.extend(self._check_missing_begin(begin_calls, end_calls))
        
        return violations
    
    def _find_lifecycle_calls(self, code: str, pattern: re.Pattern) -> List[int]:
        """Find all lifecycle calls matching the pattern.
        
        Args:
            code: Source code to search
            pattern: Regex pattern to match
            
        Returns:
            List of line numbers where pattern matches
        """
        line_numbers = []
        lines = code.split('\n')
        
        for line_num, line in enumerate(lines, start=1):
            if pattern.search(line):
                line_numbers.append(line_num)
        
        return line_numbers
    
    def _check_ordering(
        self,
        begin_calls: List[int],
        end_calls: List[int]
    ) -> List[LifecycleViolation]:
        """Check for RDI_END appearing before RDI_BEGIN.
        
        Args:
            begin_calls: List of line numbers with RDI_BEGIN
            end_calls: List of line numbers with RDI_END
            
        Returns:
            List of ordering violations
        """
        violations = []
        
        # For each END call, check if there's a BEGIN call before it
        for end_line in end_calls:
            # Find the closest BEGIN before this END
            preceding_begins = [b for b in begin_calls if b < end_line]
            
            if not preceding_begins:
                # No BEGIN before this END - wrong order
                # Find if there's a BEGIN after this END
                following_begins = [b for b in begin_calls if b > end_line]
                
                if following_begins:
                    begin_line = following_begins[0]
                    violations.append(LifecycleViolation(
                        location=str(end_line),
                        issue="wrong_order",
                        begin_line=begin_line,
                        end_line=end_line,
                        message=f"RDI_END at line {end_line} appears before RDI_BEGIN at line {begin_line}"
                    ))
        
        return violations
    
    def _check_missing_end(
        self,
        begin_calls: List[int],
        end_calls: List[int]
    ) -> List[LifecycleViolation]:
        """Check for RDI_BEGIN without matching RDI_END.
        
        Args:
            begin_calls: List of line numbers with RDI_BEGIN
            end_calls: List of line numbers with RDI_END
            
        Returns:
            List of missing END violations
        """
        violations = []
        
        # Simple check: if there are more BEGINs than ENDs, some are missing END
        if len(begin_calls) > len(end_calls):
            # For each BEGIN, check if there's an END after it
            for begin_line in begin_calls:
                following_ends = [e for e in end_calls if e > begin_line]
                
                if not following_ends:
                    violations.append(LifecycleViolation(
                        location=str(begin_line),
                        issue="missing_end",
                        begin_line=begin_line,
                        end_line=-1,
                        message=f"RDI_BEGIN at line {begin_line} has no matching RDI_END"
                    ))
        
        return violations
    
    def _check_missing_begin(
        self,
        begin_calls: List[int],
        end_calls: List[int]
    ) -> List[LifecycleViolation]:
        """Check for RDI_END without matching RDI_BEGIN.
        
        Args:
            begin_calls: List of line numbers with RDI_BEGIN
            end_calls: List of line numbers with RDI_END
            
        Returns:
            List of missing BEGIN violations
        """
        violations = []
        
        # For each END, check if there's a BEGIN before it
        for end_line in end_calls:
            preceding_begins = [b for b in begin_calls if b < end_line]
            
            if not preceding_begins:
                # Check if there's no BEGIN at all after this END either
                following_begins = [b for b in begin_calls if b > end_line]
                
                if not following_begins:
                    violations.append(LifecycleViolation(
                        location=str(end_line),
                        issue="missing_begin",
                        begin_line=-1,
                        end_line=end_line,
                        message=f"RDI_END at line {end_line} has no matching RDI_BEGIN"
                    ))
        
        return violations
