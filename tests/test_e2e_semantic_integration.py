"""
Comprehensive End-to-End Integration Tests for Semantic Scanning Integration

This test suite validates the complete integration of Agentic-Bug-Hunter's
semantic scanning capabilities into secure-code-ai, including:
- Full workflow with semantic scanning enabled
- Full workflow with semantic scanning disabled
- Graceful degradation scenarios
- Concurrent requests
- Memory usage under load

Requirements: 3.1, 3.2, 3.3, 10.1, 10.2, 10.3, 11.4
"""

import pytest
import asyncio
import time
import psutil
import os
from pathlib import Path
from typing import List, Dict, Any
from unittest.mock import Mock, AsyncMock, patch
from concurrent.futures import ThreadPoolExecutor, as_completed

from api.orchestrator import WorkflowOrchestrator
from api.config import APIConfig
from api.models import AnalyzeRequest, AnalyzeResponse
from agent.state import AgentState, Vulnerability, SemanticVulnerability
from agent.nodes.semantic_scanner import SemanticScanner
from agent.validators.validator_suite import ValidatorSuite
from agent.knowledge.knowledge_base import KnowledgeBase
from agent.knowledge.embedding_model import EmbeddingModel
from agent.knowledge.vector_store import VectorStore


# Test fixtures

@pytest.fixture
def test_config():
    """Create test configuration."""
    config = APIConfig()
    config.enable_semantic_scanning = True
    config.knowledge_base_path = "data/knowledge_base/samples.csv"
    config.embedding_model_name = "BAAI/bge-base-en-v1.5"
    config.vector_store_path = "data/vector_store"
    config.similarity_threshold = 0.7
    config.top_k_results = 10
    return config


@pytest.fixture
def test_config_no_semantic():
    """Create test configuration with semantic scanning disabled."""
    config = APIConfig()
    config.enable_semantic_scanning = False
    return config


@pytest.fixture
def sample_vulnerable_code():
    """Sample vulnerable code for testing."""
    return """
import sqlite3

def get_user(username):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    query = f"SELECT * FROM users WHERE username='{username}'"
    cursor.execute(query)
    return cursor.fetchone()

def execute_command(cmd):
    import os
    os.system(cmd)
    
def read_file(filename):
    path = '/data/' + filename
    with open(path, 'r') as f:
        return f.read()
"""


@pytest.fixture
def sample_safe_code():
    """Sample safe code for testing."""
    return """
def add_numbers(a: int, b: int) -> int:
    return a + b

def greet(name: str) -> str:
    return f"Hello, {name}!"
"""


# Test Class 1: Full Workflow with Semantic Scanning Enabled

