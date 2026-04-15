"""
SecureCodeAI - FastAPI Server
Main API server with endpoints for vulnerability detection and patching.
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import time
import uuid
from datetime import datetime
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from .models import (
    AnalyzeRequest,
    AnalyzeResponse,
    HealthResponse,
    ReadinessResponse,
    ErrorResponse,
    SearchSimilarRequest,
    SearchSimilarResponse,
    SimilarPatternResponse,
    KnowledgeBaseStatsResponse
)
from .config import config
from .vllm_client import get_vllm_client, initialize_vllm
from .orchestrator import get_orchestrator, initialize_orchestrator
from .logging_config import (
    logger,
    configure_logging,
    set_request_context,
    clear_request_context
)
from .shutdown import setup_signal_handlers, register_shutdown_callback


# Global state for tracking service status
class ServiceState:
    def __init__(self):
        self.start_time = time.time()
        self.vllm_loaded = False
        self.workflow_ready = False
        self.request_queue_depth = 0
        self.vllm_client = None
        self.orchestrator = None


service_state = ServiceState()


# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown."""
    # Startup
    configure_logging()
    logger.info(f"Starting SecureCodeAI API Server v{app.version}")
    logger.info(f"Configuration: {config.model_dump()}")
    
    # Setup signal handlers for graceful shutdown
    def shutdown_callback():
        """Callback for graceful shutdown."""
        logger.info("Executing graceful shutdown...")
        
        # Cleanup vLLM engine
        if service_state.vllm_client:
            logger.info("Cleaning up vLLM engine...")
            service_state.vllm_client.cleanup()
            logger.info("vLLM engine cleaned up")
        
        # Cleanup workflow orchestrator
        if service_state.orchestrator:
            logger.info("Cleaning up workflow orchestrator...")
            service_state.orchestrator.cleanup()
            logger.info("Workflow orchestrator cleaned up")
    
    register_shutdown_callback(shutdown_callback)
    setup_signal_handlers()
    
    try:
        # Initialize vLLM engine (if enabled)
        if config.enable_gpu:
            logger.info("Initializing vLLM engine...")
            service_state.vllm_client = get_vllm_client()
            # Note: Actual initialization happens on first request to avoid startup delays
            service_state.vllm_loaded = True
            logger.info("vLLM client ready")
        
        # Initialize workflow orchestrator
        logger.info("Initializing workflow orchestrator...")
        service_state.orchestrator = get_orchestrator(service_state.vllm_client)
        # Note: Actual initialization happens on first request to avoid startup delays
        service_state.workflow_ready = True
        logger.info("Workflow orchestrator ready")
        
    except Exception as e:
        logger.error(f"Initialization error: {e}")
        logger.warning("Service will start but may not be fully functional")
    
    yield
    
    # Shutdown
    logger.info("Shutting down SecureCodeAI API Server")
    
    # Cleanup vLLM engine
    if service_state.vllm_client:
        service_state.vllm_client.cleanup()
    
    # Cleanup workflow orchestrator
    if service_state.orchestrator:
        service_state.orchestrator.cleanup()


# Create FastAPI application
app = FastAPI(
    title="SecureCodeAI API",
    description="""
## Neuro-Symbolic Vulnerability Detection and Patching System

SecureCodeAI combines Large Language Models (LLMs) with symbolic execution to detect and patch security vulnerabilities in source code.

### Features

* **Automated Vulnerability Detection**: Scans code for security vulnerabilities using pattern matching and LLM analysis
* **Formal Verification**: Uses symbolic execution (CrossHair) to verify vulnerabilities
* **Automated Patching**: Generates and verifies security patches
* **Multi-Agent Architecture**: Coordinates Scanner, Speculator, SymBot, and Patcher agents

### Workflow

1. **Scanner Agent**: Detects potential vulnerabilities using Bandit SAST
2. **Speculator Agent**: Generates formal security contracts using LLM
3. **SymBot Agent**: Verifies vulnerabilities with symbolic execution
4. **Patcher Agent**: Generates and verifies security patches

### Model

Powered by DeepSeek-Coder-V2-Lite-Instruct (16B parameters) served via vLLM for high-performance inference.
    """,
    version="0.1.0",
    docs_url="/docs" if config.enable_docs else None,
    redoc_url="/redoc" if config.enable_docs else None,
    openapi_tags=[
        {
            "name": "Root",
            "description": "Root endpoint with API information"
        },
        {
            "name": "Analysis",
            "description": "Code vulnerability analysis and patching endpoints"
        },
        {
            "name": "Health",
            "description": "Service health and readiness monitoring endpoints"
        }
    ],
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add Gzip compression middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Add rate limiter state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    request_id = str(uuid.uuid4())
    timestamp = datetime.utcnow().isoformat() + "Z"
    
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error=exc.__class__.__name__,
            detail=str(exc),
            request_id=request_id,
            timestamp=timestamp
        ).model_dump()
    )


