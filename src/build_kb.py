#!/usr/bin/env python3
"""
Knowledge Base Builder for Research Assistant
Converts Zotero library to portable format with semantic search
"""

import contextlib
import json
import os
import re
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import click
import requests
from tqdm import tqdm


def detect_study_type(text: str) -> str:
    """Detect study type from abstract and title text."""
    text_lower = text.lower()

    # Check in order of evidence hierarchy
    if "systematic review" in text_lower or "meta-analysis" in text_lower or "meta analysis" in text_lower:
        return "systematic_review"
    if any(
        term in text_lower
        for term in [
            "randomized",
            "randomised",
            "randomized controlled",
            "randomised controlled",
            "rct",
        ]
    ):
        return "rct"
    if "cohort" in text_lower:
        return "cohort"
    if "case-control" in text_lower or "case control" in text_lower:
        return "case_control"
    if "cross-sectional" in text_lower or "cross sectional" in text_lower:
        return "cross_sectional"
    if "case report" in text_lower or "case series" in text_lower:
        return "case_report"
    return "study"  # Generic fallback


def extract_rct_sample_size(text: str, study_type: str) -> int | None:
    """Extract sample size for RCTs from abstract text."""
    if study_type != "rct":
        return None

    text_lower = text.lower()

    # RCT-specific patterns for sample size extraction
    patterns = [
        r"randomized\s+(\d+)\s+patients?",
        r"randomised\s+(\d+)\s+patients?",
        r"(\d+)\s+patients?\s+were\s+randomized",
        r"(\d+)\s+patients?\s+were\s+randomised",
        r"randomized\s+n\s*=\s*(\d+)",
        r"randomised\s+n\s*=\s*(\d+)",
        r"n\s*=\s*(\d+)\s*were\s+randomized",
        r"n\s*=\s*(\d+)\s*were\s+randomised",
        r"enrolled\s+and\s+randomized\s+(\d+)",
        r"enrolled\s+and\s+randomised\s+(\d+)",
        r"(\d+)\s+participants?\s+were\s+randomly",
        r"(\d+)\s+subjects?\s+were\s+randomized",
        r"(\d+)\s+subjects?\s+were\s+randomised",
        r"enrolling\s+(\d+)\s+patients?",  # For "enrolling 324 patients"
        r"trial\s+with\s+(\d+)\s+patients?",  # For "trial with 150 patients"
    ]

    for pattern in patterns:
        match = re.search(pattern, text_lower)
        if match:
            n = int(match.group(1))
            # Sanity check for reasonable sample sizes
            if 10 <= n <= 100000:
                return n

    return None