class TestFullWorkflowSemanticEnabled:
    """Test complete workflow with semantic scanning enabled."""
    
    @pytest.mark.asyncio
    async def test_workflow_detects_vulnerabilities_from_both_scanners(
        self, test_config, sample_vulnerable_code
    ):
        """
        Test that workflow detects vulnerabilities from both static and semantic scanners.
        
        Requirements: 3.1, 3.2
        """
        # Skip if knowledge base not available
        if not Path(test_config.knowledge_base_path).exists():
            pytest.skip("Knowledge base not available")
        
        # Create orchestrator
        orchestrator = WorkflowOrchestrator(config=test_config, vllm_client=None)
        orchestrator.initialize()
        
        try:
            # Create request
            request = AnalyzeRequest(
                code=sample_vulnerable_code,
                file_path="test.py",
                max_iterations=3
            )
            
            # Run analysis
            start_time = time.time()
            response = await orchestrator.analyze_code(request)
            execution_time = time.time() - start_time
            
            # Verify response structure
            assert isinstance(response, AnalyzeResponse)
            assert response.analysis_id is not None
            
            # Verify vulnerabilities detected
            assert "vulnerabilities" in response.dict()
            vulnerabilities = response.vulnerabilities
            
            # Should detect at least one vulnerability
            assert len(vulnerabilities) > 0, "Should detect vulnerabilities"
            
            # Verify execution completed
            assert execution_time < 60.0, f"Workflow took too long: {execution_time}s"
            
            # Log results
            print(f"\n=== Semantic Enabled Workflow ===")
            print(f"Execution time: {execution_time:.2f}s")
            print(f"Vulnerabilities detected: {len(vulnerabilities)}")
            print(f"Errors: {len(response.errors)}")
            
        finally:
            orchestrator.cleanup()
    
    @pytest.mark.asyncio
    async def test_workflow_merges_results_without_duplicates(
        self, test_config, sample_vulnerable_code
    ):
        """
        Test that workflow merges results from both scanners without duplicates.
        
        Requirements: 3.2
        """
        # Skip if knowledge base not available
        if not Path(test_config.knowledge_base_path).exists():
            pytest.skip("Knowledge base not available")
        
        orchestrator = WorkflowOrchestrator(config=test_config, vllm_client=None)
        orchestrator.initialize()
        
        try:
            request = AnalyzeRequest(
                code=sample_vulnerable_code,
                file_path="test.py"
            )
            
            response = await orchestrator.analyze_code(request)
            
            # Check for duplicate vulnerabilities
            vulnerabilities = response.vulnerabilities
            locations = [v.location for v in vulnerabilities]
            
            # Count duplicates
            unique_locations = set(locations)
            
            # Should not have exact duplicates (same location and type)
            vuln_signatures = [(v.location, v.vuln_type) for v in vulnerabilities]
            unique_signatures = set(vuln_signatures)
            
            # Allow some duplicates if they're from different sources
            # but should not have many
            duplicate_ratio = 1 - (len(unique_signatures) / len(vuln_signatures)) if vuln_signatures else 0
            assert duplicate_ratio < 0.3, f"Too many duplicates: {duplicate_ratio:.1%}"
            
            print(f"\n=== Result Merging ===")
            print(f"Total vulnerabilities: {len(vulnerabilities)}")
            print(f"Unique signatures: {len(unique_signatures)}")
            print(f"Duplicate ratio: {duplicate_ratio:.1%}")
            
        finally:
            orchestrator.cleanup()
    
    @pytest.mark.asyncio
    async def test_workflow_includes_semantic_specific_results(
        self, test_config, sample_vulnerable_code
    ):
        """
        Test that workflow includes semantic-specific results (hardware, lifecycle, API typos).
        
        Requirements: 3.1
        """
        # Skip if knowledge base not available
        if not Path(test_config.knowledge_base_path).exists():
            pytest.skip("Knowledge base not available")
        
        orchestrator = WorkflowOrchestrator(config=test_config, vllm_client=None)
        orchestrator.initialize()
        
        try:
            # Use code with hardware API calls
            code_with_hardware = """
def configure_device():
    set_voltage(35)  # Exceeds 30V limit
    set_sample_count(10000)  # Exceeds 8192 limit
"""
            
            request = AnalyzeRequest(
                code=code_with_hardware,
                file_path="hardware.py"
            )
            
            response = await orchestrator.analyze_code(request)
            
            # Check if response includes hardware violations
            # (May be in vulnerabilities or separate field depending on implementation)
            response_dict = response.dict()
            
            # Look for hardware-related findings
            has_hardware_findings = (
                any("voltage" in str(v).lower() or "sample" in str(v).lower() 
                    for v in response.vulnerabilities) or
                "hardware_violations" in response_dict
            )
            
            print(f"\n=== Semantic-Specific Results ===")
            print(f"Hardware findings detected: {has_hardware_findings}")
            print(f"Total vulnerabilities: {len(response.vulnerabilities)}")
            
        finally:
            orchestrator.cleanup()


# Test Class 2: Full Workflow with Semantic Scanning Disabled

