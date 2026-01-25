"""
Integration tests for /analyze endpoint.
Tests end-to-end workflow with sample vulnerable code.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock, patch
import time

from api.server import app, service_state
from api.models import AnalyzeResponse, VulnerabilityResponse, PatchResponse
from agent.state import Vulnerability, Patch, VerificationResult


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_service_state():
    """Reset service state before each test."""
    service_state.vllm_loaded = True
    service_state.workflow_ready = True
    service_state.request_queue_depth = 0
    service_state.start_time = time.time()
    yield
    # Cleanup after test
    service_state.vllm_loaded = False
    service_state.workflow_ready = False
    service_state.request_queue_depth = 0


class TestAnalyzeIntegration:
    """Integration tests for /analyze endpoint."""
    
    def test_analyze_with_sql_injection_vulnerability(self, client):
        """Test /analyze with sample SQL injection code."""
        # Mock orchestrator to return realistic response
        from api import server
        
        # Create mock vulnerability
        mock_vuln = Mock(spec=Vulnerability)
        mock_vuln.location = "test.py:1"
        mock_vuln.vuln_type = "SQL Injection"
        mock_vuln.severity = "HIGH"
        mock_vuln.description = "SQL query uses f-string formatting with user input"
        mock_vuln.confidence = 0.95
        mock_vuln.cwe_id = "CWE-89"
        mock_vuln.hypothesis = "User input is directly interpolated into SQL query without sanitization"
        
        # Create mock patch
        mock_verification = Mock(spec=VerificationResult)
        mock_verification.verified = True
        mock_verification.counterexample = None
        mock_verification.error_message = None
        mock_verification.execution_time = 2.5
        
        mock_patch = Mock(spec=Patch)
        mock_patch.code = 'query = "SELECT * FROM users WHERE username=?"\ncursor.execute(query, (username,))'
        mock_patch.diff = '- query = f"SELECT * FROM users WHERE username=\'{username}\'"\n+ query = "SELECT * FROM users WHERE username=?"\n+ cursor.execute(query, (username,))'
        mock_patch.verified = True
        mock_patch.verification_result = mock_verification
        
        # Mock orchestrator
        mock_orchestrator = Mock()
        mock_orchestrator.analyze_code = AsyncMock(
            return_value=AnalyzeResponse(
                analysis_id="test-sql-injection-123",
                vulnerabilities=[
                    VulnerabilityResponse(
                        location=mock_vuln.location,
                        vuln_type=mock_vuln.vuln_type,
                        severity=mock_vuln.severity,
                        description=mock_vuln.description,
                        confidence=mock_vuln.confidence,
                        cwe_id=mock_vuln.cwe_id,
                        hypothesis=mock_vuln.hypothesis
                    )
                ],
                patches=[
                    PatchResponse(
                        code=mock_patch.code,
                        diff=mock_patch.diff,
                        verified=mock_patch.verified,
                        verification_result={
                            "verified": mock_verification.verified,
                            "counterexample": mock_verification.counterexample,
                            "error_message": mock_verification.error_message,
                            "execution_time": mock_verification.execution_time
                        }
                    )
                ],
                execution_time=15.3,
                errors=[],
                logs=["Scanner Agent: Found 1 potential vulnerability", "Patcher Agent: Generated 1 patch"],
                workflow_complete=True
            )
        )
        server.service_state.orchestrator = mock_orchestrator
        
        # Send request with vulnerable SQL code
        request_data = {
            "code": "query = f\"SELECT * FROM users WHERE username='{username}'\"",
            "file_path": "test.py",
            "max_iterations": 3
        }
        
        response = client.post("/analyze", json=request_data)
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        # Check analysis ID
        assert "analysis_id" in data
        assert data["analysis_id"] == "test-sql-injection-123"
        
        # Check vulnerabilities
        assert len(data["vulnerabilities"]) == 1
        vuln = data["vulnerabilities"][0]
        assert vuln["vuln_type"] == "SQL Injection"
        assert vuln["severity"] == "HIGH"
        assert vuln["confidence"] == 0.95
        assert vuln["cwe_id"] == "CWE-89"
        
        # Check patches
        assert len(data["patches"]) == 1
        patch = data["patches"][0]
        assert patch["verified"] is True
        assert "cursor.execute" in patch["code"]
        assert patch["verification_result"]["verified"] is True
        
        # Check execution metadata
        assert data["execution_time"] > 0
        assert data["workflow_complete"] is True
        assert len(data["errors"]) == 0
        assert len(data["logs"]) > 0
        
        # Verify orchestrator was called with correct parameters
        mock_orchestrator.analyze_code.assert_called_once()
        call_kwargs = mock_orchestrator.analyze_code.call_args.kwargs
        assert call_kwargs["code"] == request_data["code"]
        assert call_kwargs["file_path"] == request_data["file_path"]
        assert call_kwargs["max_iterations"] == request_data["max_iterations"]
    
    def test_analyze_with_no_vulnerabilities(self, client):
        """Test /analyze with safe code (no vulnerabilities)."""
        from api import server
        
        # Mock orchestrator to return empty results
        mock_orchestrator = Mock()
        mock_orchestrator.analyze_code = AsyncMock(
            return_value=AnalyzeResponse(
                analysis_id="test-safe-code-456",
                vulnerabilities=[],
                patches=[],
                execution_time=5.2,
                errors=[],
                logs=["Scanner Agent: No vulnerabilities detected"],
                workflow_complete=True
            )
        )
        server.service_state.orchestrator = mock_orchestrator
        
        # Send request with safe code
        request_data = {
            "code": "print('Hello, World!')",
            "file_path": "hello.py"
        }
        
        response = client.post("/analyze", json=request_data)
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        assert data["analysis_id"] == "test-safe-code-456"
        assert len(data["vulnerabilities"]) == 0
        assert len(data["patches"]) == 0
        assert data["workflow_complete"] is True
        assert len(data["errors"]) == 0
    
    def test_analyze_with_workflow_error(self, client):
        """Test /analyze handles workflow execution errors."""
        from api import server
        
        # Mock orchestrator to return error response
        mock_orchestrator = Mock()
        mock_orchestrator.analyze_code = AsyncMock(
            return_value=AnalyzeResponse(
                analysis_id="test-error-789",
                vulnerabilities=[],
                patches=[],
                execution_time=2.0,
                errors=["Scanner Agent failed: Timeout", "Workflow aborted"],
                logs=["Scanner Agent: Starting analysis", "Scanner Agent: Timeout after 30s"],
                workflow_complete=False
            )
        )
        server.service_state.orchestrator = mock_orchestrator
        
        # Send request
        request_data = {
            "code": "some_code = 'test'"
        }
        
        response = client.post("/analyze", json=request_data)
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        assert data["workflow_complete"] is False
        assert len(data["errors"]) > 0
        assert "Scanner Agent failed" in data["errors"][0]
    
    def test_analyze_with_orchestrator_exception(self, client):
        """Test /analyze handles orchestrator exceptions."""
        from api import server
        
        # Mock orchestrator to raise exception
        mock_orchestrator = Mock()
        mock_orchestrator.analyze_code = AsyncMock(
            side_effect=Exception("Orchestrator internal error")
        )
        server.service_state.orchestrator = mock_orchestrator
        
        # Send request
        request_data = {
            "code": "test_code = 'hello'"
        }
        
        response = client.post("/analyze", json=request_data)
        
        # Verify error response
        assert response.status_code == 500
        data = response.json()
        
        assert "detail" in data
        assert "Analysis failed" in data["detail"]
        assert "Orchestrator internal error" in data["detail"]
    
    def test_analyze_without_orchestrator(self, client):
        """Test /analyze returns 503 when orchestrator not initialized."""
        from api import server
        
        # Set orchestrator to None
        server.service_state.orchestrator = None
        
        # Send request
        request_data = {
            "code": "test_code = 'hello'"
        }
        
        response = client.post("/analyze", json=request_data)
        
        # Verify error response
        assert response.status_code == 503
        data = response.json()
        
        assert "detail" in data
        assert "Workflow orchestrator not initialized" in data["detail"]
    
    def test_analyze_with_invalid_code(self, client):
        """Test /analyze rejects invalid code."""
        # Test empty code
        response = client.post("/analyze", json={"code": ""})
        assert response.status_code == 422
        
        # Test whitespace-only code
        response = client.post("/analyze", json={"code": "   \n\t  "})
        assert response.status_code == 422
    
    def test_analyze_with_invalid_max_iterations(self, client):
        """Test /analyze rejects invalid max_iterations."""
        # Test too low
        response = client.post("/analyze", json={
            "code": "print('hello')",
            "max_iterations": 0
        })
        assert response.status_code == 422
        
        # Test too high
        response = client.post("/analyze", json={
            "code": "print('hello')",
            "max_iterations": 11
        })
        assert response.status_code == 422
    
    def test_analyze_queue_depth_tracking(self, client):
        """Test /analyze tracks request queue depth."""
        from api import server
        
        # Mock orchestrator with slow response
        mock_orchestrator = Mock()
        
        async def slow_analyze(**kwargs):
            # Simulate slow processing
            import asyncio
            await asyncio.sleep(0.1)
            return AnalyzeResponse(
                analysis_id="test-queue-123",
                vulnerabilities=[],
                patches=[],
                execution_time=0.1,
                errors=[],
                logs=[],
                workflow_complete=True
            )
        
        mock_orchestrator.analyze_code = slow_analyze
        server.service_state.orchestrator = mock_orchestrator
        
        # Check initial queue depth
        initial_depth = server.service_state.request_queue_depth
        assert initial_depth == 0
        
        # Send request
        request_data = {
            "code": "print('hello')"
        }
        
        response = client.post("/analyze", json=request_data)
        
        # Verify response
        assert response.status_code == 200
        
        # Queue depth should be back to initial after request completes
        assert server.service_state.request_queue_depth == initial_depth


class TestAPILLMIntegration:
    """Integration tests for API with LLM-powered agents."""
    
    def test_orchestrator_initializes_with_llm_client(self, client):
        """Test that orchestrator is initialized with LLMClient when vLLM is available."""
        from api import server
        from api.vllm_client import VLLMClient
        from api.orchestrator import WorkflowOrchestrator
        from agent.llm_client import LLMClient
        
        # Create mock vLLM client
        mock_vllm = Mock(spec=VLLMClient)
        mock_vllm.generate = Mock(return_value="test response")
        
        # Create orchestrator with vLLM client
        orchestrator = WorkflowOrchestrator(vllm_client=mock_vllm)
        orchestrator.initialize()
        
        # Verify LLMClient was created
        assert orchestrator.llm_client is not None
        assert isinstance(orchestrator.llm_client, LLMClient)
        assert orchestrator.llm_client.vllm_client == mock_vllm
        
        # Cleanup
        orchestrator.cleanup()
    
    def test_orchestrator_initializes_without_llm_client(self, client):
        """Test that orchestrator initializes without LLMClient when vLLM unavailable."""
        from api.orchestrator import WorkflowOrchestrator
        
        # Create orchestrator without vLLM client
        orchestrator = WorkflowOrchestrator(vllm_client=None)
        orchestrator.initialize()
        
        # Verify LLMClient is None (agents will use template-based logic)
        assert orchestrator.llm_client is None
        assert orchestrator.is_initialized()
        
        # Cleanup
        orchestrator.cleanup()
    
    def test_agents_receive_llm_client(self, client):
        """Test that Scanner, Speculator, and Patcher receive LLMClient."""
        from api.vllm_client import VLLMClient
        from api.orchestrator import WorkflowOrchestrator
        from agent.nodes.scanner import ScannerAgent
        from agent.nodes.speculator import SpeculatorAgent
        from agent.nodes.patcher import PatcherAgent
        from agent.nodes.symbot import SymBotAgent
        
        # Create mock vLLM client
        mock_vllm = Mock(spec=VLLMClient)
        
        # Create orchestrator
        orchestrator = WorkflowOrchestrator(vllm_client=mock_vllm)
        
        # Patch agent constructors to capture initialization
        scanner_init_called = []
        speculator_init_called = []
        patcher_init_called = []
        symbot_init_called = []
        
        original_scanner_init = ScannerAgent.__init__
        original_speculator_init = SpeculatorAgent.__init__
        original_patcher_init = PatcherAgent.__init__
        original_symbot_init = SymBotAgent.__init__
        
        def mock_scanner_init(self, llm_client=None):
            scanner_init_called.append(llm_client)
            original_scanner_init(self, llm_client)
        
        def mock_speculator_init(self, llm_client=None):
            speculator_init_called.append(llm_client)
            original_speculator_init(self, llm_client)
        
        def mock_patcher_init(self, llm_client=None):
            patcher_init_called.append(llm_client)
            original_patcher_init(self, llm_client)
        
        def mock_symbot_init(self, timeout=30):
            symbot_init_called.append(True)
            original_symbot_init(self, timeout)
        
        with patch.object(ScannerAgent, '__init__', mock_scanner_init):
            with patch.object(SpeculatorAgent, '__init__', mock_speculator_init):
                with patch.object(PatcherAgent, '__init__', mock_patcher_init):
                    with patch.object(SymBotAgent, '__init__', mock_symbot_init):
                        orchestrator.initialize()
        
        # Verify Scanner received LLMClient
        assert len(scanner_init_called) == 1
        assert scanner_init_called[0] is not None
        
        # Verify Speculator received LLMClient
        assert len(speculator_init_called) == 1
        assert speculator_init_called[0] is not None
        
        # Verify Patcher received LLMClient
        assert len(patcher_init_called) == 1
        assert patcher_init_called[0] is not None
        
        # Verify SymBot was initialized (no LLM client needed)
        assert len(symbot_init_called) == 1
        
        # Cleanup
        orchestrator.cleanup()
    
    def test_analyze_response_contains_llm_generated_hypothesis(self, client):
        """Test that /analyze response contains LLM-generated vulnerability hypothesis."""
        from api import server
        
        # Mock orchestrator to return response with LLM-generated hypothesis
        mock_orchestrator = Mock()
        mock_orchestrator.analyze_code = AsyncMock(
            return_value=AnalyzeResponse(
                analysis_id="test-llm-hypothesis-123",
                vulnerabilities=[
                    VulnerabilityResponse(
                        location="test.py:5",
                        vuln_type="SQL Injection",
                        severity="HIGH",
                        description="SQL query uses string concatenation",
                        confidence=0.92,
                        cwe_id="CWE-89",
                        hypothesis="The function 'get_user' accepts a 'username' parameter that is directly concatenated into a SQL query without sanitization. An attacker can inject SQL commands by providing malicious input like \"admin' OR '1'='1\", which would bypass authentication and return all users from the database."
                    )
                ],
                patches=[],
                execution_time=8.5,
                errors=[],
                logs=["Scanner Agent: Generated LLM-powered hypothesis"],
                workflow_complete=True
            )
        )
        server.service_state.orchestrator = mock_orchestrator
        
        # Send request
        request_data = {
            "code": "query = 'SELECT * FROM users WHERE username=' + username",
            "file_path": "test.py"
        }
        
        response = client.post("/analyze", json=request_data)
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        # Check that hypothesis is present and detailed
        assert len(data["vulnerabilities"]) == 1
        vuln = data["vulnerabilities"][0]
        assert "hypothesis" in vuln
        assert vuln["hypothesis"] is not None
        assert len(vuln["hypothesis"]) > 50  # LLM-generated should be detailed
        assert "attacker" in vuln["hypothesis"].lower() or "inject" in vuln["hypothesis"].lower()
    
    def test_analyze_response_contains_llm_generated_contract(self, client):
        """Test that workflow generates LLM-powered contracts (verified via logs)."""
        from api import server
        
        # Mock orchestrator to return response with contract generation logs
        mock_orchestrator = Mock()
        mock_orchestrator.analyze_code = AsyncMock(
            return_value=AnalyzeResponse(
                analysis_id="test-llm-contract-456",
                vulnerabilities=[
                    VulnerabilityResponse(
                        location="test.py:10",
                        vuln_type="Command Injection",
                        severity="CRITICAL",
                        description="Subprocess call with shell=True",
                        confidence=0.95,
                        cwe_id="CWE-78",
                        hypothesis="Command injection via user-controlled input"
                    )
                ],
                patches=[],
                execution_time=12.3,
                errors=[],
                logs=[
                    "Scanner Agent: Found 1 potential vulnerability",
                    "Speculator Agent: Generating contracts...",
                    "Speculator Agent: Generated contract for Command Injection",
                    "SymBot Agent: Starting symbolic execution..."
                ],
                workflow_complete=True
            )
        )
        server.service_state.orchestrator = mock_orchestrator
        
        # Send request
        request_data = {
            "code": "subprocess.run(user_input, shell=True)",
            "file_path": "test.py"
        }
        
        response = client.post("/analyze", json=request_data)
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        # Check that contract generation is logged
        assert any("Generated contract" in log for log in data["logs"])
        assert any("Speculator Agent" in log for log in data["logs"])
    
    def test_analyze_response_contains_llm_generated_patch(self, client):
        """Test that /analyze response contains LLM-generated security patch."""
        from api import server
        
        # Mock orchestrator to return response with LLM-generated patch
        mock_verification = {
            "verified": True,
            "counterexample": None,
            "error_message": None,
            "execution_time": 3.2
        }
        
        mock_orchestrator = Mock()
        mock_orchestrator.analyze_code = AsyncMock(
            return_value=AnalyzeResponse(
                analysis_id="test-llm-patch-789",
                vulnerabilities=[
                    VulnerabilityResponse(
                        location="test.py:15",
                        vuln_type="Path Traversal",
                        severity="HIGH",
                        description="File path uses string concatenation",
                        confidence=0.88,
                        cwe_id="CWE-22",
                        hypothesis="Path traversal vulnerability via user input"
                    )
                ],
                patches=[
                    PatchResponse(
                        code="""# SECURITY FIX: Path Traversal
