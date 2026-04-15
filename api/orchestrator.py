"""
SecureCodeAI - Workflow Orchestrator
Orchestrates the LangGraph workflow for vulnerability detection and patching.
"""

import os
import asyncio
import time
import uuid
import logging
from typing import Optional, Any

from agent.graph import create_workflow
from agent.state import AgentState
from agent.nodes.scanner import ScannerAgent
from agent.nodes.speculator import SpeculatorAgent
from agent.nodes.symbot import SymBotAgent
from agent.nodes.patcher import PatcherAgent

# Optional imports - may fail on Windows
SKIP_ANGR = os.getenv("SKIP_ANGR", "false").lower() == "true"

if not SKIP_ANGR:
    try:
        from agent.nodes.binary_analyzer import BinaryAnalyzerAgent
    except ImportError:
        BinaryAnalyzerAgent = None
else:
    BinaryAnalyzerAgent = None

try:
    from agent.nodes.smart_contract import SmartContractAgent
except ImportError:
    SmartContractAgent = None

from agent.llm_client import LLMClient

from api.vllm_client import initialize_vllm, get_vllm_client, VLLMClient
from api.local_llm_client import LlamaCppClient
from api.gemini_client import GeminiClient
from api.ollama_client import OllamaClient
from api.config import config
from .models import AnalyzeResponse, VulnerabilityResponse, PatchResponse