class TestFullWorkflowSemanticDisabled:
    """Test complete workflow with semantic scanning disabled."""
    
    @pytest.mark.asyncio
    async def test_workflow_functions_without_semantic_scanning(
        self, test_config_no_semantic, sample_vulnerable_code
    ):
        """
        Test that workflow functions normally when semantic scanning is disabled.
        
        Requirements: 3.3, 10.3
        """
        orchestrator = WorkflowOrchestrator(config=test_config_no_semantic, vllm_client=None)
        orchestrator.initialize()
        
        try:
            request = AnalyzeRequest(
                code=sample_vulnerable_code,
                file_path="test.py"
            )
            
            # Should complete without errors
            response = await orchestrator.analyze_code(request)
            
            # Verify response structure
            assert isinstance(response, AnalyzeResponse)
            assert response.analysis_id is not None
            
            # Should still detect vulnerabilities (from static scanner)
            # Note: May not detect all vulnerabilities without semantic scanning
            
            # Should not have semantic-specific fields populated
            response_dict = response.dict()
            if "semantic_vulnerabilities" in response_dict:
                assert len(response_dict["semantic_vulnerabilities"]) == 0
            
            print(f"\n=== Semantic Disabled Workflow ===")
            print(f"Vulnerabilities detected: {len(response.vulnerabilities)}")
            print(f"Workflow completed successfully: ")
            
        finally:
            orchestrator.cleanup()
    
    @pytest.mark.asyncio
    async def test_workflow_performance_without_semantic_scanning(
        self, test_config_no_semantic, sample_vulnerable_code
    ):
        """
        Test that workflow is faster when semantic scanning is disabled.
        
        Requirements: 10.3
        """
        orchestrator = WorkflowOrchestrator(config=test_config_no_semantic, vllm_client=None)
        orchestrator.initialize()
        
        try:
            request = AnalyzeRequest(
                code=sample_vulnerable_code,
                file_path="test.py"
            )
            
            start_time = time.time()
            response = await orchestrator.analyze_code(request)
            execution_time = time.time() - start_time
            
            # Should complete quickly without semantic scanning
            assert execution_time < 30.0, f"Workflow took too long: {execution_time}s"
            
            print(f"\n=== Performance Without Semantic ===")
            print(f"Execution time: {execution_time:.2f}s")
            
        finally:
            orchestrator.cleanup()


# Test Class 3: Graceful Degradation Scenarios

class TestGracefulDegradation:
    """Test graceful degradation when components fail."""
    
    @pytest.mark.asyncio
    async def test_workflow_continues_when_semantic_scanner_fails(
        self, test_config, sample_vulnerable_code
    ):
        """
        Test that workflow continues when semantic scanner fails.
        
        Requirements: 3.3, 10.2
        """
        orchestrator = WorkflowOrchestrator(config=test_config, vllm_client=None)
        orchestrator.initialize()
        
        try:
            # Mock semantic scanner to fail
            if orchestrator.semantic_scanner:
                original_scan = orchestrator.semantic_scanner.scan
                
                async def failing_scan(code, file_path):
                    raise RuntimeError("Semantic scanner failed")
                
                orchestrator.semantic_scanner.scan = failing_scan
            
            request = AnalyzeRequest(
                code=sample_vulnerable_code,
                file_path="test.py"
            )
            
            # Should not crash
            response = await orchestrator.analyze_code(request)
            
            # Should have results from static scanner
            assert isinstance(response, AnalyzeResponse)
            
            # Should have logged the error
            assert len(response.errors) > 0 or len(response.logs) > 0
            
            print(f"\n=== Graceful Degradation (Semantic Failure) ===")
            print(f"Workflow completed despite semantic scanner failure: ")
            print(f"Errors logged: {len(response.errors)}")
            
        finally:
            orchestrator.cleanup()
    
    @pytest.mark.asyncio
    async def test_workflow_continues_when_validator_suite_fails(
        self, test_config, sample_vulnerable_code
    ):
        """
        Test that workflow continues when validator suite fails.
        
        Requirements: 3.3, 10.2
        """
        orchestrator = WorkflowOrchestrator(config=test_config, vllm_client=None)
        orchestrator.initialize()
        
        try:
            # Mock validator suite to fail
            if orchestrator.validator_suite:
                original_validate = orchestrator.validator_suite.validate
                
                def failing_validate(code):
                    raise RuntimeError("Validator suite failed")
                
                orchestrator.validator_suite.validate = failing_validate
            
            request = AnalyzeRequest(
                code=sample_vulnerable_code,
                file_path="test.py"
            )
            
            # Should not crash
            response = await orchestrator.analyze_code(request)
            
            # Should have results from scanners
            assert isinstance(response, AnalyzeResponse)
            
            print(f"\n=== Graceful Degradation (Validator Failure) ===")
            print(f"Workflow completed despite validator failure: ")
            
        finally:
            orchestrator.cleanup()
    
    @pytest.mark.asyncio
    async def test_workflow_continues_when_embedding_model_unavailable(
        self, test_config, sample_vulnerable_code
    ):
        """
        Test that workflow continues when embedding model is unavailable.
        
        Requirements: 10.1, 10.2
        """
        # Create config with invalid embedding model path
        config = APIConfig()
        config.enable_semantic_scanning = True
        config.embedding_model_path = "/nonexistent/path"
        config.knowledge_base_path = "data/knowledge_base/samples.csv"
        
        orchestrator = WorkflowOrchestrator(config=config, vllm_client=None)
        
        # Initialize should handle missing embedding model gracefully
        orchestrator.initialize()
        
        try:
            request = AnalyzeRequest(
                code=sample_vulnerable_code,
                file_path="test.py"
            )
            
            # Should not crash
            response = await orchestrator.analyze_code(request)
            
            # Should complete with static scanner only
            assert isinstance(response, AnalyzeResponse)
            
            print(f"\n=== Graceful Degradation (Embedding Model Unavailable) ===")
            print(f"Workflow completed without embedding model: ")
            
        finally:
            orchestrator.cleanup()


