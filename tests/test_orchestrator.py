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



class TestOrchestratorSemanticComponents:
    """Test semantic scanning component initialization."""
    
    @patch('api.orchestrator.BinaryAnalyzerAgent', Mock())
    @patch('api.orchestrator.SmartContractAgent', Mock())
    @patch('api.orchestrator.config')
    @patch('api.orchestrator.create_workflow')
    @patch('api.orchestrator.ScannerAgent')
    @patch('api.orchestrator.KnowledgeBase')
    @patch('api.orchestrator.EmbeddingModel')
    @patch('api.orchestrator.VectorStore')
    @patch('api.orchestrator.SemanticScanner')
    @patch('api.orchestrator.ValidatorSuite')
    def test_initialize_with_semantic_scanning_enabled(
        self,
        mock_validator_suite,
        mock_semantic_scanner,
        mock_vector_store,
        mock_embedding_model,
        mock_knowledge_base,
        mock_scanner,
        mock_create_workflow,
        mock_config
    ):
        """
        Test initialization with semantic scanning enabled.
        
        Validates: Requirements 10.1, 10.2
        """
        # Configure mock config
        mock_config.enable_semantic_scanning = True
        mock_config.knowledge_base_path = "data/knowledge_base/samples.csv"
        mock_config.embedding_model_name = "BAAI/bge-base-en-v1.5"
        mock_config.embedding_model_path = None
        mock_config.vector_store_path = "data/vector_store"
        mock_config.similarity_threshold = 0.7
        mock_config.top_k_results = 10
        mock_config.semantic_scan_timeout = 2.0
        mock_config.enable_hardware_validation = True
        mock_config.enable_lifecycle_validation = True
        mock_config.enable_api_typo_detection = True
        mock_config.embedding_batch_size = 32
        
        # Setup mocks
        mock_kb_instance = Mock()
        mock_kb_instance.patterns = {"1": Mock(), "2": Mock()}
        mock_knowledge_base.return_value = mock_kb_instance
        
        mock_em_instance = Mock()
        mock_embedding_model.return_value = mock_em_instance
        
        mock_vs_instance = Mock()
        mock_vs_stats = Mock()
        mock_vs_stats.document_count = 10  # Non-zero to skip building
        mock_vs_instance.get_stats.return_value = mock_vs_stats
        mock_vector_store.return_value = mock_vs_instance
        
        mock_ss_instance = Mock()
        mock_semantic_scanner.return_value = mock_ss_instance
        
        mock_validator_instance = Mock()
        mock_validator_suite.return_value = mock_validator_instance
        
        mock_workflow = Mock()
        mock_create_workflow.return_value = mock_workflow
        
        # Initialize orchestrator
        orchestrator = WorkflowOrchestrator()
        orchestrator.initialize()
        
        # Verify semantic components were initialized
        assert orchestrator.is_initialized() is True
        assert orchestrator.semantic_scanner is not None
        assert orchestrator.validator_suite is not None
        
        # Verify initialization calls
        mock_knowledge_base.assert_called_once()
        mock_kb_instance.load_patterns.assert_called_once()
        mock_embedding_model.assert_called_once()
        mock_vector_store.assert_called_once()
        mock_semantic_scanner.assert_called_once()
        mock_validator_suite.assert_called_once()
    
    @patch('api.orchestrator.BinaryAnalyzerAgent', Mock())
    @patch('api.orchestrator.SmartContractAgent', Mock())
    @patch('api.orchestrator.config')
    @patch('api.orchestrator.create_workflow')
    @patch('api.orchestrator.ScannerAgent')
    def test_initialize_with_semantic_scanning_disabled(
        self,
        mock_scanner,
        mock_create_workflow,
        mock_config
    ):
        """
        Test initialization with semantic scanning disabled.
        
        Validates: Requirements 10.2, 10.3
        """
        # Configure mock config
        mock_config.enable_semantic_scanning = False
        
        # Setup mocks
        mock_workflow = Mock()
        mock_create_workflow.return_value = mock_workflow
        
        # Initialize orchestrator
        orchestrator = WorkflowOrchestrator()
        orchestrator.initialize()
        
        # Verify semantic components were NOT initialized
        assert orchestrator.is_initialized() is True
        assert orchestrator.semantic_scanner is None
        assert orchestrator.validator_suite is None
    
    @patch('api.orchestrator.BinaryAnalyzerAgent', Mock())
    @patch('api.orchestrator.SmartContractAgent', Mock())
    @patch('api.orchestrator.config')
    @patch('api.orchestrator.create_workflow')
    @patch('api.orchestrator.ScannerAgent')
    @patch('api.orchestrator.KnowledgeBase')
    def test_initialize_handles_semantic_component_failure(
        self,
        mock_knowledge_base,
        mock_scanner,
        mock_create_workflow,
        mock_config
    ):
        """
        Test initialization handles semantic component initialization failure.
        
        Should continue with graceful degradation when semantic components fail.
        
        Validates: Requirements 10.2, 10.3
        """
        # Configure mock config
        mock_config.enable_semantic_scanning = True
        mock_config.knowledge_base_path = "data/knowledge_base/samples.csv"
        
        # Setup mocks - knowledge base fails to load
        mock_knowledge_base.side_effect = Exception("Failed to load knowledge base")
        
        mock_workflow = Mock()
        mock_create_workflow.return_value = mock_workflow
        
        # Initialize orchestrator - should not raise exception
        orchestrator = WorkflowOrchestrator()
        orchestrator.initialize()
        
        # Verify orchestrator initialized but semantic components are None
        assert orchestrator.is_initialized() is True
        assert orchestrator.semantic_scanner is None
        assert orchestrator.validator_suite is None
    
    @patch('api.orchestrator.BinaryAnalyzerAgent', Mock())
    @patch('api.orchestrator.SmartContractAgent', Mock())
    @patch('api.orchestrator.config')
    @patch('api.orchestrator.create_workflow')
    @patch('api.orchestrator.ScannerAgent')
    @patch('api.orchestrator.KnowledgeBase')
    @patch('api.orchestrator.EmbeddingModel')
    @patch('api.orchestrator.VectorStore')
    def test_vector_store_built_when_empty(
        self,
        mock_vector_store,
        mock_embedding_model,
        mock_knowledge_base,
        mock_scanner,
        mock_create_workflow,
        mock_config
    ):
        """
        Test vector store is built when empty.
        
        Validates: Requirements 10.1
        """
        # Configure mock config
        mock_config.enable_semantic_scanning = True
        mock_config.knowledge_base_path = "data/knowledge_base/samples.csv"
        mock_config.embedding_model_name = "BAAI/bge-base-en-v1.5"
        mock_config.vector_store_path = "data/vector_store"
        mock_config.embedding_batch_size = 32
        
        # Setup mocks
        mock_pattern1 = Mock()
        mock_pattern1.id = "1"
        mock_pattern1.explanation = "Bug 1"
        mock_pattern1.buggy_code = "bad code"
        mock_pattern1.category = "test"
        mock_pattern1.severity = "high"
        
        mock_kb_instance = Mock()
        mock_kb_instance.patterns = {"1": mock_pattern1}
        mock_kb_instance.get_all_patterns.return_value = [mock_pattern1]
        mock_knowledge_base.return_value = mock_kb_instance
        
        mock_em_instance = Mock()
        mock_em_instance.encode_batch.return_value = [[0.1, 0.2, 0.3]]
        mock_embedding_model.return_value = mock_em_instance
        
        mock_vs_instance = Mock()
        mock_vs_stats = Mock()
        mock_vs_stats.document_count = 0  # Empty - should trigger build
        mock_vs_instance.get_stats.return_value = mock_vs_stats
        mock_vector_store.return_value = mock_vs_instance
        
        mock_workflow = Mock()
        mock_create_workflow.return_value = mock_workflow
        
        # Initialize orchestrator
        orchestrator = WorkflowOrchestrator()
        orchestrator.initialize()
        
        # Verify vector store was built
        mock_kb_instance.get_all_patterns.assert_called_once()
        mock_em_instance.encode_batch.assert_called_once()
        mock_vs_instance.add_embeddings.assert_called_once()
    
    @patch('api.orchestrator.BinaryAnalyzerAgent', Mock())
    @patch('api.orchestrator.SmartContractAgent', Mock())
    @patch('api.orchestrator.config')
    @patch('api.orchestrator.create_workflow')
    @patch('api.orchestrator.ScannerAgent')
    @patch('api.orchestrator.KnowledgeBase')
    @patch('api.orchestrator.EmbeddingModel')
    @patch('api.orchestrator.VectorStore')
    def test_vector_store_not_built_when_populated(
        self,
        mock_vector_store,
        mock_embedding_model,
        mock_knowledge_base,
        mock_scanner,
        mock_create_workflow,
        mock_config
    ):
        """
        Test vector store is not rebuilt when already populated.
        
        Validates: Requirements 10.1
        """
        # Configure mock config
        mock_config.enable_semantic_scanning = True
        mock_config.knowledge_base_path = "data/knowledge_base/samples.csv"
        
        # Setup mocks
        mock_kb_instance = Mock()
        mock_kb_instance.patterns = {"1": Mock()}
        mock_knowledge_base.return_value = mock_kb_instance
        
        mock_em_instance = Mock()
        mock_embedding_model.return_value = mock_em_instance
        
        mock_vs_instance = Mock()
        mock_vs_stats = Mock()
        mock_vs_stats.document_count = 10  # Already populated
        mock_vs_instance.get_stats.return_value = mock_vs_stats
        mock_vector_store.return_value = mock_vs_instance
        
        mock_workflow = Mock()
        mock_create_workflow.return_value = mock_workflow
        
        # Initialize orchestrator
        orchestrator = WorkflowOrchestrator()
        orchestrator.initialize()
        
        # Verify vector store was NOT built
        mock_kb_instance.get_all_patterns.assert_not_called()
        mock_em_instance.encode_batch.assert_not_called()
        mock_vs_instance.add_embeddings.assert_not_called()


