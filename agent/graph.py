"""
SecureCodeAI - LangGraph Workflow
Defines the 4-agent cyclic state machine for vulnerability detection and patching.
"""

import os
import logging
from typing import Dict, Any, Literal, Optional
from langgraph.graph import StateGraph, END

from .state import AgentState
from .nodes.scanner import ScannerAgent
from .nodes.speculator import SpeculatorAgent
from .nodes.symbot import SymBotAgent
from .nodes.patcher import PatcherAgent
from .nodes.workflow_nodes import (
    semantic_scanner_node,
    validator_suite_node,
    merge_results_node
)

logger = logging.getLogger(__name__)

# Optional imports - may fail on Windows or when SKIP_ANGR is set
SKIP_ANGR = os.getenv("SKIP_ANGR", "false").lower() == "true"

if not SKIP_ANGR:
    try:
        from .nodes.binary_analyzer import BinaryAnalyzerAgent
        BINARY_ANALYZER_AVAILABLE = True
    except ImportError as e:
        print(f"Warning: BinaryAnalyzerAgent not available: {e}")
        BINARY_ANALYZER_AVAILABLE = False
        BinaryAnalyzerAgent = None
else:
    print("Info: Skipping BinaryAnalyzerAgent (SKIP_ANGR=true)")
    BINARY_ANALYZER_AVAILABLE = False
    BinaryAnalyzerAgent = None

try:
    from .nodes.smart_contract import SmartContractAgent
    SMART_CONTRACT_AVAILABLE = True
except ImportError as e:
    print(f"Warning: SmartContractAgent not available: {e}")
    SMART_CONTRACT_AVAILABLE = False
    SmartContractAgent = None


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
    semantic_scanner=None,
    validator_suite=None,
) -> StateGraph:
    """
    Create the SecureCodeAI LangGraph workflow.
    
    Workflow:
    1. Scanner: Identify vulnerability hotspots using static analysis + LLM
    2. Semantic Scanner (optional): Detect bugs using RAG-based semantic matching
    3. Validator Suite (optional): Run specialized validators (hardware, lifecycle, API)
    4. Merge Results: Combine static and semantic vulnerabilities
    5. Speculator: Generate formal contracts (hypotheses)
    6. SymBot: Verify with symbolic execution (CrossHair/Angr)
    7. Patcher: Generate and verify patch
    8. Loop back to SymBot if patch fails verification
    
    Args:
        scanner: Scanner agent instance
        speculator: Speculator agent instance
        symbot: SymBot agent instance
        patcher: Patcher agent instance
        binary_analyzer: Binary analyzer agent instance
        smart_contract_agent: Smart contract agent instance
        semantic_scanner: Optional semantic scanner instance
        validator_suite: Optional validator suite instance
        
    Returns:
        Compiled LangGraph workflow
        
    Validates: Requirements 3.1, 3.2, 3.3, 3.4
    """
    # Initialize state graph
    workflow = StateGraph(AgentState)
    
    # Add scanner node with error handling wrapper for graceful degradation
    def scanner_wrapper(state: AgentState) -> AgentState:
        """Wrapper for scanner with error handling for graceful degradation."""
        try:
            return scanner.execute(state)
        except Exception as e:
            # Handle errors gracefully - don't fail the entire workflow
            error_msg = f"Scanner Agent: Error - {str(e)}"
            logger.error(error_msg, exc_info=True)
            state["errors"].append(error_msg)
            state["logs"].append("Scanner Agent: Failed, continuing with empty results")
            # Ensure vulnerabilities field exists even on failure
            if "vulnerabilities" not in state:
                state["vulnerabilities"] = []
            return state
    
    # Add existing nodes
    workflow.add_node("scanner", scanner_wrapper)
    workflow.add_node("speculator", speculator.execute)
    workflow.add_node("symbot", symbot.execute)
    workflow.add_node("patcher", patcher.execute)
    
    # Add optional agents only if available
    if binary_analyzer is not None:
        workflow.add_node("binary_analyzer", binary_analyzer.execute)
    if smart_contract_agent is not None:
        workflow.add_node("smart_contract_agent", smart_contract_agent.execute)
    
    # Add new semantic scanning nodes (if enabled)
    if semantic_scanner is not None:
        # Create wrapper functions that pass the scanner/validator instances
        async def semantic_scanner_wrapper(state: AgentState) -> AgentState:
            return await semantic_scanner_node(state, semantic_scanner)
        
        workflow.add_node("semantic_scanner", semantic_scanner_wrapper)
    
    if validator_suite is not None:
        def validator_suite_wrapper(state: AgentState) -> AgentState:
            return validator_suite_node(state, validator_suite)
        
        workflow.add_node("validator_suite", validator_suite_wrapper)
    
    # Always add merge_results node (handles case when semantic scanner is disabled)
    workflow.add_node("merge_results", merge_results_node)
    
    def route_start(state: AgentState) -> Literal["scanner", "binary_analyzer", "smart_contract_agent"]:
        if state.get("binary_path") and binary_analyzer is not None:
            return "binary_analyzer"
        if state.get("file_path", "").endswith(".sol") and smart_contract_agent is not None:
            return "smart_contract_agent"
        return "scanner"

    # Build conditional entry point map - only include available agents
    entry_map = {"scanner": "scanner"}
    if binary_analyzer is not None:
        entry_map["binary_analyzer"] = "binary_analyzer"
    if smart_contract_agent is not None:
        entry_map["smart_contract_agent"] = "smart_contract_agent"

    # Set entry point
    workflow.set_conditional_entry_point(
        route_start,
        entry_map
    )
    
    # Add edges only for available optional agents
    if binary_analyzer is not None:
        workflow.add_edge("binary_analyzer", END)
    if smart_contract_agent is not None:
        workflow.add_edge("smart_contract_agent", END)
    
    # Configure workflow based on whether semantic scanning is enabled
    # Requirements 3.1, 3.2, 3.3, 3.4: Sequential execution with graceful degradation
    # Note: True parallel execution would require Annotated state keys in LangGraph
    if semantic_scanner is not None:
        # Sequential execution: scanner -> semantic_scanner -> merge_results
        # This provides the same benefits (both scanners run) with graceful degradation
        workflow.add_edge("scanner", "semantic_scanner")
        
        # Run validator suite after semantic scanner
        if validator_suite is not None:
            workflow.add_edge("semantic_scanner", "validator_suite")
            workflow.add_edge("validator_suite", "merge_results")
        else:
            workflow.add_edge("semantic_scanner", "merge_results")
    else:
        # No semantic scanning: scanner goes directly to merge_results
        # Merge node handles case when semantic results are empty
        workflow.add_edge("scanner", "merge_results")
    
    # After merging results, route based on vulnerabilities found
    workflow.add_conditional_edges(
        "merge_results",
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


def run_analysis(
    code: str,
    file_path: str = "unknown",
    semantic_scanner=None,
    validator_suite=None
) -> AgentState:
    """
    Convenience function to run full analysis on code.
    
    Args:
        code: Source code to analyze
        file_path: Path to the file (for context)
        semantic_scanner: Optional semantic scanner instance
        validator_suite: Optional validator suite instance
        
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
    
    # Create workflow with optional semantic components
    app = create_workflow(
        scanner,
        speculator,
        symbot,
        patcher,
        binary_analyzer,
        smart_contract_agent,
        semantic_scanner=semantic_scanner,
        validator_suite=validator_suite
    )
    
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
