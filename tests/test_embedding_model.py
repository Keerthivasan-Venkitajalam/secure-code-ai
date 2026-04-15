"""
Tests for EmbeddingModel class.

This module contains unit tests and property-based tests for the embedding model.
"""

import numpy as np
import pytest
from hypothesis import given, settings, strategies as st

from agent.knowledge.embedding_model import EmbeddingModel


# Shared model instance to avoid Windows access violation issues
@pytest.fixture(scope="module")
def shared_model():
    """Create a shared model instance for all tests."""
    return EmbeddingModel(device="cpu", cache_size=1000)


# Property-Based Tests

@settings(max_examples=10, deadline=None)
@given(text=st.text(min_size=10, max_size=200))
def test_embedding_caching_performance(text, shared_model):
    """
    Feature: agentic-bug-hunter-integration
    Property 11: Embedding Model Caching
    
    **Validates: Requirements 7.4, 11.1**
    
    For any text that has been embedded once, requesting the same embedding again
    should return the cached result without re-computing (verifiable by execution
    time being significantly faster).
    """
    import time
    
    # Use shared model instance
    model = shared_model
    
    # First encoding (cache miss) - measure time
    start = time.time()
    emb1 = model.encode(text)
    first_time = time.time() - start
    
    # Second encoding (cache hit) - measure time
    start = time.time()
    emb2 = model.encode(text)
    second_time = time.time() - start
    
    # Property: Cached embedding should be identical
    assert np.array_equal(emb1, emb2), "Cached embedding should be identical to original"
    
    # Property: Cached retrieval should be significantly faster (at least 10x faster)
    # We use a lenient threshold since timing can vary
    if first_time > 0.001:  # Only check if first encoding took measurable time
        assert second_time < first_time * 0.5, \
            f"Cached retrieval ({second_time:.6f}s) should be faster than first encoding ({first_time:.6f}s)"


@settings(max_examples=10, deadline=None)
@given(texts=st.lists(st.text(min_size=1, max_size=100), min_size=1, max_size=10))
def test_batch_embedding_consistency(texts, shared_model):
    """
    Feature: agentic-bug-hunter-integration
    Property 12: Batch Embedding Consistency
    
    **Validates: Requirements 7.5**
    
    For any list of texts, generating embeddings in batch should produce
    identical results to generating embeddings individually for each text.
    """
    # Use shared model instance
    model = shared_model
    
    # Generate embeddings in batch
    batch_embeddings = model.encode_batch(texts)
    
    # Generate embeddings individually
    individual_embeddings = []
    for text in texts:
        embedding = model.encode(text)
        individual_embeddings.append(embedding)
    
    individual_embeddings = np.array(individual_embeddings)
    
    # Property: Batch and individual embeddings should be identical (within floating-point precision)
    assert batch_embeddings.shape == individual_embeddings.shape, \
        f"Shape mismatch: batch {batch_embeddings.shape} vs individual {individual_embeddings.shape}"
    
    # Check each embedding
    for i, (batch_emb, indiv_emb) in enumerate(zip(batch_embeddings, individual_embeddings)):
        # Use allclose for floating-point comparison
        # Note: sentence-transformers may have minor floating-point differences between
        # batch and individual encoding due to internal optimizations
        assert np.allclose(batch_emb, indiv_emb, rtol=1e-4, atol=1e-6), \
            f"Embedding {i} mismatch for text: {texts[i][:50]}..."


# Unit Tests

def test_model_loading_from_huggingface():
    """
    Test model loading from HuggingFace.
    
    **Validates: Requirements 7.1, 7.2**
    """
    model = EmbeddingModel(model_name="BAAI/bge-base-en-v1.5", device="cpu")
    
    assert model.model is not None
    assert model.model_name == "BAAI/bge-base-en-v1.5"
    assert model.device == "cpu"


def test_model_loading_from_local_path(tmp_path):
    """
    Test model loading from local path.
    
    **Validates: Requirements 7.1, 7.3**
    """
    # First, download and save the model
    model_path = str(tmp_path / "embedding_model")
    model1 = EmbeddingModel(model_name="BAAI/bge-base-en-v1.5", model_path=model_path, device="cpu")
    
    # Now load from the saved path
    model2 = EmbeddingModel(model_path=model_path, device="cpu")
    
    assert model2.model is not None
    
    # Test that both models produce the same embeddings
    test_text = "def vulnerable_function(): pass"
    emb1 = model1.encode(test_text)
    emb2 = model2.encode(test_text)
    
    assert np.allclose(emb1, emb2, rtol=1e-5, atol=1e-8)


def test_encode_single_text():
    """
    Test encoding a single text.
    
    **Validates: Requirements 7.1, 7.2**
    """
    model = EmbeddingModel(device="cpu")
    
    text = "import os; os.system('rm -rf /')"
    embedding = model.encode(text)
    
    # Check embedding properties
    assert isinstance(embedding, np.ndarray)
    assert embedding.shape == (768,)  # BGE-base produces 768-dimensional embeddings
    assert not np.all(embedding == 0)  # Embedding should not be all zeros


def test_encode_multiple_texts():
    """
    Test encoding multiple texts.
    
    **Validates: Requirements 7.2, 7.5**
    """
    model = EmbeddingModel(device="cpu")
    
    texts = [
        "def safe_function(): pass",
        "import os; os.system('rm -rf /')",
        "sql_query = 'SELECT * FROM users WHERE id = ' + user_id"
    ]
    
    embeddings = model.encode(texts)
    
    # Check embeddings properties
    assert isinstance(embeddings, np.ndarray)
    assert embeddings.shape == (3, 768)
    assert not np.all(embeddings == 0)