@app.get(
    "/",
    tags=["Root"],
    summary="API information",
    description="Get API metadata and available endpoints",
    responses={
        200: {
            "description": "API information",
            "content": {
                "application/json": {
                    "example": {
                        "name": "SecureCodeAI API",
                        "version": "0.1.0",
                        "description": "Neuro-Symbolic Vulnerability Detection and Patching",
                        "endpoints": {
                            "analyze": "/analyze",
                            "health": "/health",
                            "readiness": "/health/ready",
                            "docs": "/docs",
                            "redoc": "/redoc"
                        }
                    }
                }
            }
        }
    }
)
async def root():
    """Root endpoint with API information."""
    return {
        "name": "SecureCodeAI API",
        "version": "0.1.0",
        "description": "Neuro-Symbolic Vulnerability Detection and Patching",
        "endpoints": {
            "analyze": "/analyze",
            "health": "/health",
            "readiness": "/health/ready",
            "docs": "/docs" if config.enable_docs else "disabled",
            "redoc": "/redoc" if config.enable_docs else "disabled"
        }
    }


@app.post(
    "/analyze",
    response_model=AnalyzeResponse,
    tags=["Analysis"],
    summary="Analyze code for vulnerabilities",
    description="Submit source code for vulnerability detection and automated patching",
    responses={
        200: {
            "description": "Analysis completed successfully",
            "content": {
                "application/json": {
                    "example": {
                        "analysis_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                        "vulnerabilities": [
                            {
                                "location": "app/database.py:42",
                                "vuln_type": "SQL Injection",
                                "severity": "HIGH",
                                "description": "SQL query uses f-string formatting with user input",
                                "confidence": 0.95,
                                "cwe_id": "CWE-89",
                                "hypothesis": "User input 'username' is directly interpolated into SQL query without sanitization, allowing SQL injection attacks"
                            }
                        ],
                        "patches": [
                            {
                                "code": "query = \"SELECT * FROM users WHERE username=?\"\ncursor.execute(query, (username,))",
                                "diff": "- query = f\"SELECT * FROM users WHERE username='{username}'\"\n+ query = \"SELECT * FROM users WHERE username=?\"\n+ cursor.execute(query, (username,))",
                                "verified": True,
                                "verification_result": {
                                    "verified": True,
                                    "execution_time": 2.5,
                                    "counterexamples": []
                                }
                            }
                        ],
                        "execution_time": 15.3,
                        "errors": [],
                        "logs": [
                            "Scanner Agent: Found 1 potential vulnerabilities",
                            "Speculator Agent: Generated security contract",
                            "SymBot Agent: Verified vulnerability with symbolic execution",
                            "Patcher Agent: Generated and verified patch"
                        ],
                        "workflow_complete": True
                    }
                }
            }
        },
        400: {
            "description": "Invalid request (empty code, invalid parameters)",
            "content": {
                "application/json": {
                    "example": {
                        "error": "ValidationError",
                        "detail": "Code cannot be empty or whitespace only",
                        "request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                        "timestamp": "2025-01-24T12:34:56.789Z"
                    }
                }
            }
        },
        429: {
            "description": "Rate limit exceeded",
            "content": {
                "application/json": {
                    "example": {
                        "error": "RateLimitExceeded",
                        "detail": "Rate limit exceeded: 10 requests per minute",
                        "request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                        "timestamp": "2025-01-24T12:34:56.789Z"
                    }
                }
            }
        },
        500: {
            "description": "Internal server error (workflow failure)",
            "content": {
                "application/json": {
                    "example": {
                        "error": "WorkflowError",
                        "detail": "Analysis failed: Agent execution error",
                        "request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                        "timestamp": "2025-01-24T12:34:56.789Z"
                    }
                }
            }
        },
        503: {
            "description": "Service unavailable (vLLM not loaded)",
            "content": {
                "application/json": {
                    "example": {
                        "error": "ServiceUnavailable",
                        "detail": "Workflow orchestrator not initialized",
                        "request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                        "timestamp": "2025-01-24T12:34:56.789Z"
                    }
                }
            }
        }
    }
)
@limiter.limit(f"{config.rate_limit_requests}/minute")
async def analyze_code(request: Request, analyze_request: AnalyzeRequest):
    """
    Analyze source code for security vulnerabilities.
    
    This endpoint:
    1. Scans code for vulnerability patterns
    2. Generates formal security contracts
    3. Verifies vulnerabilities with symbolic execution
    4. Generates and verifies security patches
    
    Returns detected vulnerabilities and verified patches.
    """
    analysis_id = str(uuid.uuid4())
    start_time = time.time()
    
    # Set request context for logging
    set_request_context(
        request_id=analysis_id,
        code_length=len(analyze_request.code),
        file_path=analyze_request.file_path,
        max_iterations=analyze_request.max_iterations
    )
    
    logger.info(f"Starting code analysis", extra={
        "request_id": analysis_id,
        "code_length": len(analyze_request.code),
        "file_path": analyze_request.file_path
    })
    
    try:
        service_state.request_queue_depth += 1
        
        # Check if orchestrator is ready
        if not service_state.orchestrator:
            logger.error("Workflow orchestrator not initialized", extra={"request_id": analysis_id})
            raise HTTPException(
                status_code=503,
                detail="Workflow orchestrator not initialized"
            )
        
        # Run analysis
        response = await service_state.orchestrator.analyze_code(
            code=analyze_request.code,
            file_path=analyze_request.file_path,
            max_iterations=analyze_request.max_iterations
        )
        
        execution_time = time.time() - start_time
        
        # Include queue depth in response when under load (queue depth > 1)
        if service_state.request_queue_depth > 1:
            response.queue_depth = service_state.request_queue_depth
        
        logger.info(f"Code analysis completed", extra={
            "request_id": analysis_id,
            "execution_time": execution_time,
            "vulnerabilities_found": len(response.vulnerabilities),
            "patches_generated": len(response.patches),
            "workflow_complete": response.workflow_complete
        })
        
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(f"Analysis failed: {str(e)}", extra={
            "request_id": analysis_id,
            "execution_time": execution_time
        }, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}"
        )
    
    finally:
        service_state.request_queue_depth -= 1
        clear_request_context()