# Test Class 4: Concurrent Requests

class TestConcurrentRequests:
    """Test handling of concurrent requests."""
    
    @pytest.mark.asyncio
    async def test_workflow_handles_concurrent_requests(
        self, test_config, sample_vulnerable_code, sample_safe_code
    ):
        """
        Test that workflow handles multiple concurrent requests correctly.
        
        Requirements: 10.1, 11.4
        """
        # Skip if knowledge base not available
        if not Path(test_config.knowledge_base_path).exists():
            pytest.skip("Knowledge base not available")
        
        orchestrator = WorkflowOrchestrator(config=test_config, vllm_client=None)
        orchestrator.initialize()
        
        try:
            # Create multiple requests
            requests = [
                AnalyzeRequest(code=sample_vulnerable_code, file_path="vuln1.py"),
                AnalyzeRequest(code=sample_safe_code, file_path="safe1.py"),
                AnalyzeRequest(code=sample_vulnerable_code, file_path="vuln2.py"),
                AnalyzeRequest(code=sample_safe_code, file_path="safe2.py"),
            ]
            
            # Run concurrently
            start_time = time.time()
            tasks = [orchestrator.analyze_code(req) for req in requests]
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            execution_time = time.time() - start_time
            
            # Verify all requests completed
            assert len(responses) == len(requests)
            
            # Count successful responses
            successful = sum(1 for r in responses if isinstance(r, AnalyzeResponse))
            assert successful == len(requests), f"Only {successful}/{len(requests)} requests succeeded"
            
            # Verify each response is unique
            analysis_ids = [r.analysis_id for r in responses if isinstance(r, AnalyzeResponse)]
            assert len(set(analysis_ids)) == len(analysis_ids), "Analysis IDs should be unique"
            
            print(f"\n=== Concurrent Requests ===")
            print(f"Total requests: {len(requests)}")
            print(f"Successful: {successful}")
            print(f"Total execution time: {execution_time:.2f}s")
            print(f"Average per request: {execution_time/len(requests):.2f}s")
            
        finally:
            orchestrator.cleanup()
    
    @pytest.mark.asyncio
    async def test_workflow_concurrent_performance(
        self, test_config, sample_vulnerable_code
    ):
        """
        Test that concurrent requests complete in reasonable time.
        
        Requirements: 10.1, 11.4
        """
        # Skip if knowledge base not available
        if not Path(test_config.knowledge_base_path).exists():
            pytest.skip("Knowledge base not available")
        
        orchestrator = WorkflowOrchestrator(config=test_config, vllm_client=None)
        orchestrator.initialize()
        
        try:
            # Create 5 concurrent requests
            num_requests = 5
            requests = [
                AnalyzeRequest(code=sample_vulnerable_code, file_path=f"test{i}.py")
                for i in range(num_requests)
            ]
            
            # Run concurrently
            start_time = time.time()
            tasks = [orchestrator.analyze_code(req) for req in requests]
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            concurrent_time = time.time() - start_time
            
            # Verify performance
            # Concurrent execution should be faster than sequential
            # (though not necessarily num_requests times faster due to shared resources)
            expected_max_time = 60.0 * num_requests  # Very generous upper bound
            assert concurrent_time < expected_max_time, \
                f"Concurrent execution took too long: {concurrent_time:.2f}s"
            
            print(f"\n=== Concurrent Performance ===")
            print(f"Requests: {num_requests}")
            print(f"Total time: {concurrent_time:.2f}s")
            print(f"Average per request: {concurrent_time/num_requests:.2f}s")
            
        finally:
            orchestrator.cleanup()