class TestOrchestratorSemanticConfiguration:
    """Test semantic configuration handling."""
    
    @patch('api.orchestrator.BinaryAnalyzerAgent', Mock())
    @patch('api.orchestrator.SmartContractAgent', Mock())
    @patch('api.orchestrator.config')
    @patch('api.orchestrator.create_workflow')
    @patch('api.orchestrator.ScannerAgent')
    @patch('api.orchestrator.ValidatorSuite')
    def test_validator_suite_respects_feature_flags(
        self,
        mock_validator_suite,
        mock_scanner,
        mock_create_workflow,
        mock_config
    ):
        """
        Test validator suite respects feature flags.
        
        Validates: Requirements 9.3, 9.4
        """
        # Configure mock config with specific feature flags
        mock_config.enable_semantic_scanning = True
        mock_config.enable_hardware_validation = False
        mock_config.enable_lifecycle_validation = True
        mock_config.enable_api_typo_detection = False
        mock_config.knowledge_base_path = "data/knowledge_base/samples.csv"
        mock_config.vector_store_path = "data/vector_store"
        
        # Setup mocks
        mock_workflow = Mock()
        mock_create_workflow.return_value = mock_workflow
        
        # Mock semantic components to avoid full initialization
        with patch('api.orchestrator.KnowledgeBase'), \
             patch('api.orchestrator.EmbeddingModel'), \
             patch('api.orchestrator.VectorStore') as mock_vs, \
             patch('api.orchestrator.SemanticScanner'):
            
            mock_vs_instance = Mock()
            mock_vs_stats = Mock()
            mock_vs_stats.document_count = 10
            mock_vs_instance.get_stats.return_value = mock_vs_stats
            mock_vs.return_value = mock_vs_instance
            
            # Initialize orchestrator
            orchestrator = WorkflowOrchestrator()
            orchestrator.initialize()
            
            # Verify validator suite was called with correct flags
            mock_validator_suite.assert_called_once()
            call_kwargs = mock_validator_suite.call_args[1]
            assert call_kwargs['enable_hardware'] is False
            assert call_kwargs['enable_lifecycle'] is True
            assert call_kwargs['enable_api_typo'] is False
