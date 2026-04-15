"""
Tests for agent state data models.
"""

import pytest
import json
from typing import List
from dataclasses import asdict

from agent.state import (
    Vulnerability,
    SemanticVulnerability,
    SimilarPattern,
    HardwareViolation,
    LifecycleViolation,
    APITypoSuggestion,
    Contract,
    VerificationResult,
    Patch,
    AgentState,
)


class TestVulnerability:
    """Test the Vulnerability dataclass."""
    
    def test_vulnerability_creation(self):
        """Test creating a vulnerability with all fields."""
        vuln = Vulnerability(
            location="test.py:10",
            vuln_type="SQL Injection",
            cwe_id="CWE-89",
            severity="HIGH",
            description="Potential SQL injection",
            hypothesis="User input not sanitized",
            confidence=0.85
        )
        
        assert vuln.location == "test.py:10"
        assert vuln.vuln_type == "SQL Injection"
        assert vuln.cwe_id == "CWE-89"
        assert vuln.severity == "HIGH"
        assert vuln.confidence == 0.85
    
    def test_vulnerability_defaults(self):
        """Test vulnerability with default values."""
        vuln = Vulnerability(
            location="test.py:5",
            vuln_type="XSS"
        )
        
        assert vuln.cwe_id is None
        assert vuln.severity == "MEDIUM"
        assert vuln.description == ""
        assert vuln.hypothesis == ""
        assert vuln.confidence == 0.0


class TestSemanticVulnerability:
    """Test the SemanticVulnerability dataclass."""
    
    def test_semantic_vulnerability_creation(self):
        """Test creating a semantic vulnerability."""
        vuln = SemanticVulnerability(
            location="test.py:15",
            vuln_type="Buffer Overflow",
            description="Potential buffer overflow detected",
            similar_pattern_id="pattern_123",
            similarity_score=0.92,
            suggested_fix="Use bounds checking",
            severity="high",
            confidence=0.88
        )
        
        assert vuln.location == "test.py:15"
        assert vuln.vuln_type == "Buffer Overflow"
        assert vuln.similar_pattern_id == "pattern_123"
        assert vuln.similarity_score == 0.92
        assert vuln.source == "semantic_scanner"
    
    def test_semantic_vulnerability_serialization(self):
        """Test serializing semantic vulnerability to dict."""
        vuln = SemanticVulnerability(
            location="test.py:20",
            vuln_type="Race Condition",
            description="Potential race condition",
            similar_pattern_id="pattern_456",
            similarity_score=0.78,
            suggested_fix="Add mutex lock",
            severity="medium",
            confidence=0.75
        )
        
        vuln_dict = asdict(vuln)
        assert isinstance(vuln_dict, dict)
        assert vuln_dict["location"] == "test.py:20"
        assert vuln_dict["similarity_score"] == 0.78
        assert vuln_dict["source"] == "semantic_scanner"


class TestSimilarPattern:
    """Test the SimilarPattern dataclass."""
    
    def test_similar_pattern_creation(self):
        """Test creating a similar pattern."""
        pattern = SimilarPattern(
            pattern_id="pat_001",
            explanation="Missing null check",
            context="Common in pointer operations",
            buggy_code="ptr->value",
            correct_code="if (ptr) { ptr->value; }",
            similarity_score=0.85,
            category="null_pointer"
        )
        
        assert pattern.pattern_id == "pat_001"
        assert pattern.similarity_score == 0.85
        assert pattern.category == "null_pointer"
    
    def test_similar_pattern_serialization(self):
        """Test serializing similar pattern to dict."""
        pattern = SimilarPattern(
            pattern_id="pat_002",
            explanation="SQL injection",
            context="User input in query",
            buggy_code="query = 'SELECT * FROM users WHERE id=' + user_id",
            correct_code="query = 'SELECT * FROM users WHERE id=?'",
            similarity_score=0.95,
            category="injection"
        )
        
        pattern_dict = asdict(pattern)
        assert isinstance(pattern_dict, dict)
        assert pattern_dict["pattern_id"] == "pat_002"
        assert pattern_dict["category"] == "injection"


