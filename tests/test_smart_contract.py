import os
import logging
from agent.nodes.smart_contract import SmartContractAgent
from agent.state import AgentState

# Configure logging
logging.basicConfig(level=logging.INFO)

def test_smart_contract_analysis():
    sol_path = os.path.abspath("tests/vulnerable.sol")
    if not os.path.exists(sol_path):
        print(f"Error: Contract not found at {sol_path}")
        return

    print(f"Testing SmartContractAgent with {sol_path}...")
    
    with open(sol_path, 'r') as f:
        code = f.read()
    
    agent = SmartContractAgent()
    
    # Mock state
    state = AgentState(
        file_path=sol_path,
        code=code,
        vulnerabilities=[],
        logs=[]
    )
    
    # Execute
    result = agent.execute(state)
    
    # Check results
    vulns = result.get("vulnerabilities", [])
    print(f"Found {len(vulns)} vulnerabilities.")
    
    expected_issues = ["Reentrancy", "Tx.Origin Authorization", "Block Timestamp Dependence"]
    found_issues = [v.vuln_type for v in vulns]
    
    for issue in expected_issues:
        if issue in found_issues:
            print(f"SUCCESS: Detected {issue}")
        else:
            print(f"FAILURE: Missed {issue}")

if __name__ == "__main__":
    test_smart_contract_analysis()
