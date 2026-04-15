# Knowledge Base Management

This document describes how to maintain bug-pattern data used by semantic scanning.

## File Format

Knowledge base file is a CSV with these required columns:

- `ID`
- `Explanation`
- `Context`
- `Code`
- `Correct Code`

Optional columns:

- `Category`
- `Severity`

`agent/knowledge/knowledge_base.py` loads this schema and enforces required columns.

## Storage Paths

Default paths:

- Knowledge base: `data/knowledge_base/samples.csv`
- Vector store: `data/vector_store`

These can be overridden with:

- `SECUREAI_KNOWLEDGE_BASE_PATH`
- `SECUREAI_VECTOR_STORE_PATH`

## Adding Patterns

1. Add rows to the CSV with valid required fields.
2. Keep `ID` unique.
3. Use normalized category/severity values.
4. Rebuild the vector store after updates.

## Migration Workflow

Use the migration script when importing from external datasets:

```bash
python scripts/migrate_knowledge_base.py --source ../Agentic-Bug-Hunter/samples.csv --dest data/knowledge_base/samples.csv --validate --report migration_report.json
```

Migration script validates:

- Required columns
- Empty mandatory values
- Category normalization
- Severity normalization

## Vector Store Rebuild

Rebuild after any major CSV change:

```bash
python scripts/rebuild_vector_store.py --knowledge-base data/knowledge_base/samples.csv --vector-store data/vector_store --embedding-model BAAI/bge-base-en-v1.5
```

What rebuild does:

1. Loads all patterns
2. Generates embeddings
3. Recreates `bug_patterns` collection
4. Verifies search integrity

## Validation Checks

Run integration checks before deployment:

```bash
python scripts/validate_integration.py --knowledge-base data/knowledge_base/samples.csv --vector-store data/vector_store --embedding-model BAAI/bge-base-en-v1.5
```

Checks include:

- Dependency availability
- Knowledge base loading
- Embedding generation
- Vector store accessibility
- Validator behavior
- Semantic search smoke test

## API Verification

After startup, verify semantic endpoints:

```bash
curl http://localhost:8000/knowledge_base/stats
```

```bash
curl -X POST http://localhost:8000/search_similar -H "Content-Type: application/json" -d "{\"query\":\"set_voltag(35)\",\"top_k\":5}"
```

## Common Failure Modes

- Missing required CSV columns: migration/loader fails
- Empty vector store: semantic search returns no hits
- Invalid model path: embedding initialization fails
- Path mismatch: API uses different KB/vector paths than scripts