class TestHardwareViolation:
    """Test the HardwareViolation dataclass."""
    
    def test_hardware_violation_creation(self):
        """Test creating a hardware violation."""
        violation = HardwareViolation(
            location="line 42",
            rule="voltage_limit",
            actual_value=35.0,
            expected_value="<= 30V",
            severity="high",
            message="Voltage exceeds maximum limit"
        )
        
        assert violation.location == "line 42"
        assert violation.rule == "voltage_limit"
        assert violation.actual_value == 35.0
        assert violation.severity == "high"
    
    def test_hardware_violation_serialization(self):
        """Test serializing hardware violation to dict."""
        violation = HardwareViolation(
            location="line 100",
            rule="sample_count_limit",
            actual_value=10000,
            expected_value="<= 8192",
            severity="medium",
            message="Sample count exceeds limit"
        )
        
        violation_dict = asdict(violation)
        assert isinstance(violation_dict, dict)
        assert violation_dict["actual_value"] == 10000


class TestLifecycleViolation:
    """Test the LifecycleViolation dataclass."""
    
    def test_lifecycle_violation_creation(self):
        """Test creating a lifecycle violation."""
        violation = LifecycleViolation(
            location="line 50",
            issue="wrong_order",
            begin_line=55,
            end_line=45,
            message="RDI_END appears before RDI_BEGIN"
        )
        
        assert violation.location == "line 50"
        assert violation.issue == "wrong_order"
        assert violation.begin_line == 55
        assert violation.end_line == 45
    
    def test_lifecycle_violation_serialization(self):
        """Test serializing lifecycle violation to dict."""
        violation = LifecycleViolation(
            location="line 75",
            issue="missing_end",
            begin_line=70,
            end_line=-1,
            message="RDI_BEGIN without matching RDI_END"
        )
        
        violation_dict = asdict(violation)
        assert isinstance(violation_dict, dict)
        assert violation_dict["issue"] == "missing_end"


class TestAPITypoSuggestion:
    """Test the APITypoSuggestion dataclass."""
    
    def test_api_typo_suggestion_creation(self):
        """Test creating an API typo suggestion."""
        suggestion = APITypoSuggestion(
            location="line 30",
            found_api="strng_copy",
            suggested_apis=["string_copy", "str_copy", "strcpy"],
            similarity_scores=[0.95, 0.90, 0.85],
            message="Did you mean 'string_copy'?"
        )
        
        assert suggestion.location == "line 30"
        assert suggestion.found_api == "strng_copy"
        assert len(suggestion.suggested_apis) == 3
        assert len(suggestion.similarity_scores) == 3
    
    def test_api_typo_suggestion_serialization(self):
        """Test serializing API typo suggestion to dict."""
        suggestion = APITypoSuggestion(
            location="line 60",
            found_api="get_valu",
            suggested_apis=["get_value", "get_val"],
            similarity_scores=[0.92, 0.88],
            message="Did you mean 'get_value'?"
        )
        
        suggestion_dict = asdict(suggestion)
        assert isinstance(suggestion_dict, dict)
        assert suggestion_dict["found_api"] == "get_valu"
        assert len(suggestion_dict["suggested_apis"]) == 2


