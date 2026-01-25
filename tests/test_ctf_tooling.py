import os
from agent.nodes.binary_analyzer import BinaryAnalyzerAgent
from agent.state import AgentState

def test_ctf_flag_search():
    binary_path = os.path.abspath("tests/ctf_challenge.exe")
    if not os.path.exists(binary_path):
        print(f"Error: Binary not found at {binary_path}")
        return

    print(f"Running CTF Tooling Test on {binary_path}...")
    
    agent = BinaryAnalyzerAgent()
    
    # Mock state
    state = AgentState(
        binary_path=binary_path,
        verification_results=[],
        logs=[],
        errors=[]
    )
    
    # Execute
    result = agent.execute(state)
    
    # Check logs for flag
    logs = result.get("logs", [])
    flag_found = False
    for log in logs:
        print(f"Log: {log}")
        if "CTF{" in log:
            flag_found = True
            
    if flag_found:
        print("SUCCESS: Flag found by BinaryAnalyzerAgent!")
    else:
        print("FAILURE: Flag not detected.")

if __name__ == "__main__":
    test_ctf_flag_search()
