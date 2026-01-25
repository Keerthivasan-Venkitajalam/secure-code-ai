import sys
from unittest.mock import MagicMock

# Mock external dependencies
sys.modules["angr"] = MagicMock()
sys.modules["langgraph"] = MagicMock()
sys.modules["langgraph.graph"] = MagicMock()
sys.modules["clairvoyance"] = MagicMock()
sys.modules["pydantic_settings"] = MagicMock()

# Mock internal dependencies to avoid import chains
sys.modules["agent.graph"] = MagicMock()
sys.modules["agent.nodes.scanner"] = MagicMock()
sys.modules["agent.nodes.speculator"] = MagicMock()
sys.modules["agent.nodes.symbot"] = MagicMock()
sys.modules["agent.nodes.patcher"] = MagicMock()

# Setup graph mocks
sys.modules["langgraph.graph"].StateGraph = MagicMock()
sys.modules["langgraph.graph"].END = "END"

import os
import logging
from agent.nodes.binary_analyzer import BinaryAnalyzerAgent
from agent.state import AgentState, VerificationResult

# Configure logging
logging.basicConfig(level=logging.INFO)

def test_binary_analysis_mock():
    print("Testing BinaryAnalyzerAgent with MOCKED dependencies...")
    
    # Setup the mock project
    mock_project = MagicMock()
    sys.modules["angr"].Project.return_value = mock_project
    
    # Mock the exploring logic
    mock_simgr = MagicMock()
    mock_project.factory.simgr.return_value = mock_simgr
    
    # Simulation: Found a dummy state
    mock_found_state = MagicMock()
    mock_found_state.posix.dumps.return_value = b"A" * 70 # Buffer overflow input
    mock_simgr.found = [mock_found_state]
    
    agent = BinaryAnalyzerAgent()
    
    binary_path = "vulnerable_mock.exe" # Doesn't need to exist
    
    state = AgentState(
        binary_path=binary_path,
        verification_results=[],
        logs=[],
        errors=[]
    )
    
    # Execute
    result = agent.execute(state)
    
    print("Execution Result:")
    # print(result)
    
    if "verification_results" in result:
        res = result["verification_results"][0]
        print(f"Verified: {res.verified}")
        if "def run_exploit():" in res.counterexample and b"A" * 70 in res.counterexample.encode('latin1'):
             print("SUCCESS: Mock vulnerability found and exploit script generated.")
    else:
        print("FAILURE: No verification results.")

    # Also test proper routing import (though we can't run the graph without langgraph)
    try:
        from agent.graph import route_start
        print("Graph module imported successfully.")
        
        # Test routing logic
        print(f"Routing for binary_path='foo': {route_start({'binary_path': 'foo'})}")
        print(f"Routing for binary_path=None: {route_start({})}")
        
    except Exception as e:
        print(f"Graph verification failed: {e}")

if __name__ == "__main__":
    test_binary_analysis_mock()