class TestAgentState:
    """Test the AgentState TypedDict."""
    
    def test_agent_state_initialization_basic(self):
        """Test initializing AgentState with basic fields."""
        state: AgentState = {
            "code": "def test(): pass",
            "file_path": "test.py",
            "vulnerabilities": [],
            "patches": [],
            "iteration_count": 0,
            "max_iterations": 3,
            "workflow_complete": False,
            "errors": [],
            "logs": [],
            "total_execution_time": 0.0
        }
        
        assert state["code"] == "def test(): pass"
        assert state["file_path"] == "test.py"
        assert state["iteration_count"] == 0
        assert state["workflow_complete"] is False
    
    def test_agent_state_with_semantic_fields(self):
        """Test initializing AgentState with new semantic fields."""
        semantic_vuln = SemanticVulnerability(
            location="test.py:10",
            vuln_type="Memory Leak",
            description="Potential memory leak",
            similar_pattern_id="pat_123",
            similarity_score=0.88,
            suggested_fix="Free allocated memory",
            severity="high",
            confidence=0.85
        )
        
        pattern = SimilarPattern(
            pattern_id="pat_123",
            explanation="Memory not freed",
            context="Common in C code",
            buggy_code="malloc(size)",
            correct_code="ptr = malloc(size); free(ptr);",
            similarity_score=0.88,
            category="memory"
        )
        
        state: AgentState = {
            "code": "void test() { malloc(100); }",
            "file_path": "test.c",
            "vulnerabilities": [],
            "semantic_vulnerabilities": [semantic_vuln],
            "similar_patterns": [pattern],
            "hardware_violations": [],
            "lifecycle_violations": [],
            "api_typo_suggestions": [],
            "patches": [],
            "iteration_count": 0,
            "max_iterations": 3,
            "workflow_complete": False,
            "errors": [],
            "logs": [],
            "total_execution_time": 0.0
        }
        
        assert len(state["semantic_vulnerabilities"]) == 1
        assert len(state["similar_patterns"]) == 1
        assert state["semantic_vulnerabilities"][0].vuln_type == "Memory Leak"
        assert state["similar_patterns"][0].pattern_id == "pat_123"
    
    def test_agent_state_with_validator_fields(self):
        """Test initializing AgentState with validator fields."""
        hw_violation = HardwareViolation(
            location="line 42",
            rule="voltage_limit",
            actual_value=35.0,
            expected_value="<= 30V",
            severity="high",
            message="Voltage exceeds limit"
        )
        
        lc_violation = LifecycleViolation(
            location="line 50",
            issue="wrong_order",
            begin_line=55,
            end_line=45,
            message="Wrong order"
        )
        
        api_suggestion = APITypoSuggestion(
            location="line 30",
            found_api="strng_copy",
            suggested_apis=["string_copy"],
            similarity_scores=[0.95],
            message="Did you mean 'string_copy'?"
        )
        
        state: AgentState = {
            "code": "test code",
            "file_path": "test.py",
            "vulnerabilities": [],
            "semantic_vulnerabilities": [],
            "similar_patterns": [],
            "hardware_violations": [hw_violation],
            "lifecycle_violations": [lc_violation],
            "api_typo_suggestions": [api_suggestion],
            "patches": [],
            "iteration_count": 0,
            "max_iterations": 3,
            "workflow_complete": False,
            "errors": [],
            "logs": [],
            "total_execution_time": 0.0
        }
        
        assert len(state["hardware_violations"]) == 1
        assert len(state["lifecycle_violations"]) == 1
        assert len(state["api_typo_suggestions"]) == 1
        assert state["hardware_violations"][0].rule == "voltage_limit"
        assert state["lifecycle_violations"][0].issue == "wrong_order"
        assert state["api_typo_suggestions"][0].found_api == "strng_copy"
    
    def test_agent_state_serialization(self):
        """Test serializing AgentState to JSON."""
        semantic_vuln = SemanticVulnerability(
            location="test.py:10",
            vuln_type="SQL Injection",
            description="Potential SQL injection",
            similar_pattern_id="pat_001",
            similarity_score=0.90,
            suggested_fix="Use parameterized queries",
            severity="high",
            confidence=0.88
        )
        
        state: AgentState = {
            "code": "SELECT * FROM users",
            "file_path": "test.py",
            "vulnerabilities": [],
            "semantic_vulnerabilities": [semantic_vuln],
            "similar_patterns": [],
            "hardware_violations": [],
            "lifecycle_violations": [],
            "api_typo_suggestions": [],
            "patches": [],
            "iteration_count": 0,
            "max_iterations": 3,
            "workflow_complete": False,
            "errors": [],
            "logs": [],
            "total_execution_time": 0.0
        }
        
        # Convert semantic vulnerabilities to dicts for JSON serialization
        state_dict = dict(state)
        state_dict["semantic_vulnerabilities"] = [
            asdict(v) for v in state_dict["semantic_vulnerabilities"]
        ]
        
        # Should be JSON serializable
        json_str = json.dumps(state_dict)
        assert isinstance(json_str, str)
        
        # Should be deserializable
        deserialized = json.loads(json_str)
        assert deserialized["code"] == "SELECT * FROM users"
        assert len(deserialized["semantic_vulnerabilities"]) == 1
        assert deserialized["semantic_vulnerabilities"][0]["vuln_type"] == "SQL Injection"
    
    def test_agent_state_partial_initialization(self):
        """Test that AgentState allows partial initialization (total=False)."""
        # Should be able to create state with only some fields
        state: AgentState = {
            "code": "test",
            "file_path": "test.py"
        }
        
        assert state["code"] == "test"
        assert state["file_path"] == "test.py"
        # Other fields are optional and not required
    
    def test_agent_state_all_new_fields_optional(self):
        """Test that all new semantic fields are optional."""
        # Should work without any semantic fields
        state: AgentState = {
            "code": "test",
            "file_path": "test.py",
            "vulnerabilities": [],
            "patches": [],
            "iteration_count": 0,
            "max_iterations": 3,
            "workflow_complete": False,
            "errors": [],
            "logs": [],
            "total_execution_time": 0.0
        }
        
        # Should not raise any errors
        assert "code" in state
        
        # New fields should be optional
        assert "semantic_vulnerabilities" not in state
        assert "similar_patterns" not in state
        assert "hardware_violations" not in state
        assert "lifecycle_violations" not in state
        assert "api_typo_suggestions" not in state


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