@app.post(
    "/search_similar",
    response_model=SearchSimilarResponse,
    tags=["Analysis"],
    summary="Search for similar bug patterns",
    description="Search the knowledge base for bug patterns similar to the provided query",
    responses={
        200: {
            "description": "Search completed successfully",
            "content": {
                "application/json": {
                    "example": {
                        "query": "SELECT * FROM users WHERE username='{}'",
                        "similar_patterns": [
                            {
                                "pattern_id": "001",
                                "explanation": "SQL injection vulnerability in string formatting",
                                "context": "Using f-strings or % formatting with user input in SQL queries",
                                "buggy_code": "query = f\"SELECT * FROM users WHERE id={user_id}\"",
                                "correct_code": "query = \"SELECT * FROM users WHERE id=?\"\ncursor.execute(query, (user_id,))",
                                "similarity_score": 0.92,
                                "category": "sql_injection"
                            }
                        ],
                        "count": 1
                    }
                }
            }
        },
        400: {
            "description": "Invalid request (empty query, invalid parameters)",
            "content": {
                "application/json": {
                    "example": {
                        "error": "ValidationError",
                        "detail": "Query cannot be empty or whitespace only",
                        "request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                        "timestamp": "2025-01-24T12:34:56.789Z"
                    }
                }
            }
        },
        503: {
            "description": "Service unavailable (semantic scanning not enabled)",
            "content": {
                "application/json": {
                    "example": {
                        "error": "ServiceUnavailable",
                        "detail": "Semantic scanning is not enabled",
                        "request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                        "timestamp": "2025-01-24T12:34:56.789Z"
                    }
                }
            }
        }
    }
)
@limiter.limit(f"{config.rate_limit_requests}/minute")
async def search_similar(request: Request, search_request: SearchSimilarRequest):
    """
    Search knowledge base for similar bug patterns.
    
    This endpoint allows direct querying of the bug pattern knowledge base
    using semantic similarity search. Useful for:
    - Finding similar vulnerabilities to a code snippet
    - Exploring the knowledge base
    - Getting fix suggestions for specific patterns
    
    Returns similar patterns ranked by similarity score.
    """
    request_id = str(uuid.uuid4())
    
    # Set request context for logging
    set_request_context(
        request_id=request_id,
        query_length=len(search_request.query),
        top_k=search_request.top_k
    )
    
    logger.info(f"Starting similarity search", extra={
        "request_id": request_id,
        "query_length": len(search_request.query),
        "top_k": search_request.top_k
    })
    
    try:
        # Check if orchestrator is ready
        if not service_state.orchestrator:
            logger.error("Workflow orchestrator not initialized", extra={"request_id": request_id})
            raise HTTPException(
                status_code=503,
                detail="Workflow orchestrator not initialized"
            )
        
        # Ensure orchestrator is initialized
        if not service_state.orchestrator.is_initialized():
            service_state.orchestrator.initialize()
        
        # Check if semantic scanning is enabled
        if not service_state.orchestrator.semantic_scanner:
            logger.error("Semantic scanning not enabled", extra={"request_id": request_id})
            raise HTTPException(
                status_code=503,
                detail="Semantic scanning is not enabled"
            )
        
        # Perform similarity search
        similar_patterns = service_state.orchestrator.semantic_scanner.search_similar(
            query=search_request.query,
            top_k=search_request.top_k
        )
        
        # Convert to response format
        pattern_responses = [
            SimilarPatternResponse(
                pattern_id=pattern.pattern_id,
                explanation=pattern.explanation,
                context=pattern.context,
                buggy_code=pattern.buggy_code,
                correct_code=pattern.correct_code,
                similarity_score=pattern.similarity_score,
                category=pattern.category
            )
            for pattern in similar_patterns
        ]
        
        response = SearchSimilarResponse(
            query=search_request.query,
            similar_patterns=pattern_responses,
            count=len(pattern_responses)
        )
        
        logger.info(f"Similarity search completed", extra={
            "request_id": request_id,
            "patterns_found": len(pattern_responses)
        })
        
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Similarity search failed: {str(e)}", extra={
            "request_id": request_id
        }, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Similarity search failed: {str(e)}"
        )
    
    finally:
        clear_request_context()


