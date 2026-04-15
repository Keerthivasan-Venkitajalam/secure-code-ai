# SecureCodeAI Architecture

This document provides a detailed overview of the SecureCodeAI system architecture, including component interactions, data flow, and deployment models.

## Table of Contents

- [System Overview](#system-overview)
- [Component Architecture](#component-architecture)
- [Data Flow](#data-flow)
- [Deployment Architecture](#deployment-architecture)
- [Technology Stack](#technology-stack)
- [Design Decisions](#design-decisions)

## System Overview

SecureCodeAI is a neuro-symbolic vulnerability detection and patching system that combines:

1. **Large Language Models (LLMs)** - For intelligent code analysis and patch generation
2. **Symbolic Execution** - For formal verification of vulnerabilities
3. **Static Analysis** - For fast initial vulnerability detection
4. **Multi-Agent Workflow** - For coordinated analysis and patching

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Client Layer                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  VS Code Ext │  │     CLI      │  │   Web UI     │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
└─────────┼──────────────────┼──────────────────┼─────────────┘
          │                  │                  │
          └──────────────────┴──────────────────┘
                             │ HTTPS/REST
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                        API Layer                             │
│  ┌────────────────────────────────────────────────────┐     │
│  │              FastAPI Application                    │     │
│  │  • Request Validation (Pydantic)                   │     │
│  │  • Rate Limiting (SlowAPI)                         │     │
│  │  • CORS & Compression                              │     │
│  │  • Health Monitoring                               │     │
│  │  • Structured Logging (Loguru)                     │     │
│  └────────────────────┬───────────────────────────────┘     │
└───────────────────────┼─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                   Orchestration Layer                        │
│  ┌────────────────────────────────────────────────────┐     │
│  │           Workflow Orchestrator                     │     │
│  │  • State Management                                │     │
│  │  • Agent Coordination                              │     │
│  │  • Error Handling                                  │     │
│  │  • Result Aggregation                              │     │
│  └────────────────────┬───────────────────────────────┘     │
└───────────────────────┼─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                      Agent Layer                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │            LangGraph Workflow                         │   │
│  │                                                       │   │
│  │  ┌──────────┐  ┌────────────┐  ┌─────────┐  ┌────┐ │   │
│  │  │ Scanner  │→ │ Speculator │→ │ SymBot  │→ │Patch││   │
│  │  │  Agent   │  │   Agent    │  │  Agent  │  │Agent││   │
│  │  └────┬─────┘  └─────┬──────┘  └────┬────┘  └──┬─┘ │   │
│  │       │              │               │          │   │   │
│  │       │  (Bandit)    │  (LLM)        │ (Cross  │(LLM)  │
│  │       │              │               │  Hair)  │   │   │
│  │       └──────────────┴───────────────┴──────────┘   │   │
│  └──────────────────────┬───────────────────────────────┘   │
└─────────────────────────┼─────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    Inference Layer                           │
│  ┌────────────────────────────────────────────────────┐     │
│  │              vLLM Engine                            │     │
│  │  • Model: DeepSeek-Coder-V2-Lite (16B)            │     │
│  │  • Quantization: AWQ 4-bit                         │     │
│  │  • PagedAttention for KV cache                     │     │
│  │  • Continuous batching                             │     │
│  │  • GPU acceleration (optional)                     │     │
│  └────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

## Component Architecture

### 1. API Layer (`api/`)

#### FastAPI Server (`server.py`)

**Responsibilities:**
- HTTP request handling
- Request validation and sanitization
- Response formatting
- Error handling and logging
- Health monitoring

**Key Features:**
- Async/await for non-blocking I/O
- Pydantic models for type safety
- OpenAPI documentation generation
- CORS middleware for cross-origin requests
- Gzip compression for large responses
- Rate limiting to prevent abuse

**Endpoints:**
```
POST   /analyze          - Analyze code for vulnerabilities
GET    /health           - Health check
GET    /health/ready     - Readiness check
GET    /                 - API information
GET    /docs             - Swagger UI
GET    /redoc            - ReDoc documentation
```

#### Configuration Manager (`config.py`)

**Responsibilities:**
- Load configuration from environment variables
- Validate configuration values
- Provide typed configuration objects

**Configuration Sources:**
1. Environment variables (highest priority)
2. `.env` file
3. Default values (lowest priority)

#### Request/Response Models (`models.py`)

**Key Models:**
- `AnalyzeRequest` - Input validation for code analysis
- `AnalyzeResponse` - Structured analysis results
- `HealthResponse` - Service health status
- `ReadinessResponse` - Component readiness status
- `VulnerabilityResponse` - Vulnerability details
- `PatchResponse` - Patch information

### 2. Orchestration Layer (`api/orchestrator.py`)

#### Workflow Orchestrator

**Responsibilities:**
- Initialize and manage agent workflow
- Convert API requests to agent state
- Execute workflow and handle state transitions
- Extract results from final state
- Manage workflow lifecycle

**State Management:**
```python
class AgentState:
    code: str                    # Source code to analyze
    file_path: str               # File path for context
    vulnerabilities: List[Vuln]  # Detected vulnerabilities
    patches: List[Patch]         # Generated patches
    errors: List[str]            # Error messages
    logs: List[str]              # Execution logs
    iteration_count: int         # Current iteration
    max_iterations: int          # Maximum iterations
```

**Workflow Execution:**
1. Create initial state from request
2. Execute Scanner → Speculator → SymBot → Patcher pipeline
3. Handle errors and state transitions
4. Extract results and format response

### 3. Agent Layer (`agent/`)

#### Scanner Agent (`scanner.py`)

**Purpose:** Initial vulnerability detection using static analysis

**Technology:** Bandit SAST tool

**Process:**
1. Parse Python code into AST
2. Run Bandit security checks
3. Extract vulnerability locations and types
4. Add to agent state

**Output:**
```python
{
    "location": "line 42",
    "vuln_type": "SQL Injection",
    "severity": "high",
    "confidence": 0.85
}
```

#### Speculator Agent (`speculator.py`)

**Purpose:** Generate formal security contracts using LLM

**Technology:** DeepSeek-Coder-V2-Lite via vLLM

**Process:**
1. Receive vulnerabilities from Scanner
2. Generate formal preconditions and postconditions
3. Create CrossHair-compatible contracts
4. Add contracts to agent state

**Example Contract:**
```python
def get_user(username: str) -> User:
    """
    Precondition: username must be alphanumeric
    Postcondition: Returns valid User object or raises exception
    """
    # Implementation
```

#### SymBot Agent (`symbot.py`)

**Purpose:** Verify vulnerabilities using symbolic execution

**Technology:** CrossHair symbolic execution engine

**Process:**
1. Receive contracts from Speculator
2. Run symbolic execution with timeout
3. Generate counterexamples for violations
4. Mark vulnerabilities as verified/unverified

**Verification Result:**
```python
{
    "verified": true,
    "counterexample": "username=\"'; DROP TABLE users; --\"",
    "execution_time": 2.3
}
```

#### Patcher Agent (`patcher.py`)

**Purpose:** Generate and verify security patches

**Technology:** DeepSeek-Coder-V2-Lite via vLLM

**Process:**
1. Receive verified vulnerabilities
2. Generate patch using LLM
3. Verify patch with SymBot
4. Iterate if verification fails (up to max_iterations)
5. Return verified patch

**Patch Output:**
```python
{
    "code": "query = \"SELECT * FROM users WHERE username = ?\"",
    "diff": "- query = f\"SELECT * FROM users WHERE username='{username}'\"\n+ query = \"SELECT * FROM users WHERE username = ?\"",
    "verified": true
}
```

### 4. Inference Layer (`api/vllm_client.py`)

#### vLLM Client

**Purpose:** High-performance LLM inference

**Features:**
- PagedAttention for efficient KV cache management
- Continuous batching for improved throughput
- AWQ 4-bit quantization for reduced memory
- GPU acceleration (optional)
- Retry logic with exponential backoff

**Configuration:**
```python
{
    "model": "DeepSeek-Coder-V2-Lite-Instruct",
    "quantization": "awq",
    "gpu_memory_utilization": 0.9,
    "tensor_parallel_size": 1,
    "temperature": 0.2,
    "top_p": 0.95,
    "max_tokens": 2048
}
```

## Data Flow

### Request Flow

```
1. Client Request
   ↓
2. FastAPI Validation (Pydantic)
   ↓
3. Rate Limiting Check
   ↓
4. Orchestrator.analyze_code()
   ↓
5. Create Initial AgentState
   ↓
6. LangGraph Workflow Execution
   ├─→ Scanner Agent (Bandit)
   │   ↓
   ├─→ Speculator Agent (LLM)
   │   ↓
   ├─→ SymBot Agent (CrossHair)
   │   ↓
   └─→ Patcher Agent (LLM)
       ↓
7. Extract Results from Final State
   ↓
8. Format AnalyzeResponse
   ↓
9. Return JSON Response
```

### State Transitions

```
Initial State
  code: "..."
  vulnerabilities: []
  patches: []
  ↓
After Scanner
  vulnerabilities: [Vuln1, Vuln2]
  ↓
After Speculator
  vulnerabilities: [Vuln1+Contract, Vuln2+Contract]
  ↓
After SymBot
  vulnerabilities: [Vuln1+Verified, Vuln2+Unverified]
  ↓
After Patcher
  patches: [Patch1+Verified]
  ↓
Final State
```

## Deployment Architecture

### Local Development

```
┌─────────────────────────────────────┐
│         Developer Machine            │
│  ┌────────────────────────────┐     │
│  │  Python Process             │     │
│  │  • FastAPI Server           │     │
│  │  • vLLM Engine (CPU)        │     │
│  │  • Agent Workflow           │     │
│  └────────────────────────────┘     │
│                                      │
│  Port: 8000                          │
│  Model: Local file system            │
└─────────────────────────────────────┘
```

### Docker Deployment

```
┌─────────────────────────────────────┐
│         Docker Host                  │
│  ┌────────────────────────────┐     │
│  │  Docker Container           │     │
│  │  ┌──────────────────────┐  │     │
│  │  │  FastAPI + vLLM      │  │     │
│  │  │  + Agents            │  │     │
│  │  └──────────────────────┘  │     │
│  │                             │     │
│  │  Volumes:                   │     │
│  │  • /models (persistent)     │     │
│  │  • /logs                    │     │
│  └────────────────────────────┘     │
│                                      │
│  Port: 8000 → Host:8000              │
└─────────────────────────────────────┘
```

### RunPod Serverless

```
┌─────────────────────────────────────────────────────┐
│              RunPod Serverless Platform              │
│                                                       │
│  ┌─────────────────────────────────────────────┐   │
│  │         GPU Instance (Auto-scaled)           │   │
│  │  ┌────────────────────────────────────────┐ │   │
│  │  │  Docker Container                       │ │   │
│  │  │  • FastAPI Server                       │ │   │
│  │  │  • vLLM Engine (GPU)                    │ │   │
│  │  │  • Agent Workflow                       │ │   │
│  │  └────────────────────────────────────────┘ │   │
│  │                                              │   │
│  │  GPU: 24GB VRAM (A5000/A6000/RTX4090)      │   │
│  │  Persistent Volume: /models (cached)        │   │
│  │  Auto-scaling: Scale to 0 after 5min idle   │   │
│  │  Cold-start: ~30s                            │   │
│  └─────────────────────────────────────────────┘   │
│                                                       │
│  HTTPS Endpoint: https://xxx.runpod.io              │
└─────────────────────────────────────────────────────┘
```

## Technology Stack

### Backend
- **FastAPI** - Modern async web framework
- **Pydantic** - Data validation and settings management
- **Uvicorn** - ASGI server
- **LangGraph** - Agent workflow orchestration
- **vLLM** - High-performance LLM inference

### AI/ML
- **DeepSeek-Coder-V2-Lite** - 16B parameter code LLM
- **Transformers** - Model loading and tokenization
- **PyTorch** - Deep learning framework
- **AWQ** - 4-bit quantization

### Security Analysis
- **Bandit** - Python SAST tool
- **CrossHair** - Symbolic execution engine
- **Z3** - SMT solver

### Infrastructure
- **Docker** - Containerization
- **Docker Compose** - Multi-container orchestration
- **RunPod** - Serverless GPU platform

### Monitoring & Logging
- **Loguru** - Structured logging
- **Prometheus** (planned) - Metrics collection
- **Grafana** (planned) - Metrics visualization

### Testing
- **Pytest** - Test framework
- **Hypothesis** - Property-based testing
- **Locust** - Load testing
- **pytest-cov** - Coverage reporting

## Design Decisions

### Why FastAPI?

**Pros:**
- Native async/await support
- Automatic OpenAPI documentation
- Pydantic integration for type safety
- High performance (comparable to Node.js)
- Modern Python features

**Alternatives Considered:**
- Flask (synchronous, less performant)
- Django (too heavyweight for API-only service)

### Why vLLM?

**Pros:**
- PagedAttention for efficient memory usage
- Continuous batching for high throughput
- Native quantization support
- GPU optimization

**Alternatives Considered:**
- Ollama (less control over batching)
- HuggingFace Transformers (slower inference)
- llama.cpp (C++ complexity)

### Why LangGraph?

**Pros:**
- Built for agent workflows
- State management
- Error handling
- Visualization tools

**Alternatives Considered:**
- Custom workflow (more maintenance)
- LangChain (less agent-focused)
- Prefect (overkill for simple workflows)

### Why Docker?

**Pros:**
- Reproducible deployments
- Dependency isolation
- Easy scaling
- Platform independence

**Alternatives Considered:**
- Virtual environments (less isolation)
- Kubernetes (overkill for single service)

### Why RunPod Serverless?

**Pros:**
- Cost-effective (pay per use)
- Auto-scaling
- Scale to zero
- GPU availability

**Alternatives Considered:**
- AWS Lambda (no GPU support)
- Google Cloud Run (limited GPU options)
- Azure Container Instances (more expensive)

## Performance Considerations

### Bottlenecks

1. **LLM Inference** - Slowest component (~1-3s per request)
2. **Symbolic Execution** - Can timeout on complex code
3. **Model Loading** - Cold start penalty (~30s)

### Optimizations

1. **vLLM Batching** - Process multiple requests together
2. **Persistent Volumes** - Cache model weights
3. **Async Processing** - Non-blocking request handling
4. **Rate Limiting** - Prevent resource exhaustion
5. **Quantization** - Reduce memory footprint

### Scalability

**Horizontal Scaling:**
- Multiple API server instances behind load balancer
- Shared vLLM engine or separate engines per instance

**Vertical Scaling:**
- Larger GPU for faster inference
- More CPU cores for concurrent requests
- More RAM for larger models

## Security Considerations

### API Security

- **Rate Limiting** - Prevent abuse
- **Input Validation** - Pydantic models
- **CORS** - Restrict origins in production
- **HTTPS** - Encrypt traffic (via reverse proxy)

### Model Security

- **Model Isolation** - Separate process for vLLM
- **Timeout Protection** - Prevent hanging requests
- **Resource Limits** - Memory and CPU caps

### Data Security

- **No Data Persistence** - Code not stored
- **Logging** - Sanitize sensitive data
- **Secrets Management** - Environment variables

## Future Enhancements

### Planned Features

1. **Multi-language Support** - JavaScript, Java, Go
2. **Incremental Analysis** - Analyze only changed code
3. **Custom Rules** - User-defined vulnerability patterns
4. **Vulnerability Database** - Track known vulnerabilities
5. **CI/CD Integration** - GitHub Actions, GitLab CI

### Architectural Improvements

1. **Message Queue** - Decouple API from workflow
2. **Result Caching** - Cache analysis results
3. **Distributed Tracing** - OpenTelemetry integration
4. **Metrics Dashboard** - Prometheus + Grafana
5. **Multi-model Support** - Support different LLMs

---

**Last Updated:** 2026-01-24  
**Version:** 0.1.0
