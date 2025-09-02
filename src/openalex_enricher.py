#!/usr/bin/env python3
"""OpenAlex Enrichment for V5 Pipeline.

Adds topic classification, SDG mapping, and comprehensive citation networks.

Features:
- 100% topic classification coverage (AI-generated for all papers)
- Sustainable Development Goals mapping
- Institution data with ROR IDs
- Citation velocity (year-by-year counts)
- Work type classification
- No authentication required (email for polite pool)
"""

from src import config
import json
import time
from pathlib import Path
from datetime import datetime, UTC
from typing import Any
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class OpenAlexEnricher:
    """Enrich papers with OpenAlex metadata."""

    def __init__(self, email: str | None = None):
        """Initialize OpenAlex enricher.

        Args:
            email: Optional email for polite pool (higher rate limits)
        """
        self.base_url = "https://api.openalex.org"
        self.email = email
        self.batch_size = 50  # OpenAlex OR filter limit
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        """Create HTTP session with retry logic."""
        session = requests.Session()
        retry = Retry(total=5, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        # Add email to headers for polite pool
        if self.email:
            session.headers.update({"User-Agent": f"mailto:{self.email}"})

        return session

    def enrich_single(self, doi: str) -> dict[str, Any] | None:
        """Enrich a single paper by DOI.

        Args:
            doi: Paper DOI

        Returns:
            Enriched metadata or None if not found
        """
        try:
            # Clean DOI
            clean_doi = self._clean_doi(doi)
            if not clean_doi:
                return None

            # Query OpenAlex
            params = {"filter": f"doi:{clean_doi}", "select": self._get_select_fields()}

            response = self.session.get(f"{self.base_url}/works", params=params, timeout=30)
            response.raise_for_status()

            data = response.json()
            if data.get("results"):
                return self._process_work(data["results"][0])

        except Exception as e:
            print(f"Error enriching {doi}: {e}")

        return None

    def _clean_doi(self, doi: str) -> str | None:
        """Clean and validate a DOI.

        Args:
            doi: Raw DOI string

        Returns:
            Cleaned DOI or None if invalid
        """
        if not doi:
            return None

        # Remove whitespace and convert to lowercase
        clean = doi.strip().lower()

        # Handle URLs
        if clean.startswith("http"):
            # Extract DOI from URL
            if "doi.org/" in clean:
                clean = clean.split("doi.org/")[-1]
            elif "doi=" in clean:
                # Extract from query parameter
                import re

                match = re.search(r"doi=([^&]+)", clean)
                if match:
                    clean = match.group(1)
                else:
                    return None
            else:
                return None

        # Remove common suffixes from extraction errors
        clean = clean.split(".from")[0]
        clean = clean.split("keywords")[0]
        clean = clean.rstrip(".)•")

        # Don't truncate DOIs - some are legitimately long
        # Just validate the format

        # Validate basic DOI format
        if not clean.startswith("10."):
            return None
        if len(clean) < config.DEFAULT_TIMEOUT or len(clean) > config.MIN_CONTENT_LENGTH:
            return None

        return clean

    def enrich_batch(self, dois: list[str]) -> dict[str, dict[str, Any]]:
        """Enrich multiple papers in a single API call.

        Args:
            dois: List of DOIs (max 50)

        Returns:
            Dictionary mapping DOI to enriched metadata
        """
        results: dict[str, dict[str, Any]] = {}

        # Clean DOIs
        clean_dois = []
        doi_map = {}  # Map clean to original

        for doi in dois[: self.batch_size]:
            clean = self._clean_doi(doi)
            if clean:
                clean_dois.append(clean)
                doi_map[clean] = doi

        if not clean_dois:
            return results

        try:
            # Build OR filter - OpenAlex uses OR operator, not pipe
            [f"doi:{doi}" for doi in clean_dois]
            doi_filter = f"doi:{'|'.join(clean_dois)}"  # doi:10.xxx|10.yyy format

            params: dict[str, Any] = {
                "filter": doi_filter,
                "per_page": self.batch_size,
                "select": self._get_select_fields(),
            }

            response = self.session.get(f"{self.base_url}/works", params=params, timeout=60)
            response.raise_for_status()

            data = response.json()

            # Process results
            for work in data.get("results", []):
                processed = self._process_work(work)
                if processed and processed.get("doi"):
                    # Map back to original DOI format
                    clean_doi = processed["doi"].lower()
                    original_doi = doi_map.get(clean_doi, clean_doi)
                    results[original_doi] = processed

        except Exception as e:
            print(f"Error in batch enrichment: {e}")

        return results

    def _get_select_fields(self) -> str:
        """Get fields to retrieve from OpenAlex."""
        fields = [
            "id",
            "doi",
            "title",
            "publication_year",
            "topics",
            "sustainable_development_goals",
            "cited_by_count",
            "counts_by_year",
            "authorships",
            "primary_location",
            "type",
            "open_access",
            "keywords",
            "concepts",
            "mesh",
            "referenced_works_count",
            "related_works",
            "cited_by_percentile_year",
            "biblio",
            "is_retracted",
            "is_paratext",
        ]
        return ",".join(fields)

    def _process_work(self, work: dict[str, Any]) -> dict[str, Any]:
        """Process OpenAlex work into enriched metadata.

        Args:
            work: Raw OpenAlex work data

        Returns:
            Processed metadata
        """
        enriched = {
            "openalex_id": work.get("id", "").replace("https://openalex.org/", ""),
            "doi": work.get("doi", "").replace("https://doi.org/", ""),
            "title": work.get("title"),
            "year": work.get("publication_year"),
            "type": work.get("type"),
            "is_retracted": work.get("is_retracted", False),
            "is_paratext": work.get("is_paratext", False),
        }

        # Topics (hierarchical classification)
        topics = work.get("topics", [])
        if topics:
            enriched["topics"] = []
            for topic in topics[:3]:  # Top 3 topics
                enriched["topics"].append(
                    {
                        "id": topic.get("id"),
                        "name": topic.get("display_name"),
                        "score": topic.get("score"),
                        "domain": topic.get("domain", {}).get("display_name"),
                        "field": topic.get("field", {}).get("display_name"),
                        "subfield": topic.get("subfield", {}).get("display_name"),
                    }
                )

        # Sustainable Development Goals
        sdgs = work.get("sustainable_development_goals", [])
        if sdgs:
            enriched["sdgs"] = []
            for sdg in sdgs:
                enriched["sdgs"].append(
                    {"id": sdg.get("id"), "name": sdg.get("display_name"), "score": sdg.get("score")}
                )

        # Citation metrics
        enriched["citation_count"] = work.get("cited_by_count", 0)
        enriched["reference_count"] = work.get("referenced_works_count", 0)

        # Citation velocity
        counts = work.get("counts_by_year", [])
        if counts:
            enriched["citations_by_year"] = {
                str(c["year"]): c["cited_by_count"] for c in counts if c.get("year")
            }

        # Citation percentile
        percentile = work.get("cited_by_percentile_year")
        if percentile:
            enriched["citation_percentile"] = {"min": percentile.get("min"), "max": percentile.get("max")}

        # Authors and institutions
        authorships = work.get("authorships", [])
        if authorships:
            enriched["authors"] = []
            institutions = set()

            for authorship in authorships:
                author = authorship.get("author", {})
                author_data = {
                    "id": author.get("id"),
                    "name": author.get("display_name"),
                    "orcid": author.get("orcid"),
                }
                enriched["authors"].append(author_data)

                # Collect institutions
                for inst in authorship.get("institutions", []):
                    if inst.get("display_name"):
                        institutions.add(inst["display_name"])

            if institutions:
                enriched["institutions"] = list(institutions)

        # Open Access status
        oa = work.get("open_access", {})
        if oa:
            enriched["open_access"] = {
                "is_oa": oa.get("is_oa", False),
                "status": oa.get("oa_status"),
                "url": oa.get("oa_url"),
            }

        # Keywords and concepts
        keywords = work.get("keywords", [])
        if keywords:
            enriched["keywords"] = [
                {"name": k.get("display_name"), "score": k.get("score")}
                for k in keywords
                if k.get("display_name")
            ]

        # MeSH terms (if available)
        mesh = work.get("mesh", [])
        if mesh:
            enriched["mesh_terms"] = [
                {
                    "descriptor": m.get("descriptor_name"),
                    "qualifier": m.get("qualifier_name"),
                    "is_major": m.get("is_major_topic"),
                }
                for m in mesh
            ]

        # Venue information
        location = work.get("primary_location", {})
        if location:
            source = location.get("source", {})
            if source:
                enriched["venue"] = {
                    "id": source.get("id"),
                    "name": source.get("display_name"),
                    "type": source.get("type"),
                    "issn": source.get("issn_l"),
                    "is_oa": source.get("is_oa"),
                }

        # Bibliographic info
        biblio = work.get("biblio", {})
        if biblio:
            enriched["volume"] = biblio.get("volume")
            enriched["issue"] = biblio.get("issue")
            enriched["first_page"] = biblio.get("first_page")
            enriched["last_page"] = biblio.get("last_page")

        return enriched


def process_directory(input_dir: str, output_dir: str, email: str | None = None) -> None:
    """Process all papers in a directory with OpenAlex enrichment.

    Args:
        input_dir: Directory containing paper JSON files
        output_dir: Directory to save enriched papers
        email: Optional email for polite pool
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Initialize enricher
    enricher = OpenAlexEnricher(email=email)

    # Load papers
    paper_files = list(input_path.glob("*.json"))
    print(f"Found {len(paper_files)} papers to process")

    # Collect papers with DOIs
    papers_with_dois = []
    papers_by_doi = {}

    for paper_file in paper_files:
        with open(paper_file) as f:
            paper = json.load(f)
            doi = paper.get("doi")
            if doi:
                papers_with_dois.append((paper_file.stem, doi))
                papers_by_doi[doi] = paper

    print(f"Found {len(papers_with_dois)} papers with DOIs")

    # Process in batches
    enriched_count = 0
    failed_count = 0
    results = {}

    for i in range(0, len(papers_with_dois), enricher.batch_size):
        batch = papers_with_dois[i : i + enricher.batch_size]
        batch_dois = [doi for _, doi in batch]

        print(
            f"Processing batch {i // enricher.batch_size + 1}/{(len(papers_with_dois) + enricher.batch_size - 1) // enricher.batch_size}"
        )

        # Enrich batch
        batch_results = enricher.enrich_batch(batch_dois)

        # Update papers
        for paper_id, doi in batch:
            if doi in batch_results:
                enrichment = batch_results[doi]
                original_paper = papers_by_doi[doi].copy()

                # Add OpenAlex fields with prefix
                for key, value in enrichment.items():
                    if value is not None:  # Only add non-null values
                        original_paper[f"openalex_{key}"] = value

                # Save enriched paper
                output_file = output_path / f"{paper_id}.json"
                with open(output_file, "w") as f:
                    json.dump(original_paper, f, indent=2)

                enriched_count += 1
                results[paper_id] = enrichment
            else:
                failed_count += 1

        # Rate limiting
        time.sleep(0.1)  # Polite delay between batches

    # Save report
    report = {
        "timestamp": datetime.now(UTC).isoformat(),
        "statistics": {
            "total_papers": len(paper_files),
            "papers_with_dois": len(papers_with_dois),
            "papers_enriched": enriched_count,
            "papers_failed": failed_count,
            "enrichment_rate": f"{(enriched_count / len(papers_with_dois) * 100):.1f}%"
            if papers_with_dois
            else "0%",
            "batches_processed": (len(papers_with_dois) + enricher.batch_size - 1) // enricher.batch_size,
            "avg_papers_per_batch": enricher.batch_size,
        },
    }

    # Analyze enrichments
    topic_coverage = sum(1 for r in results.values() if r.get("topics"))
    sdg_coverage = sum(1 for r in results.values() if r.get("sdgs"))
    oa_coverage = sum(1 for r in results.values() if r.get("open_access", {}).get("is_oa"))

    report["coverage"] = {
        "topics": f"{(topic_coverage / enriched_count * 100):.1f}%" if enriched_count else "0%",
        "sdgs": f"{(sdg_coverage / enriched_count * 100):.1f}%" if enriched_count else "0%",
        "open_access": f"{(oa_coverage / enriched_count * 100):.1f}%" if enriched_count else "0%",
    }

    report_file = output_path / "openalex_enrichment_report.json"
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)

    print("\nEnrichment complete!")
    print(
        f"  Papers enriched: {enriched_count}/{len(papers_with_dois)} ({(enriched_count / len(papers_with_dois) * 100):.1f}%)"
    )
    print(
        f"  Topic coverage: {topic_coverage}/{enriched_count} ({(topic_coverage / enriched_count * 100):.1f}%)"
        if enriched_count
        else ""
    )
    print(
        f"  SDG coverage: {sdg_coverage}/{enriched_count} ({(sdg_coverage / enriched_count * 100):.1f}%)"
        if enriched_count
        else ""
    )
    print(
        f"  Open Access: {oa_coverage}/{enriched_count} ({(oa_coverage / enriched_count * 100):.1f}%)"
        if enriched_count
        else ""
    )
    print(f"  Report saved to: {report_file}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Enrich papers with OpenAlex metadata")
    parser.add_argument("--input", default="s2_enriched_20250901_final", help="Input directory with papers")
    parser.add_argument("--output", default="openalex_enriched", help="Output directory")
    parser.add_argument("--email", help="Email for polite pool (higher rate limits)")
    parser.add_argument("--test", action="store_true", help="Test with single paper")

    args = parser.parse_args()

    if args.test:
        # Test with a single DOI
        enricher = OpenAlexEnricher(email=args.email)
        test_doi = "10.1038/s41586-020-2649-2"  # Example Nature paper

        print(f"Testing with DOI: {test_doi}")
        result = enricher.enrich_single(test_doi)

        if result:
            print("\nEnrichment successful!")
            print(json.dumps(result, indent=2))
        else:
            print("Enrichment failed")
    else:
        process_directory(args.input, args.output, args.email)