@app.get(
    "/knowledge_base/stats",
    response_model=KnowledgeBaseStatsResponse,
    tags=["Analysis"],
    summary="Get knowledge base statistics",
    description="Get statistics about the bug pattern knowledge base",
    responses={
        200: {
            "description": "Statistics retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "pattern_count": 150,
                        "categories": {
                            "sql_injection": 25,
                            "xss": 30,
                            "buffer_overflow": 20,
                            "general": 75
                        },
                        "last_updated": "2025-01-24T10:30:00.000Z"
                    }
                }
            }
        },
        503: {
            "description": "Service unavailable (semantic scanning not enabled)",
            "content": {
                "application/json": {
                    "example": {
                        "error": "ServiceUnavailable",
                        "detail": "Semantic scanning is not enabled",
                        "request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                        "timestamp": "2025-01-24T12:34:56.789Z"
                    }
                }
            }
        }
    }
)
async def get_knowledge_base_stats():
    """
    Get statistics about the knowledge base.
    
    Returns:
    - pattern_count: Total number of bug patterns
    - categories: Pattern count by category
    - last_updated: Last update timestamp
    """
    request_id = str(uuid.uuid4())
    
    logger.info(f"Retrieving knowledge base statistics", extra={
        "request_id": request_id
    })
    
    try:
        # Check if orchestrator is ready
        if not service_state.orchestrator:
            logger.error("Workflow orchestrator not initialized", extra={"request_id": request_id})
            raise HTTPException(
                status_code=503,
                detail="Workflow orchestrator not initialized"
            )
        
        # Ensure orchestrator is initialized
        if not service_state.orchestrator.is_initialized():
            service_state.orchestrator.initialize()
        
        # Check if semantic scanning is enabled
        if not service_state.orchestrator.semantic_scanner:
            logger.error("Semantic scanning not enabled", extra={"request_id": request_id})
            raise HTTPException(
                status_code=503,
                detail="Semantic scanning is not enabled"
            )
        
        # Get knowledge base stats
        kb_stats = service_state.orchestrator.semantic_scanner.knowledge_base.get_stats()
        
        response = KnowledgeBaseStatsResponse(
            pattern_count=kb_stats.pattern_count,
            categories=kb_stats.categories,
            last_updated=kb_stats.last_updated
        )
        
        logger.info(f"Knowledge base statistics retrieved", extra={
            "request_id": request_id,
            "pattern_count": kb_stats.pattern_count
        })
        
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve knowledge base statistics: {str(e)}", extra={
            "request_id": request_id
        }, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve knowledge base statistics: {str(e)}"
        )


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["Health"],
    summary="Health check",
    description="Check if the service is healthy and operational",
    responses={
        200: {
            "description": "Service is healthy",
            "content": {
                "application/json": {
                    "examples": {
                        "healthy": {
                            "summary": "Healthy service",
                            "value": {
                                "status": "healthy",
                                "vllm_loaded": True,
                                "workflow_ready": True,
                                "uptime_seconds": 3600.5,
                                "request_queue_depth": 0
                            }
                        },
                        "under_load": {
                            "summary": "Healthy but under load",
                            "value": {
                                "status": "healthy",
                                "vllm_loaded": True,
                                "workflow_ready": True,
                                "uptime_seconds": 7200.3,
                                "request_queue_depth": 5
                            }
                        }
                    }
                }
            }
        },
        503: {
            "description": "Service is unhealthy",
            "content": {
                "application/json": {
                    "example": {
                        "status": "unhealthy",
                        "vllm_loaded": False,
                        "workflow_ready": False,
                        "uptime_seconds": 10.2,
                        "request_queue_depth": 0
                    }
                }
            }
        }
    }
)
async def health_check():
    """
    Health check endpoint.
    
    Returns:
    - status: "healthy" if all components are operational
    - vllm_loaded: Whether the vLLM engine is loaded
    - workflow_ready: Whether the agent workflow is initialized
    - uptime_seconds: Service uptime
    - request_queue_depth: Current request queue depth
    """
    uptime = time.time() - service_state.start_time
    
    # Determine overall health status
    status = "healthy" if (
        service_state.vllm_loaded and 
        service_state.workflow_ready
    ) else "unhealthy"
    
    return HealthResponse(
        status=status,
        vllm_loaded=service_state.vllm_loaded,
        workflow_ready=service_state.workflow_ready,
        uptime_seconds=uptime,
        request_queue_depth=service_state.request_queue_depth
    )