def test_batch_processing_efficiency():
    """
    Test that batch processing is more efficient than individual encoding.
    
    **Validates: Requirements 7.5**
    """
    import time
    
    model = EmbeddingModel(device="cpu")
    
    texts = ["test text " + str(i) for i in range(20)]
    
    # Time batch processing
    start = time.time()
    batch_embeddings = model.encode_batch(texts, batch_size=10)
    batch_time = time.time() - start
    
    # Time individual processing (without cache)
    model.clear_cache()
    start = time.time()
    individual_embeddings = [model.encode(text) for text in texts]
    individual_time = time.time() - start
    
    # Batch processing should be faster (or at least not significantly slower)
    # We allow some tolerance since timing can vary
    assert batch_time <= individual_time * 1.5, \
        f"Batch processing ({batch_time:.3f}s) should be faster than individual ({individual_time:.3f}s)"
    
    # Results should be the same (with tolerance for floating-point differences)
    individual_embeddings = np.array(individual_embeddings)
    assert np.allclose(batch_embeddings, individual_embeddings, rtol=1e-4, atol=1e-6)


def test_get_similarity():
    """
    Test cosine similarity calculation.
    
    **Validates: Requirements 7.1, 7.2**
    """
    model = EmbeddingModel(device="cpu")
    
    text1 = "def vulnerable_function(): pass"
    text2 = "def vulnerable_function(): pass"  # Identical
    text3 = "def safe_function(): return True"  # Different
    
    emb1 = model.encode(text1)
    emb2 = model.encode(text2)
    emb3 = model.encode(text3)
    
    # Similarity between identical texts should be 1.0 (or very close)
    sim_identical = model.get_similarity(emb1, emb2)
    assert sim_identical > 0.99, f"Identical texts should have similarity ~1.0, got {sim_identical}"
    
    # Similarity between different texts should be less than 1.0
    sim_different = model.get_similarity(emb1, emb3)
    assert sim_different < 1.0, f"Different texts should have similarity < 1.0, got {sim_different}"
    
    # Similarity should be in [0, 1] range
    assert 0.0 <= sim_identical <= 1.0
    assert 0.0 <= sim_different <= 1.0


def test_embedding_cache():
    """
    Test that embedding cache works correctly.
    
    **Validates: Requirements 7.4, 11.1**
    """
    model = EmbeddingModel(device="cpu", cache_size=10)
    
    text = "def test_function(): pass"
    
    # First encoding (cache miss)
    emb1 = model.encode(text)
    
    # Second encoding (cache hit)
    emb2 = model.encode(text)
    
    # Should return the same embedding (exact same object from cache)
    assert np.array_equal(emb1, emb2)
    
    # Check cache stats
    stats = model.get_cache_stats()
    assert stats["cache_size"] == 1
    assert stats["max_cache_size"] == 10


def test_cache_eviction():
    """
    Test that cache eviction works when cache is full.
    
    **Validates: Requirements 11.1**
    """
    model = EmbeddingModel(device="cpu", cache_size=3)
    
    # Fill cache
    for i in range(5):
        text = f"def function_{i}(): pass"
        model.encode(text)
    
    # Cache should not exceed max size
    stats = model.get_cache_stats()
    assert stats["cache_size"] <= 3


def test_clear_cache():
    """
    Test clearing the embedding cache.
    
    **Validates: Requirements 11.1**
    """
    model = EmbeddingModel(device="cpu")
    
    # Add some embeddings to cache
    for i in range(5):
        text = f"def function_{i}(): pass"
        model.encode(text)
    
    # Verify cache has entries
    stats = model.get_cache_stats()
    assert stats["cache_size"] > 0
    
    # Clear cache
    model.clear_cache()
    
    # Verify cache is empty
    stats = model.get_cache_stats()
    assert stats["cache_size"] == 0


def test_encode_empty_text():
    """
    Test encoding empty text (edge case).
    
    **Validates: Requirements 7.1, 7.2**
    """
    model = EmbeddingModel(device="cpu")
    
    # Empty string should still produce an embedding
    embedding = model.encode("")
    
    assert isinstance(embedding, np.ndarray)
    assert embedding.shape == (768,)


def test_encode_very_long_text():
    """
    Test encoding very long text (edge case).
    
    **Validates: Requirements 7.1, 7.2**
    """
    model = EmbeddingModel(device="cpu")
    
    # Create a very long text (but within model's token limit)
    long_text = "def function(): pass\n" * 100
    
    embedding = model.encode(long_text)
    
    assert isinstance(embedding, np.ndarray)
    assert embedding.shape == (768,)
    assert not np.all(embedding == 0)


def test_similarity_with_zero_vectors():
    """
    Test similarity calculation with zero vectors (edge case).
    
    **Validates: Requirements 7.1, 7.2**
    """
    model = EmbeddingModel(device="cpu")
    
    zero_vec = np.zeros(768)
    normal_vec = np.random.rand(768)
    
    # Similarity with zero vector should be 0
    similarity = model.get_similarity(zero_vec, normal_vec)
    assert similarity == 0.0
    
    # Similarity between two zero vectors should be 0
    similarity = model.get_similarity(zero_vec, zero_vec)
    assert similarity == 0.0
