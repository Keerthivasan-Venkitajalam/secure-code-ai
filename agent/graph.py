"""
SecureCodeAI - LangGraph Workflow
Defines the 4-agent cyclic state machine for vulnerability detection and patching.
"""

from typing import Dict, Any, Literal
from langgraph.graph import StateGraph, END

from .state import AgentState
from .nodes.scanner import ScannerAgent
from .nodes.speculator import SpeculatorAgent
from .nodes.symbot import SymBotAgent
from .nodes.patcher import PatcherAgent
from .nodes.binary_analyzer import BinaryAnalyzerAgent
from .nodes.smart_contract import SmartContractAgent


def route_after_scan(state: AgentState) -> Literal["speculator", "end"]:
    """Route after Scanner: continue if vulnerabilities found."""
    if state.get("vulnerabilities") and len(state["vulnerabilities"]) > 0:
        return "speculator"
    else:
        return "end"


def route_after_verification(state: AgentState) -> Literal["patcher", "end"]:
    """Route after SymBot: patch if vulnerability confirmed."""
    if state.get("verification_results"):
        latest_result = state["verification_results"][-1]
        if not latest_result.verified and latest_result.counterexample:
            return "patcher"  # Vulnerability confirmed, generate patch
    return "end"


def route_after_patch(state: AgentState) -> Literal["symbot", "end", "speculator"]:
    """Route after Patcher: verify patch or retry."""
    iteration_count = state.get("iteration_count", 0)
    max_iterations = state.get("max_iterations", 3)
    
    if iteration_count >= max_iterations:
        # Max iterations reached, give up
        return "end"
    
    current_patch = state.get("current_patch")
    if current_patch and not current_patch.verified:
        # Patch needs verification
        return "symbot"
    elif current_patch and current_patch.verified:
        # Patch verified successfully
        return "end"
    else:
        # Patch generation failed, retry with refined hypothesis
        return "speculator"


def create_workflow(
    scanner: ScannerAgent,
    speculator: SpeculatorAgent,
    symbot: SymBotAgent,
    patcher: PatcherAgent,
    binary_analyzer: BinaryAnalyzerAgent,
    smart_contract_agent: SmartContractAgent,
) -> StateGraph:


    """
    Create the SecureCodeAI LangGraph workflow.
    
    Workflow:
    1. Scanner: Identify vulnerability hotspots using static analysis + LLM
    2. Speculator: Generate formal contracts (hypotheses)
    3. SymBot: Verify with symbolic execution (CrossHair/Angr)
    4. Patcher: Generate and verify patch
    5. Loop back to SymBot if patch fails verification
    
    Args:
        scanner: Scanner agent instance
        speculator: Speculator agent instance
        symbot: SymBot agent instance
        patcher: Patcher agent instance
        
    Returns:
        Compiled LangGraph workflow
    """
    # Initialize state graph
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("scanner", scanner.execute)
    workflow.add_node("speculator", speculator.execute)
    workflow.add_node("symbot", symbot.execute)
    workflow.add_node("patcher", patcher.execute)
    workflow.add_node("binary_analyzer", binary_analyzer.execute)
    workflow.add_node("smart_contract_agent", smart_contract_agent.execute)
    
    def route_start(state: AgentState) -> Literal["scanner", "binary_analyzer", "smart_contract_agent"]:
        if state.get("binary_path"):
            return "binary_analyzer"
        if state.get("file_path", "").endswith(".sol"):
            return "smart_contract_agent"
        return "scanner"

    # Set entry point
    workflow.set_conditional_entry_point(
        route_start,
        {
            "scanner": "scanner",
            "binary_analyzer": "binary_analyzer",
            "smart_contract_agent": "smart_contract_agent"
        }
    )
    
    workflow.add_edge("binary_analyzer", END)
    workflow.add_edge("smart_contract_agent", END)
    
    # Add conditional edges
    workflow.add_conditional_edges(
        "scanner",
        route_after_scan,
        {
            "speculator": "speculator",
            "end": END
        }
    )
    
    workflow.add_edge("speculator", "symbot")
    
    workflow.add_conditional_edges(
        "symbot",
        route_after_verification,
        {
            "patcher": "patcher",
            "end": END
        }
    )
    
    workflow.add_conditional_edges(
        "patcher",
        route_after_patch,
        {
            "symbot": "symbot",
            "speculator": "speculator",
            "end": END
        }
    )
    
    # Compile workflow
    return workflow.compile()


def run_analysis(code: str, file_path: str = "unknown") -> AgentState:
    """
    Convenience function to run full analysis on code.
    
    Args:
        code: Source code to analyze
        file_path: Path to the file (for context)
        
    Returns:
        Final AgentState with all results
    """
    # Initialize agents
    scanner = ScannerAgent()
    speculator = SpeculatorAgent()
    symbot = SymBotAgent()
    patcher = PatcherAgent()
    binary_analyzer = BinaryAnalyzerAgent()
    smart_contract_agent = SmartContractAgent()
    
    # Create workflow
    app = create_workflow(scanner, speculator, symbot, patcher, binary_analyzer, smart_contract_agent)
    
    # Initialize state
    initial_state: AgentState = {
        "code": code,
        "file_path": file_path,
        "vulnerabilities": [],
        "contracts": [],
        "verification_results": [],
        "patches": [],
        "iteration_count": 0,
        "max_iterations": 3,
        "workflow_complete": False,
        "errors": [],
        "logs": [],
        "total_execution_time": 0.0
    }
    
    # Run workflow
    final_state = app.invoke(initial_state)
    
    return final_state