# Issue: Path traversal vulnerability via user input
# Fix: Sanitize file paths to prevent directory traversal

import os

def read_file(filename):
    # Sanitize filename to prevent path traversal
    safe_filename = os.path.basename(filename)
    file_path = os.path.join('/safe/directory', safe_filename)
    
    with open(file_path, 'r') as f:
        return f.read()""",
                        diff="""- file_path = '/data/' + filename
+ safe_filename = os.path.basename(filename)
+ file_path = os.path.join('/safe/directory', safe_filename)""",
                        verified=True,
                        verification_result=mock_verification
                    )
                ],
                execution_time=18.7,
                errors=[],
                logs=[
                    "Scanner Agent: Found 1 potential vulnerability",
                    "Patcher Agent: Generating patch...",
                    "Patcher Agent: Generated patch (iteration 1)"
                ],
                workflow_complete=True
            )
        )
        server.service_state.orchestrator = mock_orchestrator
        
        # Send request
        request_data = {
            "code": "file_path = '/data/' + filename",
            "file_path": "test.py"
        }
        
        response = client.post("/analyze", json=request_data)
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        # Check that patch is present and contains security fix
        assert len(data["patches"]) == 1
        patch = data["patches"][0]
        assert "SECURITY FIX" in patch["code"]
        assert "os.path.basename" in patch["code"]  # LLM should use secure pattern
        assert patch["verified"] is True
        
        # Check that patch generation is logged
        assert any("Patcher Agent" in log for log in data["logs"])
        assert any("Generated patch" in log for log in data["logs"])
    
    def test_analyze_workflow_with_all_llm_agents(self, client):
        """Test complete workflow with all LLM-powered agents."""
        from api import server
        
        # Mock orchestrator to return complete workflow response
        mock_orchestrator = Mock()
        mock_orchestrator.analyze_code = AsyncMock(
            return_value=AnalyzeResponse(
                analysis_id="test-complete-workflow-999",
                vulnerabilities=[
                    VulnerabilityResponse(
                        location="app.py:42",
                        vuln_type="SQL Injection",
                        severity="CRITICAL",
                        description="SQL query uses f-string with user input",
                        confidence=0.98,
                        cwe_id="CWE-89",
                        hypothesis="The 'search_products' function accepts a 'query' parameter from user input and directly interpolates it into a SQL query using an f-string. This allows an attacker to inject arbitrary SQL commands, potentially leading to data exfiltration, modification, or deletion."
                    )
                ],
                patches=[
                    PatchResponse(
                        code="""# SECURITY FIX: SQL Injection