# Lazy-resolved semantic symbols.
# Kept at module scope so tests can patch these attributes.
SemanticScanner = None
ValidatorSuite = None
KnowledgeBase = None
EmbeddingModel = None
VectorStore = None


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
        self.active_backend = "none"
        self.backend_ready = False
        
        # Semantic scanning components
        self.semantic_scanner: Optional[Any] = None
        self.validator_suite: Optional[Any] = None
    
    def initialize(self) -> None:
        """
        Initialize agents and workflow.
        
        Raises:
            Exception: If initialization fails
        """
        if self._initialized:
            return
        
        try:
            # Initialize LLM client - priority: Ollama > Gemini > Local GGUF > vLLM
            self.active_backend = "none"
            self.backend_ready = False
            try:
                if config.use_ollama:
                    self.active_backend = "ollama"
                    logger.info("Initializing Ollama Client...")
                    self.llm_client = OllamaClient(
                        model=config.ollama_model,
                        base_url=config.ollama_url
                    )
                    self.llm_client.initialize()
                    logger.info(f"Ollama client ready with model: {config.ollama_model}")
                elif config.use_gemini:
                    self.active_backend = "gemini"
                    logger.info("Initializing Gemini Cloud Client...")
                    self.llm_client = GeminiClient()
                    self.llm_client.initialize()
                elif config.use_local_llm:
                    self.active_backend = "local_llm"
                    logger.info("Initializing Local GGUF Client...")
                    self.llm_client = LlamaCppClient()
                    self.llm_client.initialize()
                else:
                    self.active_backend = "vllm"
                    logger.info("Initializing vLLM Client...")
                    self.llm_client = get_vllm_client()
                    if not self.llm_client.is_initialized():
                        self.llm_client.initialize()

                self.backend_ready = self.llm_client is not None
            except Exception as e:
                logger.warning(f"Failed to initialize LLM client: {e}")
                logger.warning("Continuing without LLM intelligence (basic mode)")
                self.llm_client = None
                self.backend_ready = False
            
            # Initialize semantic components if enabled
            if config.enable_semantic_scanning:
                try:
                    self._initialize_semantic_components()
                    logger.info("Semantic scanning components initialized successfully")
                except Exception as e:
                    logger.error(f"Failed to initialize semantic components: {e}")
                    logger.warning("Continuing without semantic scanning (graceful degradation)")
                    self.semantic_scanner = None
                    self.validator_suite = None
            else:
                logger.info("Semantic scanning disabled via configuration")
            
            # Initialize agents with LLMClient
            # Scanner, Speculator, and Patcher get LLM client for intelligence
            # SymBot remains unchanged (no LLM needed for symbolic execution)
            scanner = ScannerAgent(llm_client=self.llm_client)
            speculator = SpeculatorAgent(llm_client=self.llm_client)
            symbot = SymBotAgent()
            patcher = PatcherAgent(llm_client=self.llm_client)
            
            # Initialize optional agents (may be None if dependencies unavailable)
            binary_analyzer = BinaryAnalyzerAgent() if BinaryAnalyzerAgent is not None else None
            smart_contract_agent = SmartContractAgent() if SmartContractAgent is not None else None
            
            logger.info("Agents initialized with LLM intelligence")
            
            # Create workflow
            self._workflow = create_workflow(
                scanner,
                speculator,
                symbot,
                patcher,
                binary_analyzer,
                smart_contract_agent,
                semantic_scanner=self.semantic_scanner,
                validator_suite=self.validator_suite,
            )
            
            self._initialized = True
            logger.info("Workflow orchestrator initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize workflow: {e}")
            raise Exception(f"Failed to initialize workflow: {e}")
    
    def is_initialized(self) -> bool:
        """Check if workflow is initialized."""
        return self._initialized
    
    def _initialize_semantic_components(self) -> None:
        """
        Initialize semantic scanning components.
        
        This includes:
        - Knowledge base loading
        - Embedding model initialization
        - Vector store setup
        - Semantic scanner creation
        - Validator suite creation
        
        Raises:
            Exception: If initialization fails
        """
        logger.info("Initializing semantic scanning components...")
        
        try:
            # Lazy imports so missing semantic dependencies do not fail module import.
            global SemanticScanner, ValidatorSuite, KnowledgeBase, EmbeddingModel, VectorStore
            if SemanticScanner is None:
                from agent.nodes.semantic_scanner import SemanticScanner as _SemanticScanner
                SemanticScanner = _SemanticScanner
            if ValidatorSuite is None:
                from agent.validators.validator_suite import ValidatorSuite as _ValidatorSuite
                ValidatorSuite = _ValidatorSuite
            if KnowledgeBase is None:
                from agent.knowledge.knowledge_base import KnowledgeBase as _KnowledgeBase
                KnowledgeBase = _KnowledgeBase
            if EmbeddingModel is None:
                from agent.knowledge.embedding_model import EmbeddingModel as _EmbeddingModel
                EmbeddingModel = _EmbeddingModel
            if VectorStore is None:
                from agent.knowledge.vector_store import VectorStore as _VectorStore
                VectorStore = _VectorStore

            # Initialize knowledge base
            logger.debug(f"Loading knowledge base from {config.knowledge_base_path}")
            knowledge_base = KnowledgeBase(data_path=config.knowledge_base_path)
            knowledge_base.load_patterns()
            logger.info(f"Loaded {len(knowledge_base.patterns)} patterns from knowledge base")
            
            # Initialize embedding model
            logger.debug(f"Initializing embedding model: {config.embedding_model_name}")
            embedding_model = EmbeddingModel(
                model_name=config.embedding_model_name,
                model_path=config.embedding_model_path,
                device="cpu"  # Use CPU for now, can be configured later
            )
            logger.info("Embedding model initialized")
            
            # Initialize vector store
            logger.debug(f"Initializing vector store at {config.vector_store_path}")
            vector_store = VectorStore(
                persist_directory=config.vector_store_path,
                collection_name="bug_patterns"
            )
            
            # Check if vector store needs to be built
            stats = vector_store.get_stats()
            if stats.document_count == 0:
                logger.info("Vector store is empty, building from knowledge base...")
                self._build_vector_store(knowledge_base, embedding_model, vector_store)
            else:
                logger.info(f"Vector store loaded with {stats.document_count} documents")
            
            # Initialize semantic scanner
            self.semantic_scanner = SemanticScanner(
                knowledge_base=knowledge_base,
                embedding_model=embedding_model,
                vector_store=vector_store,
                similarity_threshold=config.similarity_threshold,
                top_k=config.top_k_results,
                timeout_seconds=config.semantic_scan_timeout
            )
            logger.info("Semantic scanner initialized")
            
            # Initialize validator suite
            self.validator_suite = ValidatorSuite(
                hardware_rules=None,  # Use defaults
                known_apis=None,  # Use defaults
                enable_hardware=config.enable_hardware_validation,
                enable_lifecycle=config.enable_lifecycle_validation,
                enable_api_typo=config.enable_api_typo_detection
            )
            logger.info("Validator suite initialized")
            
        except Exception as e:
            logger.error(f"Error initializing semantic components: {e}", exc_info=True)
            raise
    
    def _build_vector_store(
        self,
        knowledge_base: Any,
        embedding_model: Any,
        vector_store: Any
    ) -> None:
        """
        Build vector store from knowledge base.
        
        Args:
            knowledge_base: Knowledge base with patterns
            embedding_model: Model for generating embeddings
            vector_store: Vector store to populate
        """
        logger.info("Building vector store from knowledge base...")
        
        patterns = knowledge_base.get_all_patterns()
        
        if not patterns:
            logger.warning("No patterns found in knowledge base")
            return
        
        # Prepare data for embedding
        documents = []
        metadatas = []
        ids = []
        
        for pattern in patterns:
            # Combine explanation and buggy code for embedding
            document = f"{pattern.explanation}\n\n{pattern.buggy_code}"
            documents.append(document)
            
            metadatas.append({
                "pattern_id": pattern.id,
                "category": pattern.category,
                "severity": pattern.severity
            })
            
            ids.append(pattern.id)
        
        # Generate embeddings in batches
        logger.info(f"Generating embeddings for {len(documents)} patterns...")
        embeddings = embedding_model.encode_batch(
            documents,
            batch_size=config.embedding_batch_size
        )
        
        # Add to vector store
        logger.info("Adding embeddings to vector store...")
        vector_store.add_embeddings(
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        
        logger.info(f"Vector store built with {len(documents)} patterns")
    
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
        
        # Fallback: Generate template patches if vulnerabilities found but no patches
        if vulnerabilities and not patches:
            logger.info("No patches generated, creating template-based patches")
            original_code = state.get("code", "")
            try:
                patches = self._generate_template_patches(original_code, state.get("vulnerabilities", []))
            except Exception as e:
                logger.error(f"Error generating template patches: {e}")
        
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
    
    def _generate_template_patches(self, code: str, vulnerabilities: list) -> list:
        """
        Generate patches for detected vulnerabilities.
        
        Uses Ollama LLM if available, falls back to template-based patches.
        
        Args:
            code: Original source code
            vulnerabilities: List of detected vulnerabilities
            
        Returns:
            List of PatchResponse objects
        """
        import re
        
        patches = []
        patched_code = code
        
        # Try to use Ollama/LLM for intelligent patching
        if self.llm_client is not None and hasattr(self.llm_client, 'generate_patch'):
            try:
                logger.info("Using Ollama for intelligent patch generation...")
                # Generate patch for all vulnerabilities at once
                vuln_info = "\n".join([
                    f"- {v.vuln_type} at {v.location}: {v.description}"
                    for v in vulnerabilities
                ])
                
                prompt = f"""You are a security expert. Fix ALL the following security vulnerabilities in this Python code.

VULNERABILITIES FOUND:
{vuln_info}

ORIGINAL CODE:
```python
{code}
```

INSTRUCTIONS:
1. Fix ALL security vulnerabilities while preserving functionality
2. Use secure coding practices:
   - For SQL Injection: Use parameterized queries with ? placeholders
   - For Command Injection: Use subprocess with shell=False
   - For Path Traversal: Use os.path.basename() to sanitize filenames
   - For Code Injection: Remove eval/exec, use safe alternatives
3. Keep the same function names and signatures
4. Return ONLY the complete fixed Python code
5. Do not include markdown code blocks or explanations

FIXED CODE:
"""
                patched_code = self.llm_client.generate(prompt, temperature=0.1, max_tokens=4096)
                
                # Clean up response
                patched_code = patched_code.strip()
                if patched_code.startswith("```python"):
                    patched_code = patched_code[9:]
                if patched_code.startswith("```"):
                    patched_code = patched_code[3:]
                if patched_code.endswith("```"):
                    patched_code = patched_code[:-3]
                patched_code = patched_code.strip()
                
                # Validate syntax
                try:
                    import ast
                    ast.parse(patched_code)
                    logger.info("Ollama generated valid Python patch")
                except SyntaxError as e:
                    logger.warning(f"Ollama patch has syntax error: {e}, falling back to template")
                    patched_code = code  # Reset to use template fallback
                    
            except Exception as e:
                logger.warning(f"Ollama patch generation failed: {e}, using template fallback")
                patched_code = code  # Reset to use template fallback
        
        # Template fallback (if LLM not available or failed)
        if patched_code == code:
            vuln_types = {v.vuln_type for v in vulnerabilities}

            if "SQL Injection" in vuln_types:
                # Replace f-string SQL queries with parameterized queries
                patched_code = re.sub(
                    r'(query\s*=\s*)f(["\'])SELECT\s+\*\s+FROM\s+(\w+)\s+WHERE\s+(\w+)\s*=\s*\{(\w+)\}',
                    r'\1\2SELECT * FROM \3 WHERE \4 = ?\2',
                    patched_code
                )
                patched_code = re.sub(
                    r'cursor\.execute\s*\(\s*query\s*\)',
                    r'cursor.execute(query, (username,))',
                    patched_code
                )
                # More comprehensive SQL injection fix
                patched_code = re.sub(
                    r"f['\"]SELECT \* FROM users WHERE username='\{(\w+)\}' AND password='\{(\w+)\}'['\"]",
                    r'"SELECT * FROM users WHERE username=? AND password=?"',
                    patched_code
                )
                patched_code = re.sub(
                    r'cursor\.execute\s*\(\s*query\s*\)',
                    r'cursor.execute(query, (username, password))',
                    patched_code
                )
            
            if "Command Injection" in vuln_types:
                # Replace os.system with subprocess.run
                patched_code = re.sub(
                    r'os\.system\s*\(\s*(\w+)\s*\)',
                    r'subprocess.run([\1], shell=False, capture_output=True)',
                    patched_code
                )
                # Add import if not present
                if 'import subprocess' not in patched_code:
                    patched_code = 'import subprocess\n' + patched_code
            
            if "Path Traversal" in vuln_types:
                # Add path sanitization
                patched_code = re.sub(
                    r'open\s*\(\s*f["\']([^"\']*)\{(\w+)\}["\']',
                    r'open(os.path.join("\1", os.path.basename(\2))',
                    patched_code
                )

            if "Code Injection" in vuln_types:
                patched_code = re.sub(r'\beval\s*\(', 'ast.literal_eval(', patched_code)
                # Add imports for safe eval fallback only when needed.
                if 'ast.literal_eval(' in patched_code and 'import ast' not in patched_code:
                    patched_code = 'import ast\n' + patched_code
        
        if patched_code != code:
            # Generate diff
            original_lines = code.split('\n')
            patched_lines = patched_code.split('\n')
            diff_lines = []
            for i, (orig, patch) in enumerate(zip(original_lines, patched_lines)):
                if orig != patch:
                    diff_lines.append(f"- {orig}")
                    diff_lines.append(f"+ {patch}")
            diff = '\n'.join(diff_lines) if diff_lines else "Template-based fix applied"
            
            patches.append(
                PatchResponse(
                    code=patched_code,
                    diff=diff,
                    verified=False,
                    verification_result=None
                )
            )
        
        return patches
    
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
