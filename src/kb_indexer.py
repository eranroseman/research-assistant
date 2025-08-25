"""FAISS indexing and embedding generation module for Research Assistant.

This module handles all search index functionality, including:
- Multi-QA MPNet embedding generation
- FAISS index creation and updates
- Embedding caching for performance
- GPU/CPU device detection and optimization
"""

import json
import hashlib
from pathlib import Path
from typing import Any
import numpy as np


# ============================================================================
# CUSTOM EXCEPTIONS
# ============================================================================


class EmbeddingGenerationError(Exception):
    """Exception raised when embedding generation fails."""


# ============================================================================
# MAIN INDEXER CLASS
# ============================================================================


class KBIndexer:
    """Handles FAISS indexing and embedding generation for the knowledge base.

    Features:
    - Multi-QA MPNet embeddings optimized for healthcare/scientific papers
    - GPU acceleration when available
    - Smart embedding caching to avoid regeneration
    - Incremental index updates for efficiency
    """

    def __init__(self, knowledge_base_path: str, use_gpu: bool = True):
        """Initialize the KB indexer.

        Args:
            knowledge_base_path: Path to the knowledge base directory
            use_gpu: Whether to use GPU if available
        """
        self.knowledge_base_path = Path(knowledge_base_path)
        self.index_file_path = self.knowledge_base_path / "index.faiss"
        self.metadata_file_path = self.knowledge_base_path / "metadata.json"

        # Embedding model (lazy loaded)
        self._embedding_model: Any = None
        self.model_version: str | None = None

        # Cache for embeddings
        self.embedding_cache: dict[str, Any] | None = None

        # Device detection
        self.use_gpu = use_gpu
        self.device = self._detect_device()

    def _detect_device(self) -> str:
        """Detect whether GPU is available for computation."""
        if not self.use_gpu:
            return "cpu"

        try:
            import torch

            return "cuda" if torch.cuda.is_available() else "cpu"
        except ImportError:
            return "cpu"

    @property
    def embedding_model(self) -> Any:
        """Lazy load and return the embedding model.

        Returns:
            SentenceTransformer model configured for Multi-QA MPNet embeddings
        """
        if self._embedding_model is None:
            from sentence_transformers import SentenceTransformer

            # Device already detected in __init__, just report it
            if self.device == "cuda":
                print("GPU detected! Using CUDA for faster embeddings")
            else:
                print("Using CPU for embeddings (GPU not available)")

            # Load Multi-QA MPNet model optimized for healthcare and scientific papers
            print("Loading Multi-QA MPNet embedding model...")
            # Import config for embedding model
            try:
                from src.config import EMBEDDING_MODEL
            except ImportError:
                from config import EMBEDDING_MODEL  # type: ignore[no-redef]

            self._embedding_model = SentenceTransformer(EMBEDDING_MODEL, device=self.device)
            self.model_version = "Multi-QA MPNet"
            print(f"Multi-QA MPNet model loaded successfully on {self.device}")

        return self._embedding_model

    def get_optimal_batch_size(self) -> int:
        """Determine optimal batch size based on available memory.

        Returns:
            Batch size optimized for GPU/CPU memory constraints
        """
        try:
            import psutil

            mem = psutil.virtual_memory()
            available_gb = mem.available / (1024**3)
            total_gb = mem.total / (1024**3)

            # Adjust batch size for GPU if available
            if hasattr(self, "device") and self.device == "cuda":
                try:
                    import torch

                    if torch.cuda.is_available():
                        # Get GPU memory in GB
                        gpu_memory = torch.cuda.get_device_properties(0).total_memory / (1024**3)
                        if gpu_memory > 8:
                            batch_size = 256
                        elif gpu_memory > 4:
                            batch_size = 128
                        else:
                            batch_size = 64
                        print(f"Using batch size {batch_size} for GPU with {gpu_memory:.1f}GB memory")
                        return batch_size
                except Exception as e:
                    print(f"Warning: Could not determine GPU memory: {e}")

            # CPU memory-based batch sizing
            if available_gb > 16:
                batch_size = 256
            elif available_gb > 8:
                batch_size = 128
            else:
                batch_size = 64

            print(
                f"Using batch size {batch_size} based on {available_gb:.1f}GB available (of {total_gb:.1f}GB total)",
            )

            # Note: On CPU, batch size has minimal impact on speed since the bottleneck
            # is model computation, not memory bandwidth. Larger batches may even be slower.
            return batch_size

        except ImportError:
            # If psutil not available, use conservative default
            return 128  # Better than original 64

    def get_embedding_hash(self, text: str) -> str:
        """Generate SHA256 hash for embedding cache key.

        Args:
            text: Text to hash

        Returns:
            Hexadecimal hash string
        """
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def load_embedding_cache(self) -> dict[str, Any]:
        """Load the embedding cache from disk.

        Returns:
            Dictionary with 'embeddings' numpy array and 'hashes' list
        """
        if self.embedding_cache is not None:
            return self.embedding_cache

        # Use config constants for cache file names
        try:
            from src.config import EMBEDDING_CACHE_FILE
        except ImportError:
            from config import EMBEDDING_CACHE_FILE  # type: ignore[no-redef]

        json_cache_path = self.knowledge_base_path / EMBEDDING_CACHE_FILE.name
        npy_cache_path = self.knowledge_base_path / ".embedding_data.npy"

        if json_cache_path.exists() and npy_cache_path.exists():
            import numpy as np

            with json_cache_path.open() as f:
                cache_meta = json.load(f)
            embeddings = np.load(npy_cache_path, allow_pickle=False)
            self.embedding_cache = {
                "embeddings": embeddings,
                "hashes": cache_meta["hashes"],
                "model_name": cache_meta["model_name"],
            }
            # Silent - just return the cache
            return self.embedding_cache

        self.embedding_cache = {"embeddings": None, "hashes": []}
        return self.embedding_cache

    def save_embedding_cache(self, embeddings: Any, hashes: list[str]) -> None:
        """Save embeddings to cache files (JSON metadata + NPY data).

        Args:
            embeddings: Numpy array of embedding vectors
            hashes: List of content hashes for cache validation
        """
        from datetime import datetime, UTC

        # Save metadata to JSON
        try:
            from src.config import EMBEDDING_CACHE_FILE
        except ImportError:
            from config import EMBEDDING_CACHE_FILE  # type: ignore[no-redef]

        json_cache_path = self.knowledge_base_path / EMBEDDING_CACHE_FILE.name
        cache_meta = {
            "hashes": hashes,
            "model_name": "Multi-QA MPNet",
            "created_at": datetime.now(UTC).isoformat(),
        }
        with json_cache_path.open("w") as f:
            json.dump(cache_meta, f, indent=2)

        # Save embeddings to NPY
        npy_cache_path = self.knowledge_base_path / ".embedding_data.npy"
        np.save(npy_cache_path, embeddings, allow_pickle=False)
        # Silent - cache saved

    def generate_embeddings(self, texts: list[str], show_progress: bool = True) -> Any:
        """Generate embeddings for a list of texts using cached values when possible.

        Args:
            texts: List of texts to embed
            show_progress: Whether to show progress bar

        Returns:
            Numpy array of embeddings
        """
        from tqdm import tqdm

        # Load cache
        cache = self.load_embedding_cache()
        cached_embeddings = cache.get("embeddings")
        cached_hashes = cache.get("hashes", [])

        # Determine which texts need new embeddings
        all_embeddings = []
        all_hashes = []
        texts_to_embed = []
        text_indices = []

        for i, text in enumerate(texts):
            text_hash = self.get_embedding_hash(text)
            all_hashes.append(text_hash)

            # Check if we have cached embedding
            if cached_embeddings is not None and text_hash in cached_hashes:
                cache_idx = cached_hashes.index(text_hash)
                all_embeddings.append(cached_embeddings[cache_idx])
            else:
                texts_to_embed.append(text)
                text_indices.append(i)

        # Generate new embeddings if needed
        if texts_to_embed:
            print(
                f"Generating embeddings for {len(texts_to_embed)} papers (reusing {len(texts) - len(texts_to_embed)} cached)..."
            )

            batch_size = self.get_optimal_batch_size()
            new_embeddings = []

            # Process in batches
            for i in tqdm(
                range(0, len(texts_to_embed), batch_size), desc="Embedding batches", disable=not show_progress
            ):
                batch = texts_to_embed[i : i + batch_size]
                batch_embeddings = self.embedding_model.encode(
                    batch,
                    convert_to_numpy=True,
                    show_progress_bar=False,
                )
                new_embeddings.extend(batch_embeddings)

            # Insert new embeddings at correct positions
            new_embeddings_array = np.array(new_embeddings)
            for idx, embedding in zip(text_indices, new_embeddings_array, strict=False):
                # Replace placeholder positions with actual embeddings
                if idx < len(all_embeddings):
                    all_embeddings[idx] = embedding
                else:
                    all_embeddings.insert(idx, embedding)

        return np.array(all_embeddings, dtype="float32")

    def create_index(self, papers: list[dict[str, Any]]) -> Any:
        """Create FAISS index from papers.

        Args:
            papers: List of paper dictionaries with title/abstract

        Returns:
            FAISS index object
        """
        import faiss

        # Extract texts for embedding
        texts = []
        for paper in papers:
            title = paper.get("title", "").strip()
            abstract = paper.get("abstract", "").strip()
            embedding_text = f"{title} [SEP] {abstract}" if abstract else title
            texts.append(embedding_text)

        if not texts:
            # Return empty index
            try:
                from src.config import EMBEDDING_DIMENSIONS
            except ImportError:
                from config import EMBEDDING_DIMENSIONS  # type: ignore[no-redef]
            return faiss.IndexFlatL2(EMBEDDING_DIMENSIONS)

        # Generate embeddings
        embeddings = self.generate_embeddings(texts)

        # Save cache for future use
        hashes = [self.get_embedding_hash(text) for text in texts]
        self.save_embedding_cache(embeddings, hashes)

        # Create FAISS index
        dimension = embeddings.shape[1]
        index = faiss.IndexFlatL2(dimension)
        index.add(embeddings.astype("float32"))

        print(f"Index created with {len(embeddings)} vectors of dimension {dimension}")
        return index

    def update_index_incrementally(self, papers: list[dict[str, Any]], changes: dict[str, Any]) -> None:
        """Update FAISS index incrementally for changed papers only.

        Args:
            papers: List of all paper metadata dictionaries
            changes: Dictionary with 'new_keys', 'updated_keys', 'deleted_keys'
        """
        import faiss

        # Identify papers that need new embeddings
        # Quality score upgrades don't change text content, so exclude them from embedding changes
        quality_upgrades = changes.get("quality_upgrades", set())
        changed_keys = (
            changes.get("new_keys", set()) | set(changes.get("updated_keys", []))
        ) - quality_upgrades

        if not changed_keys and not changes.get("deleted_keys"):
            print("No embedding changes needed")
            return

        print(f"Updating index for {len(changed_keys)} changed papers...")

        # Build key to index mapping from old metadata
        old_papers = {}
        if self.metadata_file_path.exists():
            with open(self.metadata_file_path) as f:
                old_metadata = json.load(f)
                for i, paper in enumerate(old_metadata.get("papers", [])):
                    old_papers[paper["zotero_key"]] = i

        # Collect existing embeddings for unchanged papers
        existing_embeddings = {}
        if self.index_file_path.exists() and old_papers:
            try:
                # Load existing index
                index = faiss.read_index(str(self.index_file_path))
                # Extract embeddings for unchanged papers
                for paper in papers:
                    key = paper["zotero_key"]
                    if key not in changed_keys and key in old_papers:
                        old_idx = old_papers[key]
                        if old_idx < index.ntotal:
                            existing_embeddings[key] = index.reconstruct(old_idx)
            except Exception as e:
                print(f"Could not reuse existing embeddings: {e}")

        # Build new embeddings list in correct order
        all_embeddings = []
        papers_to_embed = []
        texts_to_embed = []

        for paper in papers:
            key = paper["zotero_key"]
            if key in existing_embeddings:
                # Reuse existing embedding
                all_embeddings.append(existing_embeddings[key])
            else:
                # Need new embedding
                title = paper.get("title", "").strip()
                abstract = paper.get("abstract", "").strip()
                embedding_text = f"{title} [SEP] {abstract}" if abstract else title
                texts_to_embed.append(embedding_text)
                papers_to_embed.append(len(all_embeddings))
                all_embeddings.append(None)  # Placeholder

        # Generate new embeddings
        if texts_to_embed:
            new_embeddings = self.generate_embeddings(texts_to_embed)
            # Replace placeholders with actual embeddings
            for i, embedding in zip(papers_to_embed, new_embeddings, strict=False):
                all_embeddings[i] = embedding

        # Create new index
        all_embeddings_array = np.array(all_embeddings, dtype="float32")
        new_index = faiss.IndexFlatL2(all_embeddings_array.shape[1])
        new_index.add(all_embeddings_array)

        # Save updated index
        faiss.write_index(new_index, str(self.index_file_path))
        print(f"Index updated with {new_index.ntotal} papers")

    def rebuild_simple_index(self, papers: list[dict[str, Any]]) -> None:
        """Rebuild FAISS index from paper abstracts.

        Args:
            papers: List of paper metadata dictionaries
        """
        import faiss

        print("Rebuilding search index from scratch...")

        # Create and save index
        index = self.create_index(papers)
        faiss.write_index(index, str(self.index_file_path))

        if index.ntotal > 0:
            print(f"Index rebuilt with {index.ntotal} papers")
        else:
            print("Created empty index")