@app.get(
    "/health/ready",
    response_model=ReadinessResponse,
    tags=["Health"],
    summary="Readiness check",
    description="Check if the service is ready to accept requests",
    responses={
        200: {
            "description": "Readiness status",
            "content": {
                "application/json": {
                    "examples": {
                        "ready": {
                            "summary": "Service ready",
                            "value": {
                                "ready": True,
                                "components": {
                                    "api_server": True,
                                    "vllm_engine": True,
                                    "agent_workflow": True
                                }
                            }
                        },
                        "not_ready": {
                            "summary": "Service not ready",
                            "value": {
                                "ready": False,
                                "components": {
                                    "api_server": True,
                                    "vllm_engine": False,
                                    "agent_workflow": False
                                }
                            }
                        }
                    }
                }
            }
        }
    }
)
async def readiness_check():
    """
    Readiness check endpoint.
    
    Returns component-level readiness status:
    - api_server: Always true if this endpoint responds
    - vllm_engine: Whether vLLM is loaded and ready
    - agent_workflow: Whether the workflow is initialized
    """
    components = {
        "api_server": True,  # If we're responding, API server is ready
        "vllm_engine": service_state.vllm_loaded,
        "agent_workflow": service_state.workflow_ready
    }
    
    ready = all(components.values())
    
    return ReadinessResponse(
        ready=ready,
        components=components
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "api.server:app",
        host=config.host,
        port=config.port,
        workers=config.workers,
        log_level=config.log_level.lower()
    )
