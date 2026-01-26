"""
SecureCodeAI - Workflow Orchestrator
Orchestrates the LangGraph workflow for vulnerability detection and patching.
"""

import asyncio
import time
import uuid
import logging
from typing import Optional
from datetime import datetime

from agent.graph import create_workflow
from agent.state import AgentState
from agent.nodes.scanner import ScannerAgent
from agent.nodes.speculator import SpeculatorAgent
from agent.nodes.symbot import SymBotAgent
from agent.nodes.patcher import PatcherAgent
from agent.nodes.binary_analyzer import BinaryAnalyzerAgent
from agent.nodes.smart_contract import SmartContractAgent
from agent.llm_client import LLMClient

from api.vllm_client import initialize_vllm, get_vllm_client, VLLMClient
from api.local_llm_client import LlamaCppClient
from api.gemini_client import GeminiClient
from api.config import config
from .models import AnalyzeResponse, VulnerabilityResponse, PatchResponse


logger = logging.getLogger(__name__)


class WorkflowOrchestrator:
    """
    Orchestrates the SecureCodeAI workflow.
    
    Manages agent initialization, workflow execution, and result conversion.
    """
    
    def __init__(self, vllm_client: Optional[VLLMClient] = None):
        """
        Initialize workflow orchestrator.
        
        Args:
            vllm_client: vLLM client for LLM inference (optional)
        """
        self.vllm_client = vllm_client
        self.llm_client = None  # Will be created during initialization
        self._workflow = None
        self._initialized = False
    
    def initialize(self) -> None:
        """
        Initialize agents and workflow.
        
        Raises:
            Exception: If initialization fails
        """
        if self._initialized:
            return
        
        try:
            # Initialize LLM client
            try:
                if config.use_gemini:
                    logger.info("Initializing Gemini Cloud Client...")
                    self.llm_client = GeminiClient()
                    self.llm_client.initialize()
                elif config.use_local_llm:
                    logger.info("Initializing Local GGUF Client...")
                    self.llm_client = LlamaCppClient()
                    self.llm_client.initialize()
                else:
                    logger.info("Initializing vLLM Client...")
                    self.llm_client = get_vllm_client()
                    if not self.llm_client.is_initialized():
                        self.llm_client.initialize()
            except Exception as e:
                logger.warning(f"Failed to initialize LLM client: {e}")
                logger.warning("Continuing without LLM intelligence (basic mode)")
                self.llm_client = None
            
            # Initialize agents with LLMClient
            # Scanner, Speculator, and Patcher get LLM client for intelligence
            # SymBot remains unchanged (no LLM needed for symbolic execution)
            scanner = ScannerAgent(llm_client=self.llm_client)
            speculator = SpeculatorAgent(llm_client=self.llm_client)
            symbot = SymBotAgent()
            patcher = PatcherAgent(llm_client=self.llm_client)
            binary_analyzer = BinaryAnalyzerAgent()
            smart_contract_agent = SmartContractAgent()
            
            logger.info("Agents initialized with LLM intelligence")
            
            # Create workflow
            self._workflow = create_workflow(scanner, speculator, symbot, patcher, binary_analyzer, smart_contract_agent)
            
            self._initialized = True
            logger.info("Workflow orchestrator initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize workflow: {e}")
            raise Exception(f"Failed to initialize workflow: {e}")
    
    def is_initialized(self) -> bool:
        """Check if workflow is initialized."""
        return self._initialized
    
    async def analyze_code(
        self,
        code: str,
        file_path: str = "unknown",
        max_iterations: int = 3
    ) -> AnalyzeResponse:
        """
        Analyze code for vulnerabilities and generate patches.
        
        Args:
            code: Source code to analyze
            file_path: File path for context
            max_iterations: Maximum patch refinement iterations
            
        Returns:
            AnalyzeResponse with vulnerabilities and patches
            
        Raises:
            Exception: If workflow execution fails
        """
        # Ensure workflow is initialized
        if not self._initialized:
            self.initialize()
        
        # Generate analysis ID
        analysis_id = str(uuid.uuid4())
        start_time = time.time()
        
        try:
            # Create initial state
            initial_state = self._create_initial_state(
                code=code,
                file_path=file_path,
                max_iterations=max_iterations
            )
            
            # Run workflow asynchronously
            final_state = await self._run_workflow_async(initial_state)
            
            # Calculate execution time
            execution_time = time.time() - start_time
            final_state["total_execution_time"] = execution_time
            
            # Convert state to response
            response = self._state_to_response(
                state=final_state,
                analysis_id=analysis_id,
                execution_time=execution_time
            )
            
            return response
            
        except Exception as e:
            # Handle workflow errors
            execution_time = time.time() - start_time
            
            return AnalyzeResponse(
                analysis_id=analysis_id,
                vulnerabilities=[],
                patches=[],
                execution_time=execution_time,
                errors=[f"Workflow execution failed: {str(e)}"],
                logs=[],
                workflow_complete=False
            )
    
    def _create_initial_state(
        self,
        code: str,
        file_path: str,
        max_iterations: int
    ) -> AgentState:
        """
        Create initial workflow state.
        
        Args:
            code: Source code to analyze
            file_path: File path for context
            max_iterations: Maximum patch refinement iterations
            
        Returns:
            Initial AgentState
        """
        return {
            "code": code,
            "file_path": file_path,
            "vulnerabilities": [],
            "contracts": [],
            "verification_results": [],
            "patches": [],
            "iteration_count": 0,
            "max_iterations": max_iterations,
            "workflow_complete": False,
            "errors": [],
            "logs": [],
            "total_execution_time": 0.0
        }
    
    async def _run_workflow_async(self, initial_state: AgentState) -> AgentState:
        """
        Run workflow asynchronously.
        
        Args:
            initial_state: Initial workflow state
            
        Returns:
            Final workflow state
        """
        # Run synchronous workflow in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        final_state = await loop.run_in_executor(
            None,
            self._workflow.invoke,
            initial_state
        )
        
        return final_state
    
    def _state_to_response(
        self,
        state: AgentState,
        analysis_id: str,
        execution_time: float
    ) -> AnalyzeResponse:
        """
        Convert AgentState to AnalyzeResponse.
        
        Args:
            state: Final workflow state
            analysis_id: Unique analysis identifier
            execution_time: Total execution time
            
        Returns:
            AnalyzeResponse
        """
        # Convert vulnerabilities
        vulnerabilities = []
        for vuln in state.get("vulnerabilities", []):
            vulnerabilities.append(
                VulnerabilityResponse(
                    location=vuln.location,
                    vuln_type=vuln.vuln_type,
                    severity=vuln.severity,
                    description=vuln.description,
                    confidence=vuln.confidence,
                    cwe_id=vuln.cwe_id,
                    hypothesis=vuln.hypothesis
                )
            )
        
        # Convert patches
        patches = []
        for patch in state.get("patches", []):
            verification_result = None
            if patch.verification_result:
                verification_result = {
                    "verified": patch.verification_result.verified,
                    "counterexample": patch.verification_result.counterexample,
                    "error_message": patch.verification_result.error_message,
                    "execution_time": patch.verification_result.execution_time
                }
            
            patches.append(
                PatchResponse(
                    code=patch.code,
                    diff=patch.diff,
                    verified=patch.verified,
                    verification_result=verification_result
                )
            )
        
        # Get errors and logs
        errors = state.get("errors", [])
        logs = state.get("logs", [])
        workflow_complete = state.get("workflow_complete", False)
        
        return AnalyzeResponse(
            analysis_id=analysis_id,
            vulnerabilities=vulnerabilities,
            patches=patches,
            execution_time=execution_time,
            errors=errors,
            logs=logs,
            workflow_complete=workflow_complete
        )
    
    def cleanup(self) -> None:
        """Cleanup workflow resources."""
        self._workflow = None
        self._initialized = False


# Global orchestrator instance
_orchestrator: Optional[WorkflowOrchestrator] = None


def get_orchestrator(vllm_client: Optional[VLLMClient] = None) -> WorkflowOrchestrator:
    """
    Get or create global workflow orchestrator.
    
    Args:
        vllm_client: vLLM client for LLM inference (optional)
        
    Returns:
        Global WorkflowOrchestrator instance
    """
    global _orchestrator
    
    if _orchestrator is None:
        _orchestrator = WorkflowOrchestrator(vllm_client=vllm_client)
    
    return _orchestrator


def initialize_orchestrator(vllm_client: Optional[VLLMClient] = None) -> WorkflowOrchestrator:
    """
    Initialize global workflow orchestrator.
    
    Args:
        vllm_client: vLLM client for LLM inference (optional)
        
    Returns:
        Initialized WorkflowOrchestrator instance
        
    Raises:
        Exception: If initialization fails
    """
    orchestrator = get_orchestrator(vllm_client)
    orchestrator.initialize()
    return orchestrator