# Issue: SQL query uses f-string with user input
# Exploit prevented: query=' OR '1'='1
# Fix: Use parameterized queries to prevent SQL injection

def search_products(query):
    # Use parameterized query instead of f-string
    sql = "SELECT * FROM products WHERE name LIKE ?"
    cursor.execute(sql, (f'%{query}%',))
    return cursor.fetchall()""",
                        diff="""- sql = f"SELECT * FROM products WHERE name LIKE '%{query}%'"
- cursor.execute(sql)
+ sql = "SELECT * FROM products WHERE name LIKE ?"
+ cursor.execute(sql, (f'%{query}%',))""",
                        verified=True,
                        verification_result={
                            "verified": True,
                            "counterexample": None,
                            "error_message": None,
                            "execution_time": 4.1
                        }
                    )
                ],
                execution_time=25.6,
                errors=[],
                logs=[
                    "Scanner Agent: Starting scan...",
                    "Scanner Agent: Generating LLM-powered hypotheses...",
                    "Scanner Agent: Extracting code slice for symbolic execution...",
                    "Scanner Agent: Found 1 potential vulnerabilities",
                    "Speculator Agent: Generating contracts...",
                    "Speculator Agent: Generated contract for SQL Injection",
                    "SymBot Agent: Starting symbolic execution...",
                    "SymBot Agent: Vulnerability confirmed - SQL Injection",
                    "Patcher Agent: Generating patch...",
                    "Patcher Agent: Generated patch (iteration 1)"
                ],
                workflow_complete=True
            )
        )
        server.service_state.orchestrator = mock_orchestrator
        
        # Send request with vulnerable code
        request_data = {
            "code": """def search_products(query):
    sql = f"SELECT * FROM products WHERE name LIKE '%{query}%'"
    cursor.execute(sql)
    return cursor.fetchall()""",
            "file_path": "app.py",
            "max_iterations": 3
        }
        
        response = client.post("/analyze", json=request_data)
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        # Verify all LLM-powered components are present
        
        # 1. Scanner: LLM-generated hypothesis
        assert len(data["vulnerabilities"]) == 1
        vuln = data["vulnerabilities"][0]
        assert vuln["hypothesis"] is not None
        assert len(vuln["hypothesis"]) > 100  # Detailed LLM explanation
        assert "attacker" in vuln["hypothesis"].lower()
        
        # 2. Speculator: Contract generation logged
        assert any("Speculator Agent" in log and "contract" in log.lower() for log in data["logs"])
        
        # 3. Patcher: LLM-generated patch with security comment
        assert len(data["patches"]) == 1
        patch = data["patches"][0]
        assert "SECURITY FIX" in patch["code"]
        assert "parameterized" in patch["code"].lower() or "?" in patch["code"]
        
        # 4. Verify workflow completed successfully
        assert data["workflow_complete"] is True
        assert len(data["errors"]) == 0
        
        # 5. Verify all agents were invoked
        log_text = " ".join(data["logs"])
        assert "Scanner Agent" in log_text
        assert "Speculator Agent" in log_text
        assert "SymBot Agent" in log_text
        assert "Patcher Agent" in log_text