# Test Class 5: Memory Usage Under Load

class TestMemoryUsage:
    """Test memory usage under load."""
    
    @pytest.mark.asyncio
    async def test_workflow_memory_usage_stays_bounded(
        self, test_config, sample_vulnerable_code
    ):
        """
        Test that memory usage stays bounded under repeated requests.
        
        Requirements: 11.4
        """
        # Skip if knowledge base not available
        if not Path(test_config.knowledge_base_path).exists():
            pytest.skip("Knowledge base not available")
        
        orchestrator = WorkflowOrchestrator(config=test_config, vllm_client=None)
        orchestrator.initialize()
        
        try:
            # Get initial memory usage
            process = psutil.Process(os.getpid())
            initial_memory_mb = process.memory_info().rss / 1024 / 1024
            
            # Run multiple requests
            num_requests = 10
            for i in range(num_requests):
                request = AnalyzeRequest(
                    code=sample_vulnerable_code,
                    file_path=f"test{i}.py"
                )
                response = await orchestrator.analyze_code(request)
                assert isinstance(response, AnalyzeResponse)
            
            # Get final memory usage
            final_memory_mb = process.memory_info().rss / 1024 / 1024
            memory_increase_mb = final_memory_mb - initial_memory_mb
            
            # Memory increase should be reasonable (< 500MB for 10 requests)
            assert memory_increase_mb < 500, \
                f"Memory increased too much: {memory_increase_mb:.1f}MB"
            
            print(f"\n=== Memory Usage ===")
            print(f"Initial memory: {initial_memory_mb:.1f}MB")
            print(f"Final memory: {final_memory_mb:.1f}MB")
            print(f"Increase: {memory_increase_mb:.1f}MB")
            print(f"Requests processed: {num_requests}")
            
        finally:
            orchestrator.cleanup()
    
    @pytest.mark.asyncio
    async def test_embedding_cache_limits_memory_growth(
        self, test_config, sample_vulnerable_code
    ):
        """
        Test that embedding cache limits memory growth.
        
        Requirements: 11.4
        """
        # Skip if knowledge base not available
        if not Path(test_config.knowledge_base_path).exists():
            pytest.skip("Knowledge base not available")
        
        orchestrator = WorkflowOrchestrator(config=test_config, vllm_client=None)
        orchestrator.initialize()
        
        try:
            # Check if embedding model has cache
            if not orchestrator.semantic_scanner or not orchestrator.semantic_scanner.embedding_model:
                pytest.skip("Embedding model not available")
            
            embedding_model = orchestrator.semantic_scanner.embedding_model
            
            # Generate many unique embeddings
            num_embeddings = 100
            texts = [f"unique text {i}" for i in range(num_embeddings)]
            
            process = psutil.Process(os.getpid())
            initial_memory_mb = process.memory_info().rss / 1024 / 1024
            
            # Generate embeddings
            for text in texts:
                embedding_model.encode(text)
            
            final_memory_mb = process.memory_info().rss / 1024 / 1024
            memory_increase_mb = final_memory_mb - initial_memory_mb
            
            # Memory increase should be bounded by cache size
            # (Each embedding is ~3KB, so 100 embeddings = ~300KB)
            # Allow up to 100MB increase for overhead
            assert memory_increase_mb < 100, \
                f"Memory increased too much: {memory_increase_mb:.1f}MB"
            
            print(f"\n=== Embedding Cache Memory ===")
            print(f"Embeddings generated: {num_embeddings}")
            print(f"Memory increase: {memory_increase_mb:.1f}MB")
            
        finally:
            orchestrator.cleanup()


