"""
Semantic Search for AgentGraph

Uses sentence embeddings for intelligent event/entity search.
Falls back to TF-IDF if sentence-transformers not available.
"""

import json
import numpy as np
from typing import Dict, List, Optional, Tuple
from pathlib import Path

# Try to import sentence-transformers
try:
    from sentence_transformers import SentenceTransformer
    HAS_TRANSFORMERS = True
except ImportError:
    HAS_TRANSFORMERS = False

# Fallback to sklearn TF-IDF
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False


class SemanticSearch:
    """
    Semantic search engine for AgentGraph events and entities.
    
    Uses sentence embeddings when available, falls back to TF-IDF.
    """
    
    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        cache_dir: Optional[str] = None
    ):
        """
        Initialize the search engine.
        
        Args:
            model_name: Sentence transformer model name
            cache_dir: Directory to cache embeddings
        """
        self.model_name = model_name
        self.cache_dir = Path(cache_dir) if cache_dir else None
        self._model = None
        self._tfidf = None
        self._documents: List[Dict] = []
        self._embeddings: Optional[np.ndarray] = None
        self._use_transformers = HAS_TRANSFORMERS
    
    @property
    def model(self):
        """Lazy-load the embedding model."""
        if self._model is None and self._use_transformers:
            try:
                self._model = SentenceTransformer(self.model_name)
            except Exception as e:
                print(f"Warning: Failed to load transformer model: {e}")
                self._use_transformers = False
        return self._model
    
    def _text_for_event(self, event: Dict) -> str:
        """Extract searchable text from an event."""
        parts = []
        if event.get('action'):
            parts.append(event['action'])
        if event.get('description'):
            parts.append(event['description'])
        if event.get('type'):
            parts.append(event['type'])
        if event.get('input_data'):
            parts.append(json.dumps(event['input_data'])[:200])
        if event.get('output_data'):
            parts.append(json.dumps(event['output_data'])[:200])
        if event.get('tags'):
            parts.extend(event['tags'])
        return " ".join(parts)
    
    def _text_for_entity(self, entity: Dict) -> str:
        """Extract searchable text from an entity."""
        parts = []
        if entity.get('name'):
            parts.append(entity['name'])
        if entity.get('type'):
            parts.append(entity['type'])
        if entity.get('metadata'):
            parts.append(json.dumps(entity['metadata'])[:200])
        return " ".join(parts)
    
    def index_documents(self, documents: List[Dict], doc_type: str = "event"):
        """
        Index documents for searching.
        
        Args:
            documents: List of event or entity dicts
            doc_type: "event" or "entity"
        """
        self._documents = documents
        
        # Extract text from documents
        if doc_type == "event":
            texts = [self._text_for_event(doc) for doc in documents]
        else:
            texts = [self._text_for_entity(doc) for doc in documents]
        
        if not texts:
            return
        
        # Generate embeddings
        if self._use_transformers and self.model:
            self._embeddings = self.model.encode(texts, convert_to_numpy=True)
        elif HAS_SKLEARN:
            # Fall back to TF-IDF
            self._tfidf = TfidfVectorizer(stop_words='english', max_features=5000)
            self._embeddings = self._tfidf.fit_transform(texts).toarray()
        else:
            # No search available
            self._embeddings = None
    
    def search(
        self,
        query: str,
        top_k: int = 10,
        threshold: float = 0.3
    ) -> List[Tuple[Dict, float]]:
        """
        Search for documents matching the query.
        
        Args:
            query: Search query
            top_k: Number of results to return
            threshold: Minimum similarity score
            
        Returns:
            List of (document, score) tuples
        """
        if self._embeddings is None or len(self._documents) == 0:
            return []
        
        # Encode query
        if self._use_transformers and self.model:
            query_embedding = self.model.encode([query], convert_to_numpy=True)
        elif self._tfidf is not None:
            query_embedding = self._tfidf.transform([query]).toarray()
        else:
            return []
        
        # Calculate similarities
        similarities = cosine_similarity(query_embedding, self._embeddings)[0]
        
        # Get top results
        results = []
        indices = np.argsort(similarities)[::-1][:top_k]
        
        for idx in indices:
            score = float(similarities[idx])
            if score >= threshold:
                results.append((self._documents[idx], score))
        
        return results
    
    def find_similar(
        self,
        document: Dict,
        doc_type: str = "event",
        top_k: int = 5,
        exclude_self: bool = True
    ) -> List[Tuple[Dict, float]]:
        """
        Find documents similar to a given document.
        
        Args:
            document: The document to find similar items for
            doc_type: "event" or "entity"
            top_k: Number of results
            exclude_self: Whether to exclude the input document
            
        Returns:
            List of (document, score) tuples
        """
        if doc_type == "event":
            text = self._text_for_event(document)
        else:
            text = self._text_for_entity(document)
        
        results = self.search(text, top_k=top_k + 1 if exclude_self else top_k)
        
        if exclude_self and results:
            # Remove the input document if it's in results
            doc_id = document.get('id')
            results = [(doc, score) for doc, score in results if doc.get('id') != doc_id]
        
        return results[:top_k]


# Global search engine instance
_search_engine: Optional[SemanticSearch] = None


def get_search_engine() -> SemanticSearch:
    """Get or create the global search engine instance."""
    global _search_engine
    if _search_engine is None:
        _search_engine = SemanticSearch()
    return _search_engine
