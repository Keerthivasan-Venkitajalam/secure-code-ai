"""
Workflow nodes for semantic scanning and validation integration.

This module provides LangGraph nodes for:
- Semantic scanner integration
- Validator suite integration
- Result merging from multiple scanners
"""

import logging
from typing import List, Set, Tuple

from ..state import (
    AgentState,
    SemanticVulnerability,
    HardwareViolation,
    LifecycleViolation,
    APITypoSuggestion,
    Vulnerability
)
from .semantic_scanner import SemanticScanner
from ..validators.validator_suite import ValidatorSuite

logger = logging.getLogger(__name__)


async def semantic_scanner_node(
    state: AgentState,
    semantic_scanner: SemanticScanner
) -> AgentState:
    """
    LangGraph node for semantic bug detection.
    
    Extracts code and file_path from state, runs semantic scanner,
    and updates state with semantic vulnerabilities.
    
    Args:
        state: Current workflow state
        semantic_scanner: Initialized semantic scanner instance
        
    Returns:
        Updated state with semantic_vulnerabilities populated
        
    Validates: Requirements 1.1, 3.1, 10.1
    """
    state["logs"].append("Semantic Scanner Node: Starting semantic analysis...")
    
    try:
        # Extract code and file_path from state
        code = state.get("code", "")
        file_path = state.get("file_path", "unknown")
        
        # Validate inputs
        if not code or not code.strip():
            state["logs"].append("Semantic Scanner Node: Empty code, skipping scan")
            state["semantic_vulnerabilities"] = []
            return state
        
        # Run semantic scanner
        logger.info(f"Running semantic scan on {file_path}")
        semantic_vulnerabilities = await semantic_scanner.scan(code, file_path)
        
        # Update state with results
        state["semantic_vulnerabilities"] = semantic_vulnerabilities
        state["logs"].append(
            f"Semantic Scanner Node: Found {len(semantic_vulnerabilities)} "
            f"semantic vulnerabilities"
        )
        
        logger.info(
            f"Semantic scan complete: {len(semantic_vulnerabilities)} vulnerabilities found"
        )
        
    except Exception as e:
        # Handle errors gracefully - don't fail the entire workflow
        error_msg = f"Semantic Scanner Node: Error - {str(e)}"
        logger.error(error_msg, exc_info=True)
        state["errors"].append(error_msg)
        state["semantic_vulnerabilities"] = []
        state["logs"].append("Semantic Scanner Node: Failed, continuing with empty results")
    
    return state


def validator_suite_node(
    state: AgentState,
    validator_suite: ValidatorSuite
) -> AgentState:
    """
    LangGraph node for specialized validation.
    
    Extracts code from state, runs validator suite (hardware, lifecycle, API typo),
    and updates state with validation results.
    
    Args:
        state: Current workflow state
        validator_suite: Initialized validator suite instance
        
    Returns:
        Updated state with validation results populated
        
    Validates: Requirements 4.1, 5.1, 6.1, 10.1
    """
    state["logs"].append("Validator Suite Node: Starting validation...")
    
    try:
        # Extract code from state
        code = state.get("code", "")
        
        # Validate input
        if not code or not code.strip():
            state["logs"].append("Validator Suite Node: Empty code, skipping validation")
            state["hardware_violations"] = []
            state["lifecycle_violations"] = []
            state["api_typo_suggestions"] = []
            return state
        
        # Run validator suite
        logger.info("Running validator suite")
        validation_results = validator_suite.validate(code)
        
        # Update state with results
        state["hardware_violations"] = validation_results.hardware_violations
        state["lifecycle_violations"] = validation_results.lifecycle_violations
        state["api_typo_suggestions"] = validation_results.api_typo_suggestions
        
        # Log results
        state["logs"].append(
            f"Validator Suite Node: Found {len(validation_results.hardware_violations)} "
            f"hardware violations, {len(validation_results.lifecycle_violations)} "
            f"lifecycle violations, {len(validation_results.api_typo_suggestions)} "
            f"API typo suggestions"
        )
        
        logger.info(
            f"Validation complete: {len(validation_results.hardware_violations)} hardware, "
            f"{len(validation_results.lifecycle_violations)} lifecycle, "
            f"{len(validation_results.api_typo_suggestions)} API typos"
        )
        
    except Exception as e:
        # Handle errors gracefully - don't fail the entire workflow
        error_msg = f"Validator Suite Node: Error - {str(e)}"
        logger.error(error_msg, exc_info=True)
        state["errors"].append(error_msg)
        state["hardware_violations"] = []
        state["lifecycle_violations"] = []
        state["api_typo_suggestions"] = []
        state["logs"].append("Validator Suite Node: Failed, continuing with empty results")
    
    return state


