"""
Unit tests for workflow orchestrator.
Tests orchestrator initialization, workflow execution, and state conversion.
"""

import pytest
import asyncio
from unittest.mock import Mock, MagicMock, patch

from api.orchestrator import (
    WorkflowOrchestrator,
    get_orchestrator,
    initialize_orchestrator
)
from api.models import AnalyzeResponse
from agent.state import AgentState, Vulnerability, Patch, VerificationResult


class TestOrchestratorInitialization:
    """Test WorkflowOrchestrator initialization."""
    
    def test_orchestrator_creation(self):
        """Test orchestrator can be created."""
        orchestrator = WorkflowOrchestrator()
        
        assert orchestrator is not None
        assert orchestrator.is_initialized() is False
    
    def test_orchestrator_with_vllm_client(self):
        """Test orchestrator can be created with vLLM client."""
        mock_client = Mock()
        orchestrator = WorkflowOrchestrator(vllm_client=mock_client)
        
        assert orchestrator.vllm_client is mock_client
        assert orchestrator.is_initialized() is False
    
    @patch('api.orchestrator.create_workflow')
    @patch('api.orchestrator.ScannerAgent')
    @patch('api.orchestrator.SpeculatorAgent')
    @patch('api.orchestrator.SymBotAgent')
    @patch('api.orchestrator.PatcherAgent')
    def test_orchestrator_initialize(
        self,
        mock_patcher,
        mock_symbot,
        mock_speculator,
        mock_scanner,
        mock_create_workflow
    ):
        """Test orchestrator initialization."""
        # Setup mocks
        mock_workflow = Mock()
        mock_create_workflow.return_value = mock_workflow
        
        orchestrator = WorkflowOrchestrator()
        orchestrator.initialize()
        
        assert orchestrator.is_initialized() is True
        mock_scanner.assert_called_once()
        mock_speculator.assert_called_once()
        mock_symbot.assert_called_once()
        mock_patcher.assert_called_once()
        mock_create_workflow.assert_called_once()
    
    @patch('api.orchestrator.create_workflow')
    @patch('api.orchestrator.ScannerAgent')
    def test_orchestrator_initialize_idempotent(
        self,
        mock_scanner,
        mock_create_workflow
    ):
        """Test initialize() is idempotent."""
        mock_workflow = Mock()
        mock_create_workflow.return_value = mock_workflow
        
        orchestrator = WorkflowOrchestrator()
        orchestrator.initialize()
        orchestrator.initialize()  # Call again
        
        # Should only initialize once
        assert mock_scanner.call_count == 1
        assert mock_create_workflow.call_count == 1


class TestOrchestratorStateConversion:
    """Test state conversion methods."""
    
    def test_create_initial_state(self):
        """Test _create_initial_state creates correct state."""
        orchestrator = WorkflowOrchestrator()
        
        state = orchestrator._create_initial_state(
            code="print('hello')",
            file_path="test.py",
            max_iterations=5
        )
        
        assert state["code"] == "print('hello')"
        assert state["file_path"] == "test.py"
        assert state["max_iterations"] == 5
        assert state["iteration_count"] == 0
        assert state["vulnerabilities"] == []
        assert state["patches"] == []
        assert state["workflow_complete"] is False
    
    def test_state_to_response_empty(self):
        """Test _state_to_response with empty state."""
        orchestrator = WorkflowOrchestrator()
        
        state: AgentState = {
            "code": "test",
            "file_path": "test.py",
            "vulnerabilities": [],
            "patches": [],
            "errors": [],
            "logs": [],
            "workflow_complete": False
        }
        
        response = orchestrator._state_to_response(
            state=state,
            analysis_id="test-123",
            execution_time=1.5
        )
        
        assert isinstance(response, AnalyzeResponse)
        assert response.analysis_id == "test-123"
        assert response.execution_time == 1.5
        assert len(response.vulnerabilities) == 0
        assert len(response.patches) == 0
        assert response.workflow_complete is False
    
    def test_state_to_response_with_vulnerabilities(self):
        """Test _state_to_response with vulnerabilities."""
        orchestrator = WorkflowOrchestrator()
        
        vuln = Vulnerability(
            location="test.py:42",
            vuln_type="SQL Injection",
            severity="HIGH",
            description="Dangerous query",
            confidence=0.9,
            cwe_id="CWE-89",
            hypothesis="User input not sanitized"
        )
        
        state: AgentState = {
            "code": "test",
            "file_path": "test.py",
            "vulnerabilities": [vuln],
            "patches": [],
            "errors": [],
            "logs": ["Scanner: Found 1 vulnerability"],
            "workflow_complete": True
        }
        
        response = orchestrator._state_to_response(
            state=state,
            analysis_id="test-123",
            execution_time=2.0
        )
        
        assert len(response.vulnerabilities) == 1
        assert response.vulnerabilities[0].location == "test.py:42"
        assert response.vulnerabilities[0].vuln_type == "SQL Injection"
        assert response.vulnerabilities[0].severity == "HIGH"
        assert response.vulnerabilities[0].confidence == 0.9
        assert len(response.logs) == 1
    
    def test_state_to_response_with_patches(self):
        """Test _state_to_response with patches."""
        orchestrator = WorkflowOrchestrator()
        
        verification = VerificationResult(
            verified=True,
            counterexample=None,
            error_message=None,
            execution_time=1.0
        )
        
        patch = Patch(
            code="fixed_code",
            diff="- bad\n+ fixed",
            verified=True,
            verification_result=verification
        )
        
        state: AgentState = {
            "code": "test",
            "file_path": "test.py",
            "vulnerabilities": [],
            "patches": [patch],
            "errors": [],
            "logs": [],
            "workflow_complete": True
        }
        
        response = orchestrator._state_to_response(
            state=state,
            analysis_id="test-123",
            execution_time=3.0
        )
        
        assert len(response.patches) == 1
        assert response.patches[0].code == "fixed_code"
        assert response.patches[0].verified is True
        assert response.patches[0].verification_result is not None
        assert response.patches[0].verification_result["verified"] is True