class KnowledgeBaseBuilder:
    def __init__(self, knowledge_base_path: str = "kb_data", zotero_data_dir: str | None = None):
        self.knowledge_base_path = Path(knowledge_base_path)
        self.papers_path = self.knowledge_base_path / "papers"
        self.index_file_path = self.knowledge_base_path / "index.faiss"
        self.metadata_file_path = self.knowledge_base_path / "metadata.json"
        self.cache_file_path = self.knowledge_base_path / ".pdf_text_cache.json"

        self.knowledge_base_path.mkdir(exist_ok=True)
        self.papers_path.mkdir(exist_ok=True)

        # Set Zotero data directory (default to ~/Zotero)
        if zotero_data_dir:
            self.zotero_data_dir = Path(zotero_data_dir)
        else:
            self.zotero_data_dir = Path.home() / "Zotero"

        self.zotero_db_path = self.zotero_data_dir / "zotero.sqlite"
        self.zotero_storage_path = self.zotero_data_dir / "storage"

        self._embedding_model: Any = None
        self.cache: dict[str, dict[str, Any]] | None = None  # Lazy load when needed
        self.embedding_cache: dict[str, Any] | None = None  # Lazy load when needed

    @property
    def embedding_model(self) -> Any:
        """Lazy load the SPECTER2 embedding model with fallback to SPECTER."""
        if self._embedding_model is None:
            import torch
            from sentence_transformers import SentenceTransformer

            # Detect and use GPU if available for faster encoding
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            if self.device == "cuda":
                print("GPU detected! Using CUDA for faster embeddings")
            else:
                print("No GPU detected, using CPU")

            # Load SPECTER model - proven and stable for scientific papers
            # Using the sentence-transformers version which works reliably
            print("Loading SPECTER embedding model for scientific papers...")
            self._embedding_model = SentenceTransformer(
                "sentence-transformers/allenai-specter", device=self.device
            )
            self.model_version = "SPECTER"
            print(f"SPECTER model loaded successfully on {self.device}")

        return self._embedding_model

    def load_cache(self) -> dict[str, dict[str, Any]]:
        """Load the PDF text cache from disk."""
        if self.cache is not None:
            return self.cache

        if self.cache_file_path.exists():
            try:
                with open(self.cache_file_path, encoding="utf-8") as f:
                    self.cache = json.load(f)
                    print(f"Loaded cache with {len(self.cache)} entries")
                    return self.cache
            except (OSError, json.JSONDecodeError) as e:
                print(f"Warning: Could not load cache: {e}")

        self.cache = {}
        return self.cache

    def save_cache(self) -> None:
        """Save the PDF text cache to disk."""
        if self.cache is None:
            return
        try:
            with open(self.cache_file_path, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, indent=2, ensure_ascii=False)
                print(f"Saved cache with {len(self.cache)} entries")
        except (OSError, TypeError) as e:
            print(f"Warning: Could not save cache: {e}")

    def clear_cache(self) -> None:
        """Clear the PDF text cache."""
        self.cache = {}
        if self.cache_file_path.exists():
            self.cache_file_path.unlink()
            print("Cleared PDF text cache")

    def load_embedding_cache(self) -> dict[str, Any]:
        """Load the embedding cache from disk using JSON format."""
        if self.embedding_cache is not None:
            return self.embedding_cache

        # Use JSON-based cache format only
        json_cache_path = self.knowledge_base_path / ".embedding_cache.json"
        npy_cache_path = self.knowledge_base_path / ".embedding_data.npy"

        if json_cache_path.exists() and npy_cache_path.exists():
            try:
                import numpy as np

                # Load metadata from JSON
                with open(json_cache_path) as f:
                    cache_meta = json.load(f)

                # Load embeddings from NPY (safe, no pickle)
                embeddings = np.load(npy_cache_path, allow_pickle=False)

                # Build hash index for O(1) lookups
                hash_to_idx = {h: i for i, h in enumerate(cache_meta["hashes"])}

                self.embedding_cache = {
                    "embeddings": embeddings,
                    "hashes": cache_meta["hashes"],
                    "hash_index": hash_to_idx,  # O(1) lookup dict
                    "model_name": cache_meta["model_name"],
                }
                print(f"Loaded embedding cache with {len(cache_meta['hashes'])} entries")
                return self.embedding_cache
            except (OSError, ValueError, json.JSONDecodeError) as e:
                print(f"Warning: Could not load embedding cache (won't affect results, just speed): {e}")

        self.embedding_cache = {
            "embeddings": None,
            "hashes": [],
            "hash_index": {},
            "model_name": "allenai/specter2",
        }
        return self.embedding_cache

    def save_embedding_cache(self, embeddings: Any, hashes: list[str]) -> None:
        """Save embeddings to cache using safe formats."""
        try:
            from datetime import UTC, datetime

            import numpy as np

            model_name = getattr(self, "model_version", "SPECTER2")

            # Save metadata to JSON
            json_cache_path = self.knowledge_base_path / ".embedding_cache.json"
            cache_meta = {
                "hashes": hashes,
                "model_name": model_name,
                "created_at": datetime.now(UTC).isoformat(),
            }
            with open(json_cache_path, "w") as f:
                json.dump(cache_meta, f, indent=2)

            # Save embeddings to NPY (without pickle)
            npy_cache_path = self.knowledge_base_path / ".embedding_data.npy"
            np.save(npy_cache_path, embeddings, allow_pickle=False)

            print(f"Saved {model_name} embedding cache with {len(hashes)} entries")
        except (OSError, TypeError) as e:
            print(f"Warning: Could not save embedding cache (won't affect results, just speed): {e}")

    def clear_embedding_cache(self) -> None:
        """Clear the embedding cache."""
        self.embedding_cache = None

        # Clear JSON/NPY cache files
        json_cache_path = self.knowledge_base_path / ".embedding_cache.json"
        npy_cache_path = self.knowledge_base_path / ".embedding_data.npy"

        if json_cache_path.exists():
            json_cache_path.unlink()
        if npy_cache_path.exists():
            npy_cache_path.unlink()
        print("Cleared embedding cache")

    def get_embedding_hash(self, text: str) -> str:
        """Generate hash for embedding cache key."""
        import hashlib

        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def get_paper_fingerprint(self, paper: dict) -> str:
        """Create content-based fingerprint for paper to detect changes."""
        import hashlib

        # Include all content that affects embeddings
        content_parts = [
            paper.get("title", ""),
            paper.get("abstract", ""),
            paper.get("full_text", "")[:1000] if paper.get("full_text") else "",  # First 1000 chars
            str(paper.get("year", "")),
            ",".join(paper.get("authors", [])),
        ]

        content = "|".join(content_parts)
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def should_recompute_embedding(self, paper: dict, cached_fingerprints: dict) -> bool:
        """Check if paper content has changed and needs new embedding."""
        paper_key = paper.get("zotero_key", "") or paper.get("doi", "") or paper.get("title", "")

        if not paper_key:
            return True  # No key to check, recompute

        current_fingerprint = self.get_paper_fingerprint(paper)
        cached_fingerprint = cached_fingerprints.get(paper_key)

        return current_fingerprint != cached_fingerprint

    def get_optimal_batch_size(self) -> int:
        """Determine optimal batch size based on available memory."""
        try:
            import psutil

            available_gb = psutil.virtual_memory().available / (1024**3)

            # Check if using GPU
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
                except Exception:  # noqa: S110
                    pass

            # CPU memory-based batch sizing
            if available_gb > 16:
                batch_size = 256
            elif available_gb > 8:
                batch_size = 128
            else:
                batch_size = 64

            print(f"Using batch size {batch_size} based on {available_gb:.1f}GB available RAM")
            return batch_size

        except ImportError:
            # If psutil not available, use conservative default
            return 128  # Better than original 64

    def clean_knowledge_base(self) -> None:
        """Clean up existing knowledge base files before rebuilding."""
        # Remove old paper files
        if self.papers_path.exists():
            paper_files = list(self.papers_path.glob("paper_*.md"))
            if paper_files:
                for paper_file in paper_files:
                    paper_file.unlink()
                print(f"Cleaned {len(paper_files)} old paper files")

        # Remove old index and metadata
        if self.index_file_path.exists():
            self.index_file_path.unlink()
            print("Removed old FAISS index")

        if self.metadata_file_path.exists():
            self.metadata_file_path.unlink()
            print("Removed old metadata file")

    def get_pdf_paths_from_sqlite(self) -> dict[str, Path]:
        """Get mapping of paper keys to PDF file paths from Zotero SQLite database."""
        if not self.zotero_db_path.exists():
            print(f"Warning: Zotero database not found at {self.zotero_db_path}")
            return {}

        pdf_map = {}

        try:
            # Connect to SQLite database with immutable mode to work while Zotero is running
            conn = sqlite3.connect(f"file:{self.zotero_db_path}?immutable=1", uri=True)
            cursor = conn.cursor()

            # Query to get parent item keys and their PDF attachment keys
            query = """
            SELECT
                parent.key as paper_key,
                child.key as attachment_key
            FROM itemAttachments ia
            JOIN items parent ON ia.parentItemID = parent.itemID
            JOIN items child ON ia.itemID = child.itemID
            WHERE ia.contentType = 'application/pdf'
            """

            cursor.execute(query)

            for paper_key, attachment_key in cursor.fetchall():
                # Build path to PDF in storage folder
                pdf_dir = self.zotero_storage_path / attachment_key

                if pdf_dir.exists():
                    # Find PDF file in the directory
                    pdf_files = list(pdf_dir.glob("*.pdf"))
                    if pdf_files:
                        pdf_map[paper_key] = pdf_files[0]

            conn.close()
            print(f"Found {len(pdf_map)} PDF attachments mapped to papers")

        except sqlite3.Error as e:
            print(f"Warning: Could not read Zotero database: {e}")
        except Exception as e:
            print(f"Warning: Error accessing PDF paths: {e}")

        return pdf_map

    def extract_pdf_text(
        self, pdf_path: str | Path, paper_key: str | None = None, use_cache: bool = True
    ) -> str | None:
        """Extract text from PDF using PyMuPDF with caching support."""
        import fitz

        pdf_path = Path(pdf_path)

        # Check cache if enabled and key provided
        if use_cache and paper_key:
            if self.cache is None:
                self.load_cache()
            if self.cache is None:
                raise RuntimeError("Failed to load cache")
            if paper_key in self.cache:
                cache_entry = self.cache[paper_key]
                try:
                    # Check if file metadata matches
                    stat = os.stat(pdf_path)
                    if (
                        cache_entry.get("file_size") == stat.st_size
                        and cache_entry.get("file_mtime") == stat.st_mtime
                    ):
                        return cache_entry.get("text")
                except (OSError, AttributeError):
                    pass  # If stat fails, just extract fresh

        # Extract text from PDF
        try:
            pdf = fitz.open(str(pdf_path))
            text = ""
            for page in pdf:
                text += page.get_text() + "\n"
            pdf.close()
            stripped_text = text.strip() if text else None

            # Update cache if enabled and key provided
            if use_cache and paper_key and stripped_text:
                if self.cache is None:
                    self.load_cache()
                stat = os.stat(pdf_path)
                if self.cache is None:
                    raise RuntimeError("Failed to load cache")
                self.cache[paper_key] = {
                    "text": stripped_text,
                    "file_size": stat.st_size,
                    "file_mtime": stat.st_mtime,
                    "cached_at": datetime.now(UTC).isoformat(),
                }

            return stripped_text
        except Exception as e:
            print(f"Error extracting PDF {pdf_path}: {e}")
            return None

    def extract_sections(self, text: str) -> dict:
        """Extract common academic paper sections from full text."""
        import re

        sections = {
            "abstract": "",
            "introduction": "",
            "methods": "",
            "results": "",
            "discussion": "",
            "conclusion": "",
            "references": "",
            "supplementary": "",
        }

        if not text:
            return sections

        # First check for markdown headers (## Section)
        has_markdown_headers = bool(re.search(r"^## \w+", text, re.MULTILINE))

        if has_markdown_headers:
            # Parse markdown structure
            current_section = None
            section_content: list[str] = []

            for line in text.split("\n"):
                if line.startswith("## "):
                    # Save previous section
                    if current_section and section_content:
                        sections[current_section] = "\n".join(section_content).strip()[:5000]

                    # Identify new section
                    header = line[3:].strip().lower()
                    if "abstract" in header:
                        current_section = "abstract"
                    elif "introduction" in header or "background" in header:
                        current_section = "introduction"
                    elif "method" in header:
                        current_section = "methods"
                    elif "result" in header or "finding" in header:
                        current_section = "results"
                    elif "discussion" in header:
                        current_section = "discussion"
                    elif "conclusion" in header:
                        current_section = "conclusion"
                    elif "reference" in header or "bibliography" in header:
                        current_section = "references"
                    elif "supplement" in header or "appendix" in header:
                        current_section = "supplementary"
                    elif "full text" in header:
                        # For demo papers that have "## Full Text" section
                        current_section = "introduction"  # Will parse subsections below
                    else:
                        current_section = None
                    section_content = []
                elif current_section:
                    section_content.append(line)

            # Save last section
            if current_section and section_content:
                sections[current_section] = "\n".join(section_content).strip()[:5000]

        # Look for inline section headers (Introduction\n, Methods\n, etc.)
        if has_markdown_headers and "## Full Text" in text:
            # Parse the Full Text section for inline headers
            full_text_match = re.search(r"## Full Text\n(.*)", text, re.DOTALL)
            if full_text_match:
                full_text = full_text_match.group(1)

                # Common inline section patterns
                inline_patterns = [
                    (r"^Introduction\s*$", "introduction"),
                    (r"^Methods?\s*$", "methods"),
                    (r"^Results?\s*$", "results"),
                    (r"^Discussion\s*$", "discussion"),
                    (r"^Conclusions?\s*$", "conclusion"),
                    (r"^References?\s*$", "references"),
                ]

                lines = full_text.split("\n")
                current_section = None
                section_content = []

                for line in lines:
                    found_section = None
                    for pattern, section_name in inline_patterns:
                        if re.match(pattern, line.strip(), re.IGNORECASE):
                            found_section = section_name
                            break

                    if found_section:
                        # Save previous section
                        if (
                            current_section and section_content and not sections[current_section]
                        ):  # Don't overwrite
                            sections[current_section] = "\n".join(section_content).strip()[:5000]
                        current_section = found_section
                        section_content = []
                    elif current_section:
                        section_content.append(line)

                # Save last section
                if current_section and section_content and not sections[current_section]:
                    sections[current_section] = "\n".join(section_content).strip()[:5000]

        # Fallback: use regex patterns for general text
        if not any(sections.values()):
            section_patterns = {
                "abstract": r"(?i)(?:abstract|summary)\s*[\n:]",
                "introduction": r"(?i)(?:introduction|background)\s*[\n:]",
                "methods": r"(?i)(?:methods?|methodology)\s*[\n:]",
                "results": r"(?i)(?:results?|findings?)\s*[\n:]",
                "discussion": r"(?i)(?:discussion)\s*[\n:]",
                "conclusion": r"(?i)(?:conclusions?)\s*[\n:]",
                "references": r"(?i)(?:references?|bibliography)\s*[\n:]",
            }

            for section_name, pattern in section_patterns.items():
                match = re.search(pattern, text)
                if match:
                    start = match.end()
                    # Find next section or end of text
                    next_match = None
                    for other_pattern in section_patterns.values():
                        next_m = re.search(other_pattern, text[start:])
                        if next_m and (next_match is None or next_m.start() < next_match):
                            next_match = next_m.start()

                    if next_match:
                        sections[section_name] = text[start : start + next_match].strip()[:5000]
                    else:
                        sections[section_name] = text[start : start + 5000].strip()

        # If still no sections found, use heuristics
        if not any(sections.values()) and text:
            sections["abstract"] = text[:1000].strip()
            if len(text) > 2000:
                sections["conclusion"] = text[-1000:].strip()

        return sections

    def format_paper_as_markdown(self, paper_data: dict) -> str:
        """Format paper data as markdown."""
        markdown_content = f"# {paper_data['title']}\n\n"

        if paper_data.get("authors"):
            markdown_content += f"**Authors:** {', '.join(paper_data['authors'])}  \n"
        markdown_content += f"**Year:** {paper_data.get('year', 'Unknown')}  \n"

        if paper_data.get("journal"):
            markdown_content += f"**Journal:** {paper_data['journal']}  \n"
        if paper_data.get("volume"):
            markdown_content += f"**Volume:** {paper_data['volume']}  \n"
        if paper_data.get("issue"):
            markdown_content += f"**Issue:** {paper_data['issue']}  \n"
        if paper_data.get("pages"):
            markdown_content += f"**Pages:** {paper_data['pages']}  \n"
        if paper_data.get("doi"):
            markdown_content += f"**DOI:** {paper_data['doi']}  \n"

        markdown_content += "\n## Abstract\n"
        markdown_content += paper_data.get("abstract", "No abstract available.") + "\n\n"

        if paper_data.get("full_text"):
            markdown_content += "## Full Text\n"
            markdown_content += paper_data["full_text"] + "\n"

        return str(markdown_content)

    def fetch_zotero_metadata(self, api_url: str | None = None) -> dict[str, Any]:
        """Quickly fetch metadata about Zotero library for analysis."""
        base_url = api_url or "http://localhost:23119/api"

        # Test connection to local Zotero
        try:
            response = requests.get(f"{base_url}/", timeout=5)
            if response.status_code != 200:
                raise ConnectionError(
                    "Zotero local API not accessible. Ensure Zotero is running and 'Allow other applications' is enabled in Advanced settings."
                )
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Cannot connect to Zotero local API: {e}") from e

        # Get just keys and basic info for analysis
        all_items = []
        start = 0
        limit = 100

        while True:
            try:
                # Fetch only essential fields for speed
                response = requests.get(
                    f"{base_url}/users/0/items",
                    params={
                        "start": str(start),
                        "limit": str(limit),
                        "fields": "key,itemType,dateModified,title",
                    },
                    timeout=10,
                )
                response.raise_for_status()
                batch = response.json()

                if not batch:
                    break

                all_items.extend(batch)
                start += len(batch)

            except requests.exceptions.RequestException as e:
                raise RuntimeError(f"Cannot connect to Zotero. Please start Zotero and try again: {e}") from e

        # Extract paper keys and count
        paper_keys = set()
        paper_count = 0

        for item in all_items:
            if item.get("data", {}).get("itemType") in [
                "journalArticle",
                "conferencePaper",
                "preprint",
                "book",
                "thesis",
                "report",
            ]:
                paper_keys.add(item.get("key", ""))
                paper_count += 1

        return {
            "total_items": len(all_items),
            "paper_count": paper_count,
            "paper_keys": paper_keys,
            "api_url": base_url,
        }

    def analyze_knowledge_base_state(self, zotero_metadata: dict[str, Any]) -> dict[str, Any]:
        """Analyze current knowledge base and compare with Zotero library."""
        analysis = {
            "kb_exists": False,
            "kb_paper_count": 0,
            "new_papers": 0,
            "deleted_papers": 0,
            "cache_exists": self.cache_file_path.exists(),
            "cache_size_mb": 0,
            "embedding_cache_exists": (self.knowledge_base_path / ".embedding_cache.json").exists(),
            "estimated_time_seconds": 0,
            "estimated_time_str": "",
        }

        # Check existing knowledge base
        if self.metadata_file_path.exists():
            try:
                with open(self.metadata_file_path, encoding="utf-8") as f:
                    kb_metadata = json.load(f)
                    analysis["kb_exists"] = True
                    analysis["kb_paper_count"] = kb_metadata.get("total_papers", 0)

                    # Get existing paper keys
                    existing_keys = set()
                    for paper in kb_metadata.get("papers", []):
                        # Extract original zotero key from paper id or metadata
                        # We'll need to store this in metadata going forward
                        existing_keys.add(paper.get("zotero_key", ""))

                    # Calculate differences
                    zotero_keys = zotero_metadata["paper_keys"]
                    analysis["new_papers"] = len(zotero_keys - existing_keys)
                    analysis["deleted_papers"] = len(existing_keys - zotero_keys)
            except (json.JSONDecodeError, KeyError):
                pass

        # Check cache sizes
        if analysis["cache_exists"]:
            try:
                stat = self.cache_file_path.stat()
                analysis["cache_size_mb"] = stat.st_size / (1024 * 1024)
            except (OSError, AttributeError):
                pass

        # Estimate processing time
        paper_count = int(zotero_metadata["paper_count"])
        new_papers_val = analysis.get("new_papers", 0) if analysis["kb_exists"] else paper_count
        new_papers = int(cast(int, new_papers_val)) if new_papers_val is not None else 0

        if analysis["cache_exists"] and analysis["embedding_cache_exists"]:
            # With caches: ~0.5 sec per new paper, 0.1 sec per cached paper
            cached_papers = paper_count - new_papers
            time_estimate = float((new_papers * 0.5) + (cached_papers * 0.1) + 10)  # +10 for overhead
        else:
            # Without caches: ~2 sec per paper + model loading
            time_estimate = (paper_count * 2) + 30  # +30 for model loading

        analysis["estimated_time_seconds"] = int(time_estimate)

        # Format time string
        if time_estimate < 60:
            analysis["estimated_time_str"] = f"{int(time_estimate)} seconds"
        elif time_estimate < 300:
            analysis["estimated_time_str"] = f"{int(time_estimate / 60)} minutes"
        else:
            analysis["estimated_time_str"] = f"{time_estimate / 60:.1f} minutes"

        return analysis

    def process_zotero_local_library(self, api_url: str | None = None) -> list[dict]:
        """Extract papers from Zotero local library using HTTP API with proper pagination."""
        base_url = api_url or "http://localhost:23119/api"

        # Test connection to local Zotero
        try:
            response = requests.get(f"{base_url}/", timeout=5)
            if response.status_code != 200:
                raise ConnectionError(
                    "Zotero local API not accessible. Ensure Zotero is running and 'Allow other applications' is enabled in Advanced settings."
                )
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Cannot connect to Zotero local API: {e}") from e

        # Get all items from library with pagination
        all_items = []
        start = 0
        limit = 100

        print("Fetching items from Zotero API...")
        while True:
            try:
                response = requests.get(
                    f"{base_url}/users/0/items",
                    params={"start": start, "limit": limit},
                    timeout=30,
                )
                response.raise_for_status()
                batch = response.json()

                if not batch:
                    break

                all_items.extend(batch)
                start += len(batch)
                print(f"  Fetched {len(all_items)} items...", end="\r")

            except requests.exceptions.RequestException as e:
                raise RuntimeError(f"Cannot connect to Zotero. Please start Zotero and try again: {e}") from e

        print(f"  Fetched {len(all_items)} total items from Zotero")

        papers = []

        # Process items to extract paper metadata
        for item in tqdm(all_items, desc="Filtering for research papers"):
            if item.get("data", {}).get("itemType") not in [
                "journalArticle",
                "conferencePaper",
                "preprint",
                "book",
                "thesis",
                "report",
            ]:
                continue

            paper_data = {
                "title": item["data"].get("title", ""),
                "authors": [],
                "year": None,
                "journal": item["data"].get("publicationTitle", ""),
                "volume": item["data"].get("volume", ""),
                "issue": item["data"].get("issue", ""),
                "pages": item["data"].get("pages", ""),
                "doi": item["data"].get("DOI", ""),
                "abstract": item["data"].get("abstractNote", ""),
                "zotero_key": item.get("key", ""),
            }

            for creator in item["data"].get("creators", []):
                if creator.get("lastName"):
                    name = f"{creator.get('firstName', '')} {creator['lastName']}".strip()
                    paper_data["authors"].append(name)

            if item["data"].get("date"):
                with contextlib.suppress(ValueError, IndexError, KeyError):
                    paper_data["year"] = int(item["data"]["date"][:4])

            papers.append(paper_data)

        print(f"  Found {len(papers)} research papers (from {len(all_items)} total items)")
        return papers

    def augment_papers_with_pdfs(self, papers: list[dict], use_cache: bool = True) -> None:
        """Add full text from PDFs using SQLite database paths with caching."""
        # Ensure cache is loaded
        if use_cache and self.cache is None:
            self.load_cache()

        pdf_map = self.get_pdf_paths_from_sqlite()

        if not pdf_map:
            print("No PDF paths found in SQLite database")
            return

        papers_with_pdfs_available = sum(1 for p in papers if p["zotero_key"] in pdf_map)
        print(f"Extracting text from PDFs ({papers_with_pdfs_available} papers have PDFs)...")
        papers_with_pdfs = 0
        cache_hits = 0

        for paper in tqdm(papers, desc="Extracting PDF text"):
            if paper["zotero_key"] in pdf_map:
                pdf_path = pdf_map[paper["zotero_key"]]

                # Check if we're using cache and if this is a valid cache hit
                was_cached = False
                if use_cache:
                    if self.cache is None:
                        self.load_cache()
                    if self.cache is None:
                        raise RuntimeError("Failed to load cache")
                    if paper["zotero_key"] in self.cache:
                        cache_entry = self.cache[paper["zotero_key"]]
                        try:
                            stat = os.stat(pdf_path)
                            if (
                                cache_entry.get("file_size") == stat.st_size
                                and cache_entry.get("file_mtime") == stat.st_mtime
                            ):
                                was_cached = True
                        except (OSError, AttributeError, KeyError):
                            pass

                full_text = self.extract_pdf_text(pdf_path, paper["zotero_key"], use_cache)
                if full_text:
                    paper["full_text"] = full_text
                    papers_with_pdfs += 1
                    if was_cached:
                        cache_hits += 1

        print(f"Successfully extracted text from {papers_with_pdfs}/{len(papers)} papers")
        if use_cache and cache_hits > 0:
            print(
                f"  Using cache: {cache_hits}/{papers_with_pdfs} PDFs ({cache_hits * 100 // papers_with_pdfs}%)"
            )

        # Save cache after extraction
        if use_cache:
            self.save_cache()

    def update_incremental(self, api_url: str | None = None) -> int:
        """Add only new papers since last build - much faster than full rebuild."""
        if not self.metadata_file_path.exists():
            print("❌ No existing knowledge base found. Run full build first.")
            return 0

        # Load existing metadata
        with open(self.metadata_file_path) as f:
            existing_metadata = json.load(f)

        last_updated = existing_metadata.get("last_updated", "")
        existing_keys = {p.get("zotero_key") for p in existing_metadata.get("papers", [])}

        print(f"🔍 Checking for new papers since {last_updated[:19]}...")

        # Fetch current papers from Zotero
        all_papers = self.process_zotero_local_library(api_url)

        # Find new papers
        new_papers = []
        for paper in all_papers:
            if paper.get("zotero_key") not in existing_keys:
                new_papers.append(paper)

        if not new_papers:
            print("✅ No new papers found. Knowledge base is up to date!")
            return 0

        print(f"📚 Found {len(new_papers)} new papers to add")

        # Add PDFs to new papers
        self.augment_papers_with_pdfs(new_papers, use_cache=True)

        # Load existing FAISS index
        import faiss
        import numpy as np

        index = faiss.read_index(str(self.index_file_path))

        # Generate embeddings for new papers only
        print(f"Generating embeddings for {len(new_papers)} new papers...")
        new_abstracts = []
        for paper in new_papers:
            title = paper.get("title", "").strip()
            abstract = paper.get("abstract", "").strip()

            embedding_text = f"{title} [SEP] {abstract}" if abstract else title

            new_abstracts.append(embedding_text)

        # Compute embeddings
        batch_size = self.get_optimal_batch_size()
        new_embeddings = self.embedding_model.encode(
            new_abstracts, show_progress_bar=True, batch_size=batch_size
        )

        # Add to FAISS index
        index.add(new_embeddings.astype("float32"))

        # Update metadata
        start_id = len(existing_metadata["papers"]) + 1
        for i, paper in enumerate(new_papers):
            paper_id = f"{start_id + i:04d}"

            # Detect study type and sample size
            text_for_classification = f"{paper.get('title', '')} {paper.get('abstract', '')}"
            study_type = detect_study_type(text_for_classification)
            sample_size = extract_rct_sample_size(text_for_classification, study_type)

            paper_metadata = {
                "id": paper_id,
                "doi": paper.get("doi", ""),
                "title": paper.get("title", ""),
                "authors": paper.get("authors", []),
                "year": paper.get("year", None),
                "journal": paper.get("journal", ""),
                "volume": paper.get("volume", ""),
                "issue": paper.get("issue", ""),
                "pages": paper.get("pages", ""),
                "abstract": paper.get("abstract", ""),
                "study_type": study_type,
                "sample_size": sample_size,
                "has_full_text": bool(paper.get("full_text")),
                "filename": f"paper_{paper_id}.md",
                "embedding_index": len(existing_metadata["papers"]) + i,
                "zotero_key": paper.get("zotero_key", ""),
            }

            existing_metadata["papers"].append(paper_metadata)

            # Save paper markdown file
            md_content = self.format_paper_as_markdown(paper)
            markdown_file_path = self.papers_path / f"paper_{paper_id}.md"
            with open(markdown_file_path, "w", encoding="utf-8") as f:
                f.write(md_content)

        # Update metadata counts and timestamp
        existing_metadata["total_papers"] = len(existing_metadata["papers"])
        existing_metadata["last_updated"] = datetime.now(UTC).isoformat()

        # Save updated index and metadata
        faiss.write_index(index, str(self.index_file_path))
        with open(self.metadata_file_path, "w", encoding="utf-8") as f:
            json.dump(existing_metadata, f, indent=2, ensure_ascii=False)

        # Update embedding cache with new embeddings
        if new_embeddings.shape[0] > 0:
            cache = self.load_embedding_cache()
            if cache["embeddings"] is not None:
                # Append new embeddings to existing ones
                combined = np.vstack([cache["embeddings"], new_embeddings])

                # Add new hashes
                new_hashes = []
                for abstract in new_abstracts:
                    new_hashes.append(self.get_embedding_hash(abstract))

                all_hashes = cache["hashes"] + new_hashes
                self.save_embedding_cache(combined, all_hashes)

        print(f"✅ Successfully added {len(new_papers)} new papers!")
        print(f"   Total papers: {existing_metadata['total_papers']}")
        print(f"   Index: {self.index_file_path}")

        return len(new_papers)

    def build_from_zotero_local(
        self,
        api_url: str | None = None,
        use_cache: bool = True,
        skip_prompt: bool = False,
        incremental: bool = False,
    ) -> None:
        """Build knowledge base from local Zotero library."""
        # Try incremental update first if requested
        if incremental and self.metadata_file_path.exists():
            try:
                new_count = self.update_incremental(api_url)
                if new_count > 0:
                    return  # Success!
                elif new_count == 0:
                    return  # Already up to date
            except Exception as e:
                print(f"⚠️  Incremental update failed: {e}")
                print("   Falling back to full rebuild...")

        print("Connecting to Zotero library...")

        # Step 0: Fetch metadata first for analysis
        try:
            print("Analyzing library...", end="", flush=True)
            zotero_metadata = self.fetch_zotero_metadata(api_url)
            kb_analysis = self.analyze_knowledge_base_state(zotero_metadata)
            print(" Done!")

        except (ConnectionError, RuntimeError) as e:
            print(f"\nError: {e}")
            print("\nCannot proceed without Zotero connection.")
            raise

        # Step 1: Show status and confirm action
        if not skip_prompt:
            if kb_analysis["kb_exists"]:
                # Existing knowledge base
                print(
                    f"📚 Zotero: {zotero_metadata['paper_count']} papers | Knowledge base: {kb_analysis['kb_paper_count']} papers"
                )

                if kb_analysis["new_papers"] > 0 or kb_analysis["deleted_papers"] > 0:
                    # Changes detected - show more concise summary
                    changes = []
                    if kb_analysis["new_papers"] > 0:
                        changes.append(f"+{kb_analysis['new_papers']} new")
                    if kb_analysis["deleted_papers"] > 0:
                        changes.append(f"-{kb_analysis['deleted_papers']} removed")

                    print(f"📝 Changes: {', '.join(changes)}")
                    print(f"⏱️  Time: ~{kb_analysis['estimated_time_str']}", end="")
                    if kb_analysis["cache_exists"]:
                        print(" (using cache)", end="")
                    print()

                    response = input("\nUpdate knowledge base? [Y/n]: ").strip().lower()
                    if response == "n":
                        print("Update cancelled.")
                        return

                    print("\nUpdating knowledge base...")
                    self.clean_knowledge_base()
                else:
                    # No changes
                    print("✅ Knowledge base is up to date!")
                    print("\nNo changes detected. Rebuild anyway?")
                    response = input("[y/N]: ").strip().lower()
                    if response != "y":
                        print("Build cancelled.")
                        return

                    print("\nRebuilding knowledge base...")
                    self.clean_knowledge_base()
            else:
                # New knowledge base
                print(f"📚 New knowledge base: {zotero_metadata['paper_count']} papers found")
                print(f"⏱️  Time: ~{kb_analysis['estimated_time_str']}", end="")
                if kb_analysis["cache_exists"]:
                    print(f" (cache: {kb_analysis['cache_size_mb']:.1f} MB)", end="")
                print()

                response = input("\nBuild knowledge base? [Y/n]: ").strip().lower()
                if response == "n":
                    print("Build cancelled.")
                    return

                print("\nBuilding new knowledge base...")
        else:
            # When using --clear-cache flag, skip all prompts
            print(f"\n📚 Full rebuild: {zotero_metadata['paper_count']} papers (--clear-cache)")
            print(f"⏱️  Time: ~{(zotero_metadata['paper_count'] * 2 + 30) // 60} minutes (no cache)")
            print("\nClearing caches and rebuilding...")
            self.clean_knowledge_base()

        # Step 1: Get metadata from API
        papers = self.process_zotero_local_library(api_url)

        # Step 2: Add full text from PDFs via SQLite
        self.augment_papers_with_pdfs(papers, use_cache)

        # Step 3: Build the knowledge base
        self.build_from_papers(papers)

    def generate_missing_pdfs_report(self, papers: list[dict]) -> Path:
        """Generate markdown report of papers missing or with incomplete PDFs."""
        report_lines = []
        report_lines.append("# Missing/Incomplete PDFs Report\n")
        report_lines.append(f"**Generated:** {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}\n")

        # Categorize papers
        missing_pdfs = []
        small_pdfs = []  # Likely supplementary materials
        no_abstract = []

        for paper in papers:
            if "full_text" not in paper or not paper.get("full_text"):
                missing_pdfs.append(paper)
                if not paper.get("abstract"):
                    no_abstract.append(paper)
            elif len(paper.get("full_text", "")) < 5000:  # Less than 5KB of text
                small_pdfs.append(paper)

        # Summary statistics
        report_lines.append("## Summary Statistics\n")
        report_lines.append(f"- **Total papers:** {len(papers)}")
        report_lines.append(
            f"- **Papers with full text:** {len(papers) - len(missing_pdfs)} ({(len(papers) - len(missing_pdfs)) * 100 / len(papers):.1f}%)"
        )
        report_lines.append(
            f"- **Missing PDFs:** {len(missing_pdfs)} ({len(missing_pdfs) * 100 / len(papers):.1f}%)"
        )
        report_lines.append(f"- **Small PDFs (<5KB text):** {len(small_pdfs)}")
        report_lines.append(f"- **No abstract or full text:** {len(no_abstract)}\n")

        # List papers without PDFs
        if missing_pdfs:
            report_lines.append("## Papers Without Full Text\n")
            report_lines.append("These papers have no PDF attachments in Zotero or PDF extraction failed:\n")

            # Limit to first 100 to avoid huge reports
            for i, paper in enumerate(missing_pdfs[:100], 1):
                year = paper.get("year", "n.d.")
                authors = paper.get("authors", [])
                first_author = authors[0].split()[-1] if authors else "Unknown"
                journal = paper.get("journal", "Unknown journal")[:40]

                report_lines.append(
                    f"{i}. **[{year}]** {first_author} et al." if authors else f"{i}. **[{year}]**"
                )
                report_lines.append(f"   - *{paper.get('title', 'Untitled')[:100]}*")
                report_lines.append(f"   - {journal}")
                if paper.get("doi"):
                    report_lines.append(f"   - DOI: {paper['doi']}")
                report_lines.append("")

            if len(missing_pdfs) > 100:
                report_lines.append(f"\n*... and {len(missing_pdfs) - 100} more papers without full text*\n")

        # List papers with small PDFs (likely supplementary)
        if small_pdfs:
            report_lines.append("## Papers with Minimal Text (<5KB)\n")
            report_lines.append(
                "These PDFs likely contain only supplementary materials, not the full paper:\n"
            )

            for i, paper in enumerate(small_pdfs[:20], 1):
                text_len = len(paper.get("full_text", ""))
                year = paper.get("year", "n.d.")
                report_lines.append(f"{i}. [{year}] {paper.get('title', 'Untitled')[:80]}")
                report_lines.append(f"   - Text extracted: {text_len} characters")
                report_lines.append("")

            if len(small_pdfs) > 20:
                report_lines.append(f"\n*... and {len(small_pdfs) - 20} more papers with minimal text*\n")

        # Recommendations
        report_lines.append("## Recommendations\n")
        report_lines.append("To improve full-text coverage:\n")
        report_lines.append("1. **Add PDFs in Zotero**: Use Zotero's 'Find Available PDF' feature")
        report_lines.append(
            "2. **Check PDF quality**: Ensure PDFs contain full paper text, not just supplementary materials"
        )
        report_lines.append(
            "3. **Verify attachments**: Some papers may have PDFs attached to child items instead of the main entry"
        )
        report_lines.append(
            "4. **Re-run build**: After adding PDFs, run `python build_kb.py` (cache will speed up rebuild)"
        )

        # Save report
        report_path = self.knowledge_base_path / "missing_pdfs_report.md"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("\n".join(report_lines))

        return report_path

    def build_from_papers(self, papers: list[dict]) -> None:
        """Build knowledge base from a list of paper dictionaries."""
        # No backups - clean rebuild only

        # Detect and remove duplicates
        print("Checking for duplicate papers...")
        unique_papers = []
        seen_dois = set()
        seen_titles = set()
        duplicates_removed = 0

        for paper in papers:
            # Check for duplicate DOI
            doi = paper.get("doi", "").strip().lower()
            if doi and doi in seen_dois:
                duplicates_removed += 1
                continue

            # Check for duplicate title (normalized)
            title = paper.get("title", "").strip().lower()
            # Remove common variations in titles
            normalized_title = re.sub(r"[^\w\s]", "", title)  # Remove punctuation
            normalized_title = re.sub(r"\s+", " ", normalized_title)  # Normalize whitespace

            if normalized_title and normalized_title in seen_titles:
                duplicates_removed += 1
                continue

            # Add to unique papers
            unique_papers.append(paper)
            if doi:
                seen_dois.add(doi)
            if normalized_title:
                seen_titles.add(normalized_title)

        if duplicates_removed > 0:
            print(f"  Removed {duplicates_removed} duplicate papers")
            print(f"  Processing {len(unique_papers)} unique papers...")
        else:
            print("  No duplicates found")
            print(f"Processing {len(unique_papers)} papers...")

        papers = unique_papers  # Use deduplicated list

        metadata: dict[str, Any] = {
            "papers": [],
            "total_papers": len(papers),
            "last_updated": datetime.now(UTC).isoformat(),
            "embedding_model": "sentence-transformers/allenai-specter",
            "embedding_dimensions": 768,
            "model_version": "SPECTER",
        }

        abstracts = []
        sections_index = {}  # Store extracted sections for each paper

        for i, paper in enumerate(tqdm(papers, desc="Building knowledge base")):
            paper_id = f"{i + 1:04d}"

            # Combine title and abstract for classification
            text_for_classification = f"{paper.get('title', '')} {paper.get('abstract', '')}"
            study_type = detect_study_type(text_for_classification)
            sample_size = extract_rct_sample_size(text_for_classification, study_type)

            paper_metadata = {
                "id": paper_id,
                "doi": paper.get("doi", ""),
                "title": paper.get("title", ""),
                "authors": paper.get("authors", []),
                "year": paper.get("year", None),
                "journal": paper.get("journal", ""),
                "volume": paper.get("volume", ""),
                "issue": paper.get("issue", ""),
                "pages": paper.get("pages", ""),
                "abstract": paper.get("abstract", ""),
                "study_type": study_type,
                "sample_size": sample_size,
                "has_full_text": bool(paper.get("full_text")),
                "filename": f"paper_{paper_id}.md",
                "embedding_index": i,
                "zotero_key": paper.get("zotero_key", ""),  # Store for future comparisons
            }

            metadata["papers"].append(paper_metadata)

            # Extract sections if full text is available
            if paper.get("full_text"):
                extracted_sections = self.extract_sections(paper["full_text"])
                sections_index[paper_id] = extracted_sections
            else:
                # Use abstract as the only section if no full text
                sections_index[paper_id] = {
                    "abstract": paper.get("abstract", ""),
                    "introduction": "",
                    "methods": "",
                    "results": "",
                    "discussion": "",
                    "conclusion": "",
                    "references": "",
                    "supplementary": "",
                }

            md_content = self.format_paper_as_markdown(paper)
            markdown_file_path = self.papers_path / f"paper_{paper_id}.md"
            with open(markdown_file_path, "w", encoding="utf-8") as f:
                f.write(md_content)

            # Format for SciNCL: Title and Abstract with separator
            # SciNCL expects title and abstract concatenated with a separator
            title = paper.get("title", "").strip()
            abstract = paper.get("abstract", "").strip()

            # SciNCL handles papers with missing abstracts well
            embedding_text = f"{title} [SEP] {abstract}" if abstract else title

            abstracts.append(embedding_text)

        print(f"Building FAISS index for {len(abstracts)} papers...")
        import faiss
        import numpy as np

        if abstracts:
            # Load embedding cache
            cache = self.load_embedding_cache()
            cached_embeddings = []
            new_abstracts = []
            new_indices = []
            all_hashes = []

            # Load fingerprint cache for smart invalidation
            fingerprint_cache_path = self.knowledge_base_path / ".fingerprint_cache.json"
            if fingerprint_cache_path.exists():
                with open(fingerprint_cache_path) as f:
                    fingerprint_cache = json.load(f)
            else:
                fingerprint_cache = {}

            # Track new fingerprints
            new_fingerprints = {}

            # Check cache for each abstract with smart invalidation
            for i, (abstract_text, paper) in enumerate(zip(abstracts, papers, strict=False)):
                text_hash = self.get_embedding_hash(abstract_text)
                all_hashes.append(text_hash)

                # Check if content has changed using fingerprint
                paper_key = paper.get("zotero_key", "") or paper.get("doi", "") or paper.get("title", "")
                if paper_key:
                    new_fingerprints[paper_key] = self.get_paper_fingerprint(paper)

                # Smart cache check: valid if hash exists AND content unchanged
                content_changed = self.should_recompute_embedding(paper, fingerprint_cache)

                # Try to find in cache using O(1) dictionary lookup
                if (
                    not content_changed
                    and cache["embeddings"] is not None
                    and text_hash in cache.get("hash_index", {})
                ):
                    cache_idx = cache["hash_index"][text_hash]  # O(1) lookup!
                    cached_embeddings.append(cache["embeddings"][cache_idx])
                else:
                    new_abstracts.append(abstract_text)
                    new_indices.append(i)

            # Report cache usage
            cache_hits = len(cached_embeddings)
            if cache_hits > 0:
                print(
                    f"Using cached embeddings for {cache_hits}/{len(abstracts)} papers ({cache_hits * 100 // len(abstracts)}%)"
                )

            # Compute new embeddings if needed
            if new_abstracts:
                print(f"Computing embeddings for {len(new_abstracts)} new/modified papers...")
                # Use dynamic batch size based on available memory
                batch_size = self.get_optimal_batch_size()

                # Enhanced progress tracking for embedding generation
                print(f"  Processing in batches of {batch_size}...")
                total_batches = (len(new_abstracts) + batch_size - 1) // batch_size
                print(f"  Total batches to process: {total_batches}")

                new_embeddings = self.embedding_model.encode(
                    new_abstracts, show_progress_bar=True, batch_size=batch_size
                )
            else:
                new_embeddings = []

            # Combine cached and new embeddings in correct order
            all_embeddings = np.zeros((len(abstracts), 768), dtype="float32")

            # Place embeddings in correct positions
            cache_idx = 0
            new_idx = 0
            for i in range(len(abstracts)):
                if i in new_indices:
                    all_embeddings[i] = new_embeddings[new_idx]
                    new_idx += 1
                else:
                    all_embeddings[i] = cached_embeddings[cache_idx]
                    cache_idx += 1

            # Save cache
            print("Saving embedding cache...")
            self.save_embedding_cache(all_embeddings, all_hashes)

            # Save fingerprint cache for smart invalidation
            with open(fingerprint_cache_path, "w") as f:
                json.dump(new_fingerprints, f)

            # Build FAISS index
            print("Creating searchable index...")
            dimension = all_embeddings.shape[1]
            index = faiss.IndexFlatL2(dimension)
            index.add(all_embeddings.astype("float32"))
            print(f"  Index created with {len(all_embeddings)} vectors of dimension {dimension}")
        else:
            # Create empty index with default dimension
            dimension = 768  # SPECTER dimension
            index = faiss.IndexFlatL2(dimension)

        faiss.write_index(index, str(self.index_file_path))

        with open(self.metadata_file_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        # Save sections index for fast retrieval
        sections_index_path = self.knowledge_base_path / "sections_index.json"
        with open(sections_index_path, "w", encoding="utf-8") as f:
            json.dump(sections_index, f, indent=2, ensure_ascii=False)
        print(f"  - Sections index: {sections_index_path}")

        print("Knowledge base built successfully!")
        print(f"  - Papers: {len(papers)}")
        print(f"  - Index: {self.index_file_path}")
        print(f"  - Metadata: {self.metadata_file_path}")
        print(f"  - Papers directory: {self.papers_path}")

        # Check for missing PDFs and offer to generate report
        missing_count = sum(1 for p in papers if "full_text" not in p or not p.get("full_text"))
        if missing_count > 0:
            print(
                f"\n📊 Note: {missing_count} papers lack full text PDFs ({missing_count * 100 / len(papers):.1f}%)"
            )
            response = input("Generate detailed missing PDFs report? (y/N): ").strip().lower()
            if response == "y":
                print("Generating report...")
                report_path = self.generate_missing_pdfs_report(papers)
                print(f"✅ Report saved to: {report_path}")

    def build_demo_kb(self) -> None:
        """Build a demo knowledge base with sample papers."""
        # Clean up old knowledge base first (no prompt for demo)
        self.clean_knowledge_base()

        demo_papers = [
            {
                "title": "Digital Health Interventions for Depression, Anxiety, and Enhancement of Psychological Well-Being",
                "authors": ["John Smith", "Jane Doe", "Alice Johnson"],
                "year": 2023,
                "journal": "Nature Digital Medicine",
                "volume": "6",
                "issue": "3",
                "pages": "123-145",
                "doi": "10.1038/s41746-023-00789-9",
                "abstract": "Digital health interventions have shown promise in addressing mental health challenges. This systematic review examines the effectiveness of mobile apps, web-based platforms, and digital therapeutics for treating depression and anxiety disorders. We analyzed 127 randomized controlled trials involving over 50,000 participants. Results indicate moderate to large effect sizes for guided digital interventions compared to waitlist controls.",
                "full_text": "Introduction\n\nThe proliferation of digital technologies has created new opportunities for mental health interventions. Mobile health (mHealth) applications, web-based cognitive behavioral therapy (CBT), and digital therapeutics represent a rapidly growing field...\n\nMethods\n\nWe conducted a systematic search of PubMed, PsycINFO, and Cochrane databases for randomized controlled trials published between 2010 and 2023. Inclusion criteria required studies to evaluate digital interventions for depression or anxiety...\n\nResults\n\nOf 3,421 articles screened, 127 met inclusion criteria. Digital CBT showed the strongest evidence base with an average effect size of d=0.73 for depression and d=0.67 for anxiety. Smartphone-based interventions demonstrated moderate effects (d=0.45-0.52) with higher engagement rates than web-based platforms...\n\nDiscussion\n\nDigital health interventions offer scalable solutions for mental health treatment gaps. However, challenges remain regarding engagement, personalization, and integration with traditional care models...",
            },
            {
                "title": "Barriers to Digital Health Adoption in Elderly Populations: A Mixed-Methods Study",
                "authors": ["Michael Chen", "Sarah Williams", "Robert Brown"],
                "year": 2024,
                "journal": "Journal of Medical Internet Research",
                "volume": "26",
                "issue": "2",
                "pages": "e45678",
                "doi": "10.2196/45678",
                "abstract": "Understanding barriers to digital health adoption among elderly populations is crucial for equitable healthcare delivery. This mixed-methods study combines survey data from 2,500 adults aged 65+ with qualitative interviews from 150 participants. Key barriers identified include technological literacy (67%), privacy concerns (54%), lack of perceived benefit (43%), and physical/cognitive limitations (38%). Facilitators included family support, simplified interfaces, and integration with existing care.",
                "full_text": "Background\n\nThe digital divide in healthcare disproportionately affects elderly populations, potentially exacerbating health disparities. As healthcare systems increasingly adopt digital solutions, understanding adoption barriers becomes critical...\n\nObjective\n\nThis study aims to identify and quantify barriers to digital health technology adoption among adults aged 65 and older, and to explore potential facilitators for increased engagement...\n\nMethods\n\nWe employed a sequential explanatory mixed-methods design. Phase 1 involved a nationally representative survey of 2,500 older adults. Phase 2 consisted of semi-structured interviews with 150 participants selected through purposive sampling...\n\nResults\n\nTechnological literacy emerged as the primary barrier, with 67% reporting difficulty navigating digital interfaces. Privacy and security concerns affected 54% of respondents, particularly regarding health data sharing. Perceived lack of benefit was cited by 43%, often due to preference for in-person care...\n\nConclusions\n\nAddressing digital health adoption barriers requires multi-faceted approaches including user-centered design, digital literacy programs, and hybrid care models that maintain human connection while leveraging technology benefits...",
            },
            {
                "title": "Artificial Intelligence in Clinical Decision Support: A Systematic Review of Diagnostic Accuracy",
                "authors": ["Emily Zhang", "David Martinez", "Lisa Anderson"],
                "year": 2023,
                "journal": "The Lancet Digital Health",
                "volume": "5",
                "issue": "8",
                "pages": "e523-e535",
                "doi": "10.1016/S2589-7500(23)00089-0",
                "abstract": "AI-based clinical decision support systems (CDSS) show promising diagnostic accuracy across multiple medical specialties. This systematic review analyzed 89 studies comparing AI diagnostic performance to clinical experts. In radiology, AI achieved 94.5% sensitivity and 95.3% specificity for detecting malignancies. Dermatology applications showed 91.2% accuracy for skin cancer detection. However, real-world implementation faces challenges including algorithm bias, interpretability, and integration with clinical workflows.",
                "full_text": "Introduction\n\nArtificial intelligence has emerged as a transformative technology in healthcare, particularly in diagnostic imaging and pattern recognition. This systematic review evaluates the current state of AI diagnostic accuracy across clinical specialties...\n\nMethods\n\nWe searched MEDLINE, Embase, and IEEE Xplore for studies published between 2018 and 2023 comparing AI diagnostic performance to human experts or established diagnostic standards. Quality assessment used QUADAS-2 criteria...\n\nResults\n\nRadiology applications dominated the literature (n=42 studies), with deep learning models achieving expert-level performance in chest X-ray interpretation (AUC 0.94), mammography (AUC 0.92), and CT lung nodule detection (sensitivity 94.5%). Dermatology studies (n=18) showed comparable accuracy to dermatologists for melanoma detection...\n\nChallenges and Limitations\n\nDespite impressive accuracy metrics, several challenges impede clinical translation. Dataset bias remains problematic, with most training data from high-resource settings. Algorithmic interpretability is limited, creating trust barriers among clinicians...\n\nConclusions\n\nAI demonstrates diagnostic accuracy comparable to or exceeding human experts in specific domains. Successful implementation requires addressing technical, ethical, and workflow integration challenges...",
            },
            {
                "title": "Telemedicine Effectiveness During COVID-19: A Global Meta-Analysis",
                "authors": ["James Wilson", "Maria Garcia", "Thomas Lee"],
                "year": 2023,
                "journal": "BMJ Global Health",
                "volume": "8",
                "issue": "4",
                "pages": "e011234",
                "doi": "10.1136/bmjgh-2023-011234",
                "abstract": "The COVID-19 pandemic accelerated telemedicine adoption globally. This meta-analysis of 156 studies across 42 countries evaluates telemedicine effectiveness for various conditions during 2020-2023. Patient satisfaction rates averaged 86%, with no significant differences in clinical outcomes compared to in-person care for chronic disease management. Cost savings averaged 23% per consultation. However, disparities in access persisted, particularly in low-resource settings.",
                "full_text": "Introduction\n\nThe COVID-19 pandemic necessitated rapid healthcare delivery transformation, with telemedicine emerging as a critical tool for maintaining care continuity. This meta-analysis synthesizes global evidence on telemedicine effectiveness during the pandemic period...\n\nMethods\n\nWe conducted a comprehensive search of multiple databases for studies evaluating telemedicine interventions during COVID-19 (March 2020 - March 2023). Random-effects meta-analysis was performed for clinical outcomes, patient satisfaction, and cost-effectiveness...\n\nResults\n\nFrom 4,567 articles screened, 156 studies met inclusion criteria, representing 2.3 million patients across 42 countries. Chronic disease management via telemedicine showed non-inferior outcomes for diabetes (HbA1c difference: -0.08%, 95% CI: -0.15 to -0.01), hypertension (systolic BP difference: -1.2 mmHg, 95% CI: -2.4 to 0.1), and mental health conditions...\n\nPatient Experience\n\nPatient satisfaction rates were high across regions (mean 86%, range 71-94%). Key satisfaction drivers included convenience (92%), reduced travel time (89%), and maintained care quality (78%). Dissatisfaction related to technical difficulties (31%) and lack of physical examination (28%)...\n\nConclusions\n\nTelemedicine proved effective for maintaining healthcare delivery during COVID-19, with outcomes comparable to traditional care for many conditions. Post-pandemic integration should address equity concerns and optimize hybrid care models...",
            },
            {
                "title": "Wearable Devices for Continuous Health Monitoring: Clinical Validation and Real-World Evidence",
                "authors": ["Kevin Park", "Jennifer White", "Christopher Davis"],
                "year": 2024,
                "journal": "npj Digital Medicine",
                "volume": "7",
                "issue": "1",
                "pages": "45",
                "doi": "10.1038/s41746-024-01012-z",
                "abstract": "Consumer wearable devices increasingly claim health monitoring capabilities, but clinical validation remains inconsistent. This study evaluated 25 popular wearables against medical-grade equipment for heart rate, blood oxygen, and activity tracking. While heart rate monitoring showed excellent accuracy (r=0.96), SpO2 measurements varied significantly (r=0.72-0.89). Real-world data from 10,000 users revealed high engagement initially (82%) declining to 34% at 6 months, highlighting adherence challenges.",
                "full_text": "Introduction\n\nThe wearable device market has expanded rapidly, with manufacturers increasingly positioning products as health monitoring tools. This study provides comprehensive clinical validation of consumer wearables and analyzes real-world usage patterns...\n\nMethods\n\nPhase 1: Laboratory validation compared 25 consumer wearables (smartwatches, fitness trackers, rings) against gold-standard medical devices. Measurements included heart rate, SpO2, sleep stages, and physical activity. Phase 2: Prospective cohort study followed 10,000 users for 12 months, tracking engagement patterns and health outcomes...\n\nValidation Results\n\nHeart rate monitoring demonstrated excellent agreement with ECG (mean absolute error: 2.3 bpm, r=0.96). Performance was consistent across activities except high-intensity exercise (MAE: 5.7 bpm). SpO2 accuracy varied by device, with newer models showing improved performance (r=0.89 vs 0.72 for older generations)...\n\nReal-World Engagement\n\nInitial engagement was high (82% daily use in month 1) but declined significantly over time. At 6 months, only 34% maintained daily use. Factors associated with sustained engagement included goal setting (OR 2.3), social features (OR 1.8), and health condition monitoring (OR 3.1)...\n\nClinical Implications\n\nWhile wearables show promise for continuous monitoring, clinical integration requires careful consideration of accuracy limitations and engagement sustainability. Hybrid models combining wearable data with periodic clinical validation may optimize outcomes...",
            },
        ]

        self.build_from_papers(demo_papers)


@click.command()
@click.option("--demo", is_flag=True, help="Build demo knowledge base with sample papers")
@click.option(
    "--api-url",
    help="Custom Zotero API URL (e.g., http://host.docker.internal:23119/api for WSL)",
)
@click.option("--knowledge-base-path", default="kb_data", help="Path to knowledge base directory")
@click.option("--zotero-data-dir", help="Path to Zotero data directory (default: ~/Zotero)")
@click.option(
    "--clear-cache",
    is_flag=True,
    help="Force full rebuild - clear all caches and rebuild from scratch",
)
@click.option(
    "--export", "export_path", help="Export knowledge base to portable archive (e.g., kb_export.tar.gz)"
)
@click.option("--import", "import_path", help="Import knowledge base from portable archive")
@click.option("--update", is_flag=True, help="Incremental update - only add new papers (10x faster)")
def main(
    demo: bool,
    api_url: str | None,
    knowledge_base_path: str,
    zotero_data_dir: str | None,
    clear_cache: bool,
    export_path: str | None,
    import_path: str | None,
    update: bool,
) -> None:
    """Build knowledge base for research assistant.

    By default, connects to local Zotero library via HTTP API.
    Requires Zotero to be running with 'Allow other applications' enabled.

    For WSL users with Zotero on Windows host, the API URL will be auto-detected.
    """
    import tarfile

    # Handle export first (doesn't need builder)
    if export_path:
        kb_path = Path(knowledge_base_path)
        if not kb_path.exists():
            print(f"❌ Knowledge base not found at {kb_path}")
            sys.exit(1)

        print(f"📦 Exporting knowledge base to {export_path}...")

        # Create tar.gz archive
        with tarfile.open(export_path, "w:gz") as tar:
            # Add all KB files
            tar.add(kb_path, arcname="kb_data")

        # Calculate size
        size_mb = os.path.getsize(export_path) / (1024 * 1024)
        print(f"✅ Exported KB to {export_path} ({size_mb:.1f} MB)")
        print("\nTransfer this file to your other computer and import with:")
        print(f"  python src/build_kb.py --import {export_path}")
        return

    # Handle import
    if import_path:
        if not Path(import_path).exists():
            print(f"❌ Archive file not found: {import_path}")
            sys.exit(1)

        kb_path = Path(knowledge_base_path)

        # Check if KB already exists
        if kb_path.exists():
            response = input(f"⚠️  Knowledge base already exists at {kb_path}. Overwrite? [y/N]: ")
            if response.lower() != "y":
                print("Import cancelled.")
                return

            # Backup existing KB
            import shutil

            backup_path = f"{kb_path}_backup_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}"
            shutil.move(str(kb_path), backup_path)
            print(f"📁 Backed up existing KB to {backup_path}")

        print(f"📦 Importing knowledge base from {import_path}...")

        # Extract archive
        with tarfile.open(import_path, "r:gz") as tar:
            # Extract to parent directory
            # Safe extraction with path validation
            for member in tar.getmembers():
                # Validate that extracted files stay within target directory
                member_path = os.path.normpath(os.path.join(str(kb_path.parent), member.name))
                if not member_path.startswith(str(kb_path.parent)):
                    raise ValueError(f"Unsafe tar file: {member.name}")
            tar.extractall(kb_path.parent)  # noqa: S202

        # Verify import
        metadata_file = kb_path / "metadata.json"
        if metadata_file.exists():
            with open(metadata_file) as f:
                metadata = json.load(f)
                paper_count = metadata.get("total_papers", 0)
                last_updated = metadata.get("last_updated", "Unknown")

            print(f"✅ Successfully imported {paper_count} papers")
            print(f"   Last updated: {last_updated}")
            print(f"   Location: {kb_path}")
        else:
            print("⚠️  Import completed but metadata not found")

        return

    # Regular build process
    # Delay instantiation until after help flag is handled
    builder = KnowledgeBaseBuilder(knowledge_base_path, zotero_data_dir)

    # Clear caches if requested
    if clear_cache:
        builder.clear_cache()
        builder.clear_embedding_cache()

    if demo:
        print("Building demo knowledge base...")
        builder.build_demo_kb()
    else:
        # Auto-detect WSL environment and Windows host IP if no API URL provided
        if not api_url:
            # Check if we're in WSL
            try:
                with open("/proc/version") as f:
                    if "microsoft" in f.read().lower():
                        # We're in WSL, get Windows host IP
                        import subprocess

                        result = subprocess.run(  # noqa: S603
                            ["/bin/cat", "/etc/resolv.conf"],
                            capture_output=True,
                            text=True,
                            check=False,
                        )
                        for line in result.stdout.split("\n"):
                            if "nameserver" in line:
                                host_ip = line.split()[1]
                                api_url = f"http://{host_ip}:23119/api"
                                print(f"Detected WSL environment. Using Windows host at {host_ip}")
                                break
            except (OSError, FileNotFoundError, PermissionError):
                pass  # Not in WSL or can't read file

        print("Connecting to Zotero library...")
        if api_url:
            print(f"Using API URL: {api_url}")
        else:
            print("Using default: http://localhost:23119/api")

        print("Ensure Zotero is running and 'Allow other applications' is enabled in Advanced settings")

        try:
            # Pass skip_prompt=True when using --clear-cache flag
            # Pass incremental=True when using --update flag
            builder.build_from_zotero_local(
                api_url, use_cache=True, skip_prompt=clear_cache, incremental=update
            )
        except ConnectionError as e:
            print(f"Error building knowledge base: {e}")
            print("\nTip: For a quick demo, run: python src/build_kb.py --demo")
            print("For local Zotero library, ensure Zotero is running and try again.")
            print("\nTo enable local API access:")
            print("1. Open Zotero on your Windows host")
            print("2. Go to Edit > Settings > Advanced")
            print("3. Check 'Allow other applications on this computer to communicate with Zotero'")
            print("4. Restart Zotero if needed")
            # Safely check if running in WSL
            is_wsl = False
            try:
                with open("/proc/version") as f:
                    is_wsl = "microsoft" in f.read().lower()
            except (OSError, FileNotFoundError, PermissionError):
                pass

            if "WSL" in str(e) or is_wsl:
                print("\nFor WSL users:")
                print("- Ensure Windows Firewall allows connections on port 23119")
                print("- You may need to manually specify the API URL:")
                print("  python build_kb.py --api-url http://<windows-host-ip>:23119/api")
            sys.exit(1)
        except Exception as e:
            print(f"Error building knowledge base: {e}")
            print("\nTip: For a quick demo, run: python src/build_kb.py --demo")
            print("For local Zotero library, ensure Zotero is running and try again.")
            sys.exit(1)


if __name__ == "__main__":
    main()
