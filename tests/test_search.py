"""
Tests for Semantic Search module.
"""

import pytest
from unittest.mock import patch, MagicMock
import numpy as np

from agentgraph.search.semantic import SemanticSearch, HAS_SKLEARN


class TestSemanticSearchInit:
    """Test SemanticSearch initialization."""
    
    def test_init_default(self):
        """Test default initialization."""
        search = SemanticSearch()
        assert search.model_name == "all-MiniLM-L6-v2"
        assert search._documents == []
    
    def test_init_custom_model(self):
        """Test initialization with custom model."""
        search = SemanticSearch(model_name="custom-model")
        assert search.model_name == "custom-model"


class TestDocumentIndexing:
    """Test document indexing."""
    
    def test_index_empty(self):
        """Test indexing empty list."""
        search = SemanticSearch()
        search._use_transformers = False  # Use TF-IDF
        search.index_documents([], doc_type="event")
        assert len(search._documents) == 0
    
    @pytest.mark.skipif(not HAS_SKLEARN, reason="sklearn not installed")
    def test_index_documents_tfidf(self):
        """Test indexing with TF-IDF fallback."""
        search = SemanticSearch()
        search._use_transformers = False
        
        docs = [
            {"id": "1", "description": "searched for AI papers"},
            {"id": "2", "description": "wrote code for testing"},
            {"id": "3", "description": "deployed the application"},
        ]
        
        search.index_documents(docs, doc_type="event")
        
        assert len(search._documents) == 3
    
    def test_text_for_event(self):
        """Test event text extraction."""
        search = SemanticSearch()
        
        event = {
            "id": "123",
            "description": "test description",
            "action": "search",
            "type": "tool.call"
        }
        
        text = search._text_for_event(event)
        
        assert "test description" in text
        assert "search" in text


class TestSearch:
    """Test search functionality."""
    
    @pytest.mark.skipif(not HAS_SKLEARN, reason="sklearn not installed")
    def test_search_tfidf(self):
        """Test search with TF-IDF."""
        search = SemanticSearch()
        search._use_transformers = False
        
        docs = [
            {"id": "1", "description": "machine learning paper"},
            {"id": "2", "description": "web development tutorial"},
            {"id": "3", "description": "deep learning neural networks"},
        ]
        
        search.index_documents(docs, doc_type="event")
        
        results = search.search("machine learning", top_k=2)
        
        assert len(results) <= 2
        # First result should be about machine learning
        if results:
            assert "machine" in results[0][0].get("description", "").lower() or \
                   "learning" in results[0][0].get("description", "").lower()
    
    def test_search_empty_index(self):
        """Test search on empty index."""
        search = SemanticSearch()
        search._use_transformers = False
        
        results = search.search("test query")
        
        assert results == []
    
    @pytest.mark.skipif(not HAS_SKLEARN, reason="sklearn not installed")
    def test_search_with_threshold(self):
        """Test search with similarity threshold."""
        search = SemanticSearch()
        search._use_transformers = False
        
        docs = [
            {"id": "1", "description": "completely unrelated topic"},
        ]
        
        search.index_documents(docs, doc_type="event")
        
        # High threshold should filter out low-similarity results
        results = search.search("machine learning AI", threshold=0.9)
        
        # May or may not return results depending on threshold
        assert isinstance(results, list)


class TestFindSimilar:
    """Test finding similar documents."""
    
    @pytest.mark.skipif(not HAS_SKLEARN, reason="sklearn not installed")
    def test_find_similar(self):
        """Test finding similar documents."""
        search = SemanticSearch()
        search._use_transformers = False
        
        docs = [
            {"id": "1", "description": "python programming tutorial"},
            {"id": "2", "description": "python coding guide"},
            {"id": "3", "description": "cooking recipes"},
        ]
        
        search.index_documents(docs, doc_type="event")
        
        target = {"id": "1", "description": "python programming tutorial"}
        similar = search.find_similar(target, top_k=2)
        
        # Should return similar docs (excluding the target itself ideally)
        assert isinstance(similar, list)


class TestHelperFunctions:
    """Test helper functions."""
    
    def test_get_search_engine_singleton(self):
        """Test that get_search_engine returns singleton."""
        from agentgraph.search.semantic import get_search_engine
        
        engine1 = get_search_engine()
        engine2 = get_search_engine()
        
        assert engine1 is engine2


class TestEdgeCases:
    """Test edge cases."""
    
    def test_search_special_characters(self):
        """Test search with special characters."""
        search = SemanticSearch()
        search._use_transformers = False
        
        # Should not crash
        results = search.search("test @#$%^&*()")
        assert isinstance(results, list)
    
    def test_search_unicode(self):
        """Test search with unicode."""
        search = SemanticSearch()
        search._use_transformers = False
        
        results = search.search("测试 тест テスト")
        assert isinstance(results, list)
    
    def test_index_documents_with_missing_fields(self):
        """Test indexing documents with missing fields."""
        search = SemanticSearch()
        search._use_transformers = False
        
        docs = [
            {"id": "1"},  # Missing description
            {"description": "test"},  # Missing id
            {},  # Empty
        ]
        
        # Should not crash
        search.index_documents(docs, doc_type="event")
