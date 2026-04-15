# Semantic Scanning Guide

This guide covers the semantic bug detection path used by SecureCodeAI.

## Overview

Semantic scanning augments static analysis by matching incoming code against known bug patterns.

Pipeline:

1. Load patterns from CSV knowledge base
2. Embed incoming code and stored patterns
3. Search vector store for nearest matches
4. Filter by similarity threshold
5. Convert matches into semantic vulnerabilities

## Core Components

- `agent/nodes/semantic_scanner.py`: semantic scan logic and `search_similar()`
- `agent/knowledge/knowledge_base.py`: pattern loading and stats
- `agent/knowledge/embedding_model.py`: embedding model lifecycle
- `agent/knowledge/vector_store.py`: persistent similarity search
- `agent/nodes/workflow_nodes.py`: merge node and validator node integration

## Data Requirements

Knowledge base CSV required columns:

- `ID`
- `Explanation`
- `Context`
- `Code`
- `Correct Code`

Optional columns:

- `Category`
- `Severity`

Default file location:

- `data/knowledge_base/samples.csv`

## Configuration

Set via environment variables (see `api/config.py`):

- `SECUREAI_ENABLE_SEMANTIC_SCANNING`
- `SECUREAI_KNOWLEDGE_BASE_PATH`
- `SECUREAI_EMBEDDING_MODEL_NAME`
- `SECUREAI_EMBEDDING_MODEL_PATH`
- `SECUREAI_VECTOR_STORE_PATH`
- `SECUREAI_SIMILARITY_THRESHOLD`
- `SECUREAI_TOP_K_RESULTS`
- `SECUREAI_SEMANTIC_SCAN_TIMEOUT`
- `SECUREAI_EMBEDDING_BATCH_SIZE`
- `SECUREAI_VECTOR_STORE_MAX_MEMORY_MB`
- `SECUREAI_VECTOR_STORE_HNSW_EF`
- `SECUREAI_EMBEDDING_CACHE_SIZE`

## API Endpoints

- `POST /search_similar`: query similar patterns directly
- `GET /knowledge_base/stats`: get pattern counts and categories

These endpoints return `503` if semantic scanning is disabled or unavailable.

## Operational Commands

Migrate knowledge base data:

```bash
python scripts/migrate_knowledge_base.py --source ../Agentic-Bug-Hunter/samples.csv --dest data/knowledge_base/samples.csv --validate
```

Rebuild vector store:

```bash
python scripts/rebuild_vector_store.py --knowledge-base data/knowledge_base/samples.csv --vector-store data/vector_store --embedding-model BAAI/bge-base-en-v1.5
```

Run integration validation:

```bash
python scripts/validate_integration.py --knowledge-base data/knowledge_base/samples.csv --vector-store data/vector_store --embedding-model BAAI/bge-base-en-v1.5
```

## Troubleshooting

- Empty semantic results:
  - Check `SECUREAI_ENABLE_SEMANTIC_SCANNING=true`
  - Confirm knowledge base CSV exists and has required columns
  - Rebuild vector store

- Slow scans:
  - Lower `SECUREAI_TOP_K_RESULTS`
  - Tune `SECUREAI_VECTOR_STORE_HNSW_EF`
  - Tune `SECUREAI_EMBEDDING_BATCH_SIZE`

- Startup failures:
  - Verify embedding dependencies are installed from `requirements.txt`
  - Validate CSV file format with migration script