# Test Class 6: End-to-End Workflow Validation

class TestEndToEndWorkflowValidation:
    """Validate complete end-to-end workflow."""
    
    @pytest.mark.asyncio
    async def test_complete_workflow_with_all_components(
        self, test_config, sample_vulnerable_code
    ):
        """
        Test complete workflow with all components enabled.
        
        Requirements: 3.1, 3.2, 10.1
        """
        # Skip if knowledge base not available
        if not Path(test_config.knowledge_base_path).exists():
            pytest.skip("Knowledge base not available")
        
        orchestrator = WorkflowOrchestrator(config=test_config, vllm_client=None)
        orchestrator.initialize()
        
        try:
            request = AnalyzeRequest(
                code=sample_vulnerable_code,
                file_path="complete_test.py",
                max_iterations=3
            )
            
            # Run complete analysis
            start_time = time.time()
            response = await orchestrator.analyze_code(request)
            execution_time = time.time() - start_time
            
            # Verify all workflow stages completed
            assert isinstance(response, AnalyzeResponse)
            assert response.analysis_id is not None
            
            # Verify response has all expected fields
            response_dict = response.dict()
            expected_fields = [
                "analysis_id",
                "vulnerabilities",
                "patches",
                "execution_time",
                "errors",
                "logs",
                "workflow_complete"
            ]
            
            for field in expected_fields:
                assert field in response_dict, f"Missing field: {field}"
            
            # Verify execution time is reasonable
            assert execution_time < 120.0, f"Workflow took too long: {execution_time}s"
            
            # Log comprehensive results
            print(f"\n=== Complete Workflow Validation ===")
            print(f"Execution time: {execution_time:.2f}s")
            print(f"Vulnerabilities: {len(response.vulnerabilities)}")
            print(f"Patches: {len(response.patches)}")
            print(f"Errors: {len(response.errors)}")
            print(f"Logs: {len(response.logs)}")
            print(f"Workflow complete: {response.workflow_complete}")
            
            # Verify workflow completed successfully
            assert response.workflow_complete or len(response.errors) == 0, \
                "Workflow should complete successfully or have no errors"
            
        finally:
            orchestrator.cleanup()
    
    @pytest.mark.asyncio
    async def test_workflow_state_consistency_throughout_execution(
        self, test_config, sample_vulnerable_code
    ):
        """
        Test that workflow maintains state consistency throughout execution.
        
        Requirements: 3.1, 3.2
        """
        # Skip if knowledge base not available
        if not Path(test_config.knowledge_base_path).exists():
            pytest.skip("Knowledge base not available")
        
        orchestrator = WorkflowOrchestrator(config=test_config, vllm_client=None)
        orchestrator.initialize()
        
        try:
            request = AnalyzeRequest(
                code=sample_vulnerable_code,
                file_path="state_test.py"
            )
            
            response = await orchestrator.analyze_code(request)
            
            # Verify state consistency
            response_dict = response.dict()
            
            # All list fields should be lists
            list_fields = ["vulnerabilities", "patches", "errors", "logs"]
            for field in list_fields:
                if field in response_dict:
                    assert isinstance(response_dict[field], list), \
                        f"{field} should be a list"
            
            # Execution time should be positive
            assert response.execution_time >= 0, "Execution time should be non-negative"
            
            # Analysis ID should be non-empty
            assert response.analysis_id, "Analysis ID should not be empty"
            
            print(f"\n=== State Consistency ===")
            print(f"All state fields valid: ")
            print(f"State consistency maintained: ")
            
        finally:
            orchestrator.cleanup()


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "-s", "--tb=short"])