class TestOrchestratorWorkflowExecution:
    """Test workflow execution."""
    
    @pytest.mark.asyncio
    @patch('api.orchestrator.create_workflow')
    @patch('api.orchestrator.ScannerAgent')
    async def test_analyze_code_initializes_if_needed(
        self,
        mock_scanner,
        mock_create_workflow
    ):
        """Test analyze_code initializes orchestrator if needed."""
        # Setup mocks
        mock_workflow = Mock()
        mock_workflow.invoke.return_value = {
            "code": "test",
            "file_path": "test.py",
            "vulnerabilities": [],
            "patches": [],
            "errors": [],
            "logs": [],
            "workflow_complete": True
        }
        mock_create_workflow.return_value = mock_workflow
        
        orchestrator = WorkflowOrchestrator()
        assert orchestrator.is_initialized() is False
        
        response = await orchestrator.analyze_code(
            code="print('hello')",
            file_path="test.py"
        )
        
        assert orchestrator.is_initialized() is True
        assert isinstance(response, AnalyzeResponse)
    
    @pytest.mark.asyncio
    @patch('api.orchestrator.create_workflow')
    @patch('api.orchestrator.ScannerAgent')
    async def test_analyze_code_returns_response(
        self,
        mock_scanner,
        mock_create_workflow
    ):
        """Test analyze_code returns AnalyzeResponse."""
        # Setup mocks
        mock_workflow = Mock()
        mock_workflow.invoke.return_value = {
            "code": "test",
            "file_path": "test.py",
            "vulnerabilities": [],
            "patches": [],
            "errors": [],
            "logs": ["Test log"],
            "workflow_complete": True
        }
        mock_create_workflow.return_value = mock_workflow
        
        orchestrator = WorkflowOrchestrator()
        
        response = await orchestrator.analyze_code(
            code="print('hello')",
            file_path="test.py",
            max_iterations=5
        )
        
        assert isinstance(response, AnalyzeResponse)
        assert response.analysis_id is not None
        assert response.execution_time >= 0  # Execution time should be non-negative
        assert len(response.logs) == 1
    
    @pytest.mark.asyncio
    @patch('api.orchestrator.create_workflow')
    @patch('api.orchestrator.ScannerAgent')
    async def test_analyze_code_handles_errors(
        self,
        mock_scanner,
        mock_create_workflow
    ):
        """Test analyze_code handles workflow errors."""
        # Setup mocks to raise error
        mock_workflow = Mock()
        mock_workflow.invoke.side_effect = Exception("Workflow failed")
        mock_create_workflow.return_value = mock_workflow
        
        orchestrator = WorkflowOrchestrator()
        
        response = await orchestrator.analyze_code(
            code="print('hello')",
            file_path="test.py"
        )
        
        assert isinstance(response, AnalyzeResponse)
        assert len(response.errors) > 0
        assert "Workflow failed" in response.errors[0]
        assert response.workflow_complete is False


class TestOrchestratorGlobalInstance:
    """Test global orchestrator instance."""
    
    def test_get_orchestrator_returns_singleton(self):
        """Test get_orchestrator() returns same instance."""
        orch1 = get_orchestrator()
        orch2 = get_orchestrator()
        
        assert orch1 is orch2
    
    @patch('api.orchestrator.create_workflow')
    @patch('api.orchestrator.ScannerAgent')
    def test_initialize_orchestrator_initializes_global(
        self,
        mock_scanner,
        mock_create_workflow
    ):
        """Test initialize_orchestrator() initializes global instance."""
        mock_workflow = Mock()
        mock_create_workflow.return_value = mock_workflow
        
        orch = initialize_orchestrator()
        
        assert orch.is_initialized() is True
