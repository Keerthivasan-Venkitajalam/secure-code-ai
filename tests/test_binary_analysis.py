import sys
import os
import logging
from agent.nodes.binary_analyzer import BinaryAnalyzerAgent
from agent.state import AgentState

# Configure logging
logging.basicConfig(level=logging.INFO)

def test_binary_analysis():
    binary_path = os.path.abspath("tests/vulnerable.exe")
    if not os.path.exists(binary_path):
        print(f"Error: Binary not found at {binary_path}")
        return

    print(f"Testing BinaryAnalyzerAgent with {binary_path}...")
    
    agent = BinaryAnalyzerAgent()
    
    # Create a mock state
    state = AgentState(
        binary_path=binary_path,
        verification_results=[],
        logs=[],
        errors=[]
    )
    
    # Execute agent
    result = agent.execute(state)
    
    # Check results
    if "errors" in result and result["errors"]:
        print("Analysis failed with errors:")
        for err in result["errors"]:
            print(f" - {err}")
    else:
        print("Analysis completed.")
        results = result.get("verification_results", [])
        print(f"Found {len(results)} results.")
        for res in results:
            print(f"Verified: {res.verified}")
            print(f"Error Message: {res.error_message}")
            if res.counterexample:
                print(f"Counterexample found!")
                # print(f"Counterexample data: {res.counterexample}")

if __name__ == "__main__":
    test_binary_analysis()
