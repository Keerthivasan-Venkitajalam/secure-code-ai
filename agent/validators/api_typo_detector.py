"""
API typo detector using fuzzy string matching.

This module provides detection of potential API name typos by comparing
found API calls against a list of known API names using fuzzy matching.
"""

import re
from dataclasses import dataclass
from typing import List, Set, Tuple
from rapidfuzz import fuzz, process


@dataclass
class APITypoSuggestion:
    """Represents a potential API typo with suggestions.
    
    Attributes:
        location: Line number where potential typo occurs
        found_api: The API name found in the code
        suggested_apis: List of suggested correct API names
        similarity_scores: List of similarity scores for each suggestion (0-1)
        message: Human-readable description
    """
    location: str
    found_api: str
    suggested_apis: List[str]
    similarity_scores: List[float]
    message: str


class APITypoDetector:
    """Detects potential API name typos using fuzzy matching.
    
    This detector:
    - Identifies API calls in code
    - Compares them against known API names
    - Suggests corrections when similarity > 0.8
    - Returns top 3 suggestions per typo
    """
    
    # Pattern for detecting function calls (potential API calls)
    API_CALL_PATTERN = re.compile(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\(')
    
    # Minimum similarity threshold for suggestions
    MIN_SIMILARITY = 0.8
    
    # Maximum number of suggestions to return
    MAX_SUGGESTIONS = 3
    
    def __init__(self, known_apis: List[str]):
        """Initialize API typo detector with known API names.
        
        Args:
            known_apis: List of known/correct API names
        """
        self.known_apis = set(known_apis)
    
    def detect_typos(self, code: str) -> List[APITypoSuggestion]:
        """Detect potential API name typos in code.
        
        Args:
            code: Source code to analyze
            
        Returns:
            List of APITypoSuggestion objects for potential typos
        """
        suggestions = []
        
        # Find all API calls in code
        api_calls = self._find_api_calls(code)
        
        # Check each API call for potential typos
        for line_num, api_name in api_calls:
            # Skip if API name is in known APIs (exact match)
            if api_name in self.known_apis:
                continue
            
            # Find similar API names
            similar_apis = self._find_similar_apis(api_name)
            
            if similar_apis:
                suggested_names = [name for name, _ in similar_apis]
                scores = [score / 100.0 for _, score in similar_apis]  # Convert to 0-1 range
                
                suggestions.append(APITypoSuggestion(
                    location=str(line_num),
                    found_api=api_name,
                    suggested_apis=suggested_names,
                    similarity_scores=scores,
                    message=f"Possible typo '{api_name}' at line {line_num}. Did you mean: {', '.join(suggested_names[:3])}?"
                ))
        
        return suggestions
    
    def _find_api_calls(self, code: str) -> List[Tuple[int, str]]:
        """Find all API calls in code with line numbers.
        
        Args:
            code: Source code to search
            
        Returns:
            List of (line_number, api_name) tuples
        """
        api_calls = []
        lines = code.split('\n')
        
        for line_num, line in enumerate(lines, start=1):
            matches = self.API_CALL_PATTERN.finditer(line)
            for match in matches:
                api_name = match.group(1)
                api_calls.append((line_num, api_name))
        
        return api_calls
    
    def _find_similar_apis(self, api_name: str) -> List[Tuple[str, float]]:
        """Find similar API names using fuzzy matching.
        
        Args:
            api_name: API name to find matches for
            
        Returns:
            List of (api_name, similarity_score) tuples, sorted by score descending
        """
        # Use rapidfuzz to find similar strings
        matches = process.extract(
            api_name,
            self.known_apis,
            scorer=fuzz.ratio,
            limit=self.MAX_SUGGESTIONS
        )
        
        # Filter by minimum similarity and convert to list
        similar = [
            (name, score)
            for name, score, _ in matches
            if score >= self.MIN_SIMILARITY * 100  # rapidfuzz uses 0-100 scale
        ]
        
        return similar
