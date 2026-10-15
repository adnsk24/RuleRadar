import hashlib
from collections import OrderedDict
import numpy as np
from typing import List, Union, Optional
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import logging

logger = logging.getLogger(__name__)

class EmbeddingService:
    """
    Dual-mode embedding engine with SHA-256 LRU caching:
    1. Primary: Lightweight SentenceTransformer ('all-MiniLM-L6-v2') on CPU
    2. Resilient Offline Fallback: TF-IDF with sublinear term-frequency and sub-word char n-grams
    Guarantees 100% availability with zero external API calls and zero paid services.
    """

    _instance = None
    _st_model = None
    _tfidf_vectorizer = None
    _is_st_available = False
    _cache: OrderedDict = OrderedDict()
    _MAX_CACHE_SIZE = 4096

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EmbeddingService, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Attempt to load SentenceTransformer; fallback to TF-IDF if offline/unavailable."""
        try:
            from sentence_transformers import SentenceTransformer
            logger.info("RuleRadar AI: Initializing SentenceTransformer ('all-MiniLM-L6-v2')...")
            self._st_model = SentenceTransformer('all-MiniLM-L6-v2')
            self._is_st_available = True
            logger.info("RuleRadar AI: SentenceTransformer successfully loaded on CPU.")
        except Exception as e:
            logger.warning(f"SentenceTransformer not loaded ({str(e)}). Engaging robust TF-IDF fallback engine.")
            self._is_st_available = False

        self._tfidf_vectorizer = TfidfVectorizer(
            ngram_range=(1, 3),
            analyzer="word",
            sublinear_tf=True,
            max_features=15000,
            token_pattern=r'(?u)\b\w+\b'
        )

    @property
    def model_type(self) -> str:
        return "SentenceTransformer (all-MiniLM-L6-v2)" if self._is_st_available else "TF-IDF N-Gram Vectorizer"

    def _hash_text(self, text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def _get_from_cache(self, h: str) -> Optional[np.ndarray]:
        if h in self._cache:
            self._cache.move_to_end(h)
            return self._cache[h]
        return None

    def _put_in_cache(self, h: str, vector: np.ndarray):
        if len(self._cache) >= self._MAX_CACHE_SIZE:
            self._cache.popitem(last=False)
        self._cache[h] = vector

    def encode(self, texts: Union[str, List[str]]) -> np.ndarray:
        """
        Compute dense or normalized vector embeddings for one or more strings with LRU caching.
        """
        if isinstance(texts, str):
            texts = [texts]

        if not texts:
            return np.empty((0, 384 if self._is_st_available else 128), dtype=np.float32)

        cleaned = [t.strip() if t and t.strip() else "empty clause" for t in texts]
        hashes = [self._hash_text(t) for t in cleaned]

        # Check cache hits
        results = [None] * len(cleaned)
        miss_indices = []
        miss_texts = []

        for idx, h in enumerate(hashes):
            cached_vec = self._get_from_cache(h)
            if cached_vec is not None:
                results[idx] = cached_vec
            else:
                miss_indices.append(idx)
                miss_texts.append(cleaned[idx])

        # If all hit cache, return assembled matrix immediately
        if not miss_indices:
            return np.array(results, dtype=np.float32)

        # Compute embeddings for misses
        new_embeddings = None
        if self._is_st_available and self._st_model is not None:
            try:
                new_embeddings = self._st_model.encode(
                    miss_texts,
                    convert_to_numpy=True,
                    normalize_embeddings=True,
                    batch_size=32,
                    show_progress_bar=False
                )
            except Exception as e:
                logger.warning(f"SentenceTransformer encoding failed: {e}. Falling back to TF-IDF.")
                new_embeddings = None

        if new_embeddings is None:
            # Fallback TF-IDF
            try:
                matrix = self._tfidf_vectorizer.fit_transform(cleaned)
                return matrix.toarray()
            except Exception:
                dim = 128
                out = np.zeros((len(cleaned), dim), dtype=np.float32)
                for i, text in enumerate(cleaned):
                    for word in text.split():
                        h_val = hash(word) % dim
                        out[i, h_val] += 1.0
                    norm = np.linalg.norm(out[i])
                    if norm > 0:
                        out[i] /= norm
                return out

        # Store misses into cache and assemble final results
        for i, original_idx in enumerate(miss_indices):
            vec = new_embeddings[i]
            self._put_in_cache(hashes[original_idx], vec)
            results[original_idx] = vec

        return np.array(results, dtype=np.float32)

    def compute_similarity(self, query: str, candidate_texts: List[str]) -> List[float]:
        """
        Compute cosine similarity between a single query and a list of candidate texts.
        Returns a list of float scores in range [0.0, 1.0].
        """
        if not candidate_texts:
            return []

        q_clean = query.strip() if query and query.strip() else "empty query"
        q_emb = self.encode([q_clean])
        c_emb = self.encode(candidate_texts)

        # Dot product of normalized unit vectors = cosine similarity
        sims = np.dot(c_emb, q_emb.T).flatten()
        return [float(max(0.0, min(1.0, s))) for s in sims]

    def pairwise_similarity(self, texts_a: List[str], texts_b: List[str]) -> np.ndarray:
        """
        Compute full pairwise cosine similarity matrix between texts_a and texts_b.
        Returns an (len(texts_a), len(texts_b)) numpy array.
        """
        if not texts_a or not texts_b:
            return np.zeros((len(texts_a), len(texts_b)), dtype=np.float32)

        emb_a = self.encode(texts_a)
        emb_b = self.encode(texts_b)

        if emb_a.shape[1] != emb_b.shape[1]:
            combined = texts_a + texts_b
            vec = TfidfVectorizer(ngram_range=(1, 2)).fit(combined)
            emb_a = vec.transform(texts_a).toarray()
            emb_b = vec.transform(texts_b).toarray()

        sims = np.dot(emb_a, emb_b.T)
        return np.clip(sims, 0.0, 1.0)

embedding_service = EmbeddingService()

