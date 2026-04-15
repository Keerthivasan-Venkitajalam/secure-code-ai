"""
Tests for Vector Store

This module contains unit tests and property-based tests for the VectorStore
component of the Agentic Bug Hunter integration.
"""

import pytest
import os
import tempfile
import shutil
import numpy as np
from pathlib import Path
from hypothesis import given, strategies as st, settings, HealthCheck

from agent.knowledge import VectorStore, SearchResult, VectorStoreStats


# ============================================================================
# Property-Based Tests
# ============================================================================

@settings(
    max_examples=10,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    deadline=None
)
@given(
    n_patterns=st.integers(min_value=5, max_value=20),
    embedding_dim=st.just(768),  # Fixed dimension for BGE model
    rebuild_count=st.integers(min_value=2, max_value=3)
)
def test_vector_store_rebuild_consistency(n_patterns, embedding_dim, rebuild_count):
    """
    Feature: agentic-bug-hunter-integration
    Property 5: Vector Store Rebuild Consistency
    
    For any knowledge base, rebuilding the vector store should produce embeddings
    that yield equivalent search results (within floating-point precision) to the
    original vector store.
    
    Validates: Requirements 2.3, 2.5
    """
    # Create temporary directory for vector store
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Generate random embeddings and documents
        embeddings = np.random.randn(n_patterns, embedding_dim).astype(np.float32)
        # Normalize embeddings (as sentence transformers does)
        embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
        
        documents = [f"document_{i}" for i in range(n_patterns)]
        metadatas = [{"pattern_id": str(i), "category": f"cat_{i % 3}"} for i in range(n_patterns)]
        ids = [str(i) for i in range(n_patterns)]
        
        # Create a query embedding
        query_embedding = np.random.randn(embedding_dim).astype(np.float32)
        query_embedding = query_embedding / np.linalg.norm(query_embedding)
        
        # Build and query vector store multiple times
        search_results_list = []
        
        for rebuild_idx in range(rebuild_count):
            # Create a new vector store instance
            vs = VectorStore(
                persist_directory=temp_dir,
                collection_name=f"test_collection_{rebuild_idx}"
            )
            
            # Add embeddings
            vs.add_embeddings(
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            
            # Perform search
            results = vs.search(query_embedding=query_embedding, top_k=5)
            
            # Store results for comparison
            search_results_list.append({
                'result_ids': [r.id for r in results],
                'result_similarities': [r.similarity for r in results],
                'result_documents': [r.document for r in results]
            })
            
            # Clean up this collection
            vs.delete_collection()
        
        # Property: All rebuilds should produce consistent results
        first_results = search_results_list[0]
        
        for idx, results in enumerate(search_results_list[1:], start=1):
            # Check that result IDs are the same (same documents retrieved)
            assert results['result_ids'] == first_results['result_ids'], \
                f"Rebuild {idx}: Result IDs should be identical across rebuilds"
            
            # Check that documents are the same
            assert results['result_documents'] == first_results['result_documents'], \
                f"Rebuild {idx}: Result documents should be identical across rebuilds"
            
            # Check that similarities are close (within floating-point precision)
            for i, (sim1, sim2) in enumerate(zip(first_results['result_similarities'], 
                                                   results['result_similarities'])):
                assert abs(sim1 - sim2) < 1e-5, \
                    f"Rebuild {idx}, Result {i}: Similarity scores should be nearly identical " \
                    f"(got {sim1} vs {sim2}, diff={abs(sim1 - sim2)})"
    
    finally:
        # Clean up
        shutil.rmtree(temp_dir, ignore_errors=True)


# ============================================================================
# Unit Tests
# ============================================================================

def test_add_and_search_embeddings():
    """
    Test adding embeddings and searching for similar ones.
    
    Requirements: 2.4
    """
    temp_dir = tempfile.mkdtemp()
    
    try:
        vs = VectorStore(persist_directory=temp_dir, collection_name="test_add_search")
        
        # Create test embeddings (768-dimensional)
        embeddings = np.array([
            [1.0] + [0.0] * 767,  # First dimension is 1
            [0.0, 1.0] + [0.0] * 766,  # Second dimension is 1
            [0.0, 0.0, 1.0] + [0.0] * 765,  # Third dimension is 1
        ], dtype=np.float32)
        
        # Normalize embeddings
        embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
        
        documents = ["doc1", "doc2", "doc3"]
        metadatas = [{"id": "1"}, {"id": "2"}, {"id": "3"}]
        ids = ["1", "2", "3"]
        
        # Add embeddings
        vs.add_embeddings(
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        
        # Search with a query similar to the first embedding
        query = np.array([1.0] + [0.0] * 767, dtype=np.float32)
        query = query / np.linalg.norm(query)
        
        results = vs.search(query_embedding=query, top_k=3)
        
        # Verify results
        assert len(results) == 3
        assert results[0].id == "1"  # Most similar should be first
        assert results[0].document == "doc1"
        assert results[0].similarity > 0.9  # Should be very similar
        
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_search_with_filter():
    """
    Test searching with metadata filter.
    
    Requirements: 2.4
    """
    temp_dir = tempfile.mkdtemp()
    
    try:
        vs = VectorStore(persist_directory=temp_dir, collection_name="test_filter")
        
        # Create test embeddings
        embeddings = np.random.randn(5, 768).astype(np.float32)
        embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
        
        documents = [f"doc{i}" for i in range(5)]
        metadatas = [
            {"category": "hardware"},
            {"category": "lifecycle"},
            {"category": "hardware"},
            {"category": "api"},
            {"category": "hardware"}
        ]
        ids = [str(i) for i in range(5)]
        
        # Add embeddings
        vs.add_embeddings(
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        
        # Search with filter for hardware category
        query = np.random.randn(768).astype(np.float32)
        query = query / np.linalg.norm(query)
        
        results = vs.search(
            query_embedding=query,
            top_k=10,
            filter={"category": "hardware"}
        )
        
        # Verify only hardware results returned
        assert len(results) == 3  # Only 3 hardware patterns
        for result in results:
            assert result.metadata["category"] == "hardware"
        
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_memory_limit_enforcement():
    """
    Test that memory limit warnings are logged (soft limit).
    
    Requirements: 2.4, 2.5
    """
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Create vector store with very low memory limit
        vs = VectorStore(
            persist_directory=temp_dir,
            collection_name="test_memory",
            max_memory_mb=1  # Very low limit
        )
        
        # Add many embeddings to exceed the limit
        n_patterns = 100
        embeddings = np.random.randn(n_patterns, 768).astype(np.float32)
        embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
        
        documents = [f"doc{i}" for i in range(n_patterns)]
        metadatas = [{"id": str(i)} for i in range(n_patterns)]
        ids = [str(i) for i in range(n_patterns)]
        
        # This should trigger a warning but not fail
        vs.add_embeddings(
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        
        # Verify data was still added
        stats = vs.get_stats()
        assert stats.document_count == n_patterns
        
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_collection_deletion():
    """
    Test deleting and recreating a collection.
    
    Requirements: 2.5
    """
    temp_dir = tempfile.mkdtemp()
    
    try:
        vs = VectorStore(persist_directory=temp_dir, collection_name="test_delete")
        
        # Add some embeddings
        embeddings = np.random.randn(5, 768).astype(np.float32)
        embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
        
        documents = [f"doc{i}" for i in range(5)]
        metadatas = [{"id": str(i)} for i in range(5)]
        ids = [str(i) for i in range(5)]
        
        vs.add_embeddings(
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        
        # Verify data exists
        stats = vs.get_stats()
        assert stats.document_count == 5
        
        # Delete collection
        vs.delete_collection()
        
        # Verify collection is empty
        stats = vs.get_stats()
        assert stats.document_count == 0
        
        # Verify we can add data again
        vs.add_embeddings(
            embeddings=embeddings[:2],
            documents=documents[:2],
            metadatas=metadatas[:2],
            ids=ids[:2]
        )
        
        stats = vs.get_stats()
        assert stats.document_count == 2
        
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_get_stats():
    """
    Test getting statistics about the vector store.
    
    Requirements: 2.4
    """
    temp_dir = tempfile.mkdtemp()
    
    try:
        vs = VectorStore(persist_directory=temp_dir, collection_name="test_stats")
        
        # Initially empty
        stats = vs.get_stats()
        assert stats.collection_name == "test_stats"
        assert stats.document_count == 0
        assert stats.memory_usage_mb >= 0
        
        # Add some embeddings
        n_patterns = 10
        embeddings = np.random.randn(n_patterns, 768).astype(np.float32)
        embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
        
        documents = [f"doc{i}" for i in range(n_patterns)]
        metadatas = [{"id": str(i)} for i in range(n_patterns)]
        ids = [str(i) for i in range(n_patterns)]
        
        vs.add_embeddings(
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        
        # Check stats after adding
        stats = vs.get_stats()
        assert stats.document_count == n_patterns
        assert stats.memory_usage_mb > 0
        
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_empty_embeddings():
    """
    Test handling of empty embeddings list.
    
    Requirements: 2.5
    """
    temp_dir = tempfile.mkdtemp()
    
    try:
        vs = VectorStore(persist_directory=temp_dir, collection_name="test_empty")
        
        # Try to add empty embeddings
        vs.add_embeddings(
            embeddings=np.array([]),
            documents=[],
            metadatas=[],
            ids=[]
        )
        
        # Should not fail, just log a warning
        stats = vs.get_stats()
        assert stats.document_count == 0
        
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_input_length_mismatch():
    """
    Test error handling for mismatched input lengths.
    
    Requirements: 2.5
    """
    temp_dir = tempfile.mkdtemp()
    
    try:
        vs = VectorStore(persist_directory=temp_dir, collection_name="test_mismatch")
        
        embeddings = np.random.randn(3, 768).astype(np.float32)
        documents = ["doc1", "doc2"]  # Wrong length
        metadatas = [{"id": "1"}, {"id": "2"}, {"id": "3"}]
        ids = ["1", "2", "3"]
        
        with pytest.raises(ValueError) as exc_info:
            vs.add_embeddings(
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
        
        assert "Input length mismatch" in str(exc_info.value)
        
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_search_empty_collection():
    """
    Test searching an empty collection.
    
    Requirements: 2.4
    """
    temp_dir = tempfile.mkdtemp()
    
    try:
        vs = VectorStore(persist_directory=temp_dir, collection_name="test_empty_search")
        
        # Search without adding any data
        query = np.random.randn(768).astype(np.float32)
        query = query / np.linalg.norm(query)
        
        results = vs.search(query_embedding=query, top_k=5)
        
        # Should return empty results
        assert len(results) == 0
        
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_persistence():
    """
    Test that data persists across vector store instances.
    
    Requirements: 2.4
    """
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Create first instance and add data
        vs1 = VectorStore(persist_directory=temp_dir, collection_name="test_persist")
        
        embeddings = np.random.randn(5, 768).astype(np.float32)
        embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
        
        documents = [f"doc{i}" for i in range(5)]
        metadatas = [{"id": str(i)} for i in range(5)]
        ids = [str(i) for i in range(5)]
        
        vs1.add_embeddings(
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        
        # Create second instance with same directory
        vs2 = VectorStore(persist_directory=temp_dir, collection_name="test_persist")
        
        # Verify data persisted
        stats = vs2.get_stats()
        assert stats.document_count == 5
        
        # Verify we can search the persisted data
        query = embeddings[0]  # Use first embedding as query
        results = vs2.search(query_embedding=query, top_k=1)
        
        assert len(results) == 1
        assert results[0].id == "0"
        
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_get_collection_info():
    """
    Test getting detailed collection information.
    
    Requirements: 2.4
    """
    temp_dir = tempfile.mkdtemp()
    
    try:
        vs = VectorStore(persist_directory=temp_dir, collection_name="test_info")
        
        info = vs.get_collection_info()
        
        assert info["name"] == "test_info"
        assert info["count"] == 0
        assert "metadata" in info
        assert info["persist_directory"] == temp_dir
        
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