def merge_results_node(state: AgentState) -> AgentState:
    """
    LangGraph node for merging results from multiple scanners.
    
    Merges vulnerabilities from static scanner and semantic scanner,
    removing duplicates based on location and type while preserving
    metadata from both sources.
    
    Args:
        state: Current workflow state
        
    Returns:
        Updated state with merged vulnerabilities
        
    Validates: Requirements 3.2, 3.5
    """
    state["logs"].append("Merge Results Node: Merging scanner results...")
    
    try:
        # Get vulnerabilities from both scanners
        static_vulns = state.get("vulnerabilities", [])
        semantic_vulns = state.get("semantic_vulnerabilities", [])
        
        logger.info(
            f"Merging {len(static_vulns)} static vulnerabilities with "
            f"{len(semantic_vulns)} semantic vulnerabilities"
        )
        
        # Track seen (location, type) pairs to avoid duplicates
        seen_pairs: Set[Tuple[str, str]] = set()
        merged_vulns = []
        
        # Add static vulnerabilities first (deduplicate within static)
        for vuln in static_vulns:
            pair = (vuln.location, vuln.vuln_type)
            if pair not in seen_pairs:
                merged_vulns.append(vuln)
                seen_pairs.add(pair)
        
        # Add semantic vulnerabilities if not duplicates
        for sem_vuln in semantic_vulns:
            pair = (sem_vuln.location, sem_vuln.vuln_type)
            
            if pair not in seen_pairs:
                # Convert semantic vulnerability to standard Vulnerability
                standard_vuln = Vulnerability(
                    location=sem_vuln.location,
                    vuln_type=sem_vuln.vuln_type,
                    cwe_id=None,  # Semantic scanner doesn't provide CWE
                    severity=sem_vuln.severity.upper(),  # Normalize to uppercase
                    description=sem_vuln.description,
                    hypothesis=f"Semantic match (score: {sem_vuln.similarity_score:.2f}): "
                              f"{sem_vuln.description}",
                    confidence=sem_vuln.confidence
                )
                merged_vulns.append(standard_vuln)
                seen_pairs.add(pair)
            else:
                logger.debug(
                    f"Skipping duplicate vulnerability at {sem_vuln.location} "
                    f"({sem_vuln.vuln_type})"
                )
        
        # Update state with merged results
        state["vulnerabilities"] = merged_vulns
        
        duplicates_removed = len(static_vulns) + len(semantic_vulns) - len(merged_vulns)
        state["logs"].append(
            f"Merge Results Node: Merged to {len(merged_vulns)} total vulnerabilities "
            f"({duplicates_removed} duplicates removed)"
        )
        
        logger.info(
            f"Merge complete: {len(merged_vulns)} total vulnerabilities "
            f"({duplicates_removed} duplicates removed)"
        )
        
    except Exception as e:
        # Handle errors gracefully
        error_msg = f"Merge Results Node: Error - {str(e)}"
        logger.error(error_msg, exc_info=True)
        state["errors"].append(error_msg)
        state["logs"].append("Merge Results Node: Failed, keeping original vulnerabilities")
        # Keep original vulnerabilities if merge fails
    
    return state
