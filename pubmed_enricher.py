#!/usr/bin/env python3
"""PubMed Enrichment for V5 Pipeline
Adds authoritative medical metadata for biomedical papers.

Features:
- MeSH terms with qualifiers and major/minor designation
- Publication types (Clinical Trial, Review, Meta-Analysis, etc.)
- Chemical substances and gene symbols
- Clinical trial numbers (NCT identifiers)
- Grant information and funding
- Comments, corrections, and retractions
- ~30% coverage (biomedical subset of papers)
"""

import json
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime
from typing import Any
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from collections import defaultdict
import re


class PubMedEnricher:
    """Enrich papers with PubMed biomedical metadata."""

    def __init__(self, api_key: str | None = None):
        """Initialize PubMed enricher.

        Args:
            api_key: Optional NCBI API key for higher rate limits (10/sec vs 3/sec)
        """
        self.base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
        self.api_key = api_key
        self.session = self._create_session()
        self.stats = defaultdict(int)

        # Rate limiting based on API key
        self.delay = 0.1 if api_key else 0.34  # 10/sec with key, 3/sec without

    def _create_session(self) -> requests.Session:
        """Create HTTP session with retry logic."""
        session = requests.Session()
        retry = Retry(total=5, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        # Set user agent
        session.headers.update(
            {"User-Agent": "Research Assistant v5.0 (https://github.com/research-assistant)"}
        )

        return session

    def enrich_single_by_doi(self, doi: str) -> dict[str, Any] | None:
        """Enrich a single paper by DOI.

        Args:
            doi: Paper DOI

        Returns:
            Enriched metadata or None if not found
        """
        # Clean DOI
        clean_doi = self._clean_doi(doi)
        if not clean_doi:
            self.stats["invalid_doi"] += 1
            return None

        # First, convert DOI to PMID
        pmid = self._doi_to_pmid(clean_doi)
        if not pmid:
            self.stats["not_in_pubmed"] += 1
            return None

        # Then fetch full metadata
        return self.enrich_single_by_pmid(pmid)

    def enrich_single_by_pmid(self, pmid: str) -> dict[str, Any] | None:
        """Enrich a single paper by PMID.

        Args:
            pmid: PubMed ID

        Returns:
            Enriched metadata or None if not found
        """
        try:
            # Fetch metadata from PubMed
            params = {"db": "pubmed", "id": pmid, "retmode": "xml"}
            if self.api_key:
                params["api_key"] = self.api_key

            response = self.session.get(f"{self.base_url}/efetch.fcgi", params=params, timeout=30)
            response.raise_for_status()

            # Parse XML response
            root = ET.fromstring(response.content)
            article = root.find(".//PubmedArticle")

            if article is None:
                self.stats["parse_error"] += 1
                return None

            enriched = self._parse_pubmed_article(article)
            enriched["pmid"] = pmid

            self.stats["enriched"] += 1
            return enriched

        except Exception as e:
            self.stats["error"] += 1
            print(f"Error enriching PMID {pmid}: {e}")
            return None

    def _clean_doi(self, doi: str) -> str | None:
        """Clean and validate a DOI (reuses logic from OpenAlex/Unpaywall).

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
            if "doi.org/" in clean:
                clean = clean.split("doi.org/")[-1]
            elif "doi=" in clean:
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

        # Validate basic DOI format
        if not clean.startswith("10."):
            return None
        if len(clean) < 10 or len(clean) > 100:
            return None

        return clean

    def _doi_to_pmid(self, doi: str) -> str | None:
        """Convert DOI to PMID using PubMed search.

        Args:
            doi: Cleaned DOI

        Returns:
            PMID or None if not found
        """
        try:
            # Search PubMed for DOI
            params = {"db": "pubmed", "term": f"{doi}[DOI]", "retmode": "json"}
            if self.api_key:
                params["api_key"] = self.api_key

            response = self.session.get(f"{self.base_url}/esearch.fcgi", params=params, timeout=30)
            response.raise_for_status()

            data = response.json()
            result = data.get("esearchresult", {})
            id_list = result.get("idlist", [])

            if id_list:
                return id_list[0]  # Return first (should be only) match

            return None

        except Exception as e:
            print(f"Error converting DOI to PMID: {e}")
            return None

    def _parse_pubmed_article(self, article: ET.Element) -> dict[str, Any]:
        """Parse PubMed article XML into structured metadata.

        Args:
            article: PubmedArticle XML element

        Returns:
            Parsed metadata
        """
        enriched = {}

        # Get MedlineCitation element
        medline = article.find("MedlineCitation")
        if medline is None:
            return enriched

        # Basic article info
        article_elem = medline.find(".//Article")
        if article_elem:
            # Title
            title = article_elem.findtext(".//ArticleTitle", "")
            if title:
                enriched["title"] = title

            # Abstract
            abstract_elem = article_elem.find(".//Abstract")
            if abstract_elem is not None:
                abstract_parts = []
                for abstract_text in abstract_elem.findall(".//AbstractText"):
                    label = abstract_text.get("Label")
                    text = abstract_text.text or ""
                    if label:
                        abstract_parts.append(f"{label}: {text}")
                    else:
                        abstract_parts.append(text)
                if abstract_parts:
                    enriched["abstract"] = " ".join(abstract_parts)

            # Journal info
            journal = article_elem.find(".//Journal")
            if journal is not None:
                journal_title = journal.findtext(".//Title", "")
                if journal_title:
                    enriched["journal"] = journal_title

                # Publication date
                pub_date = journal.find(".//PubDate")
                if pub_date is not None:
                    year = pub_date.findtext("Year")
                    month = pub_date.findtext("Month")
                    day = pub_date.findtext("Day")
                    if year:
                        enriched["publication_year"] = int(year)
                    if year and month:
                        enriched["publication_date"] = f"{year}-{month}"
                        if day:
                            enriched["publication_date"] += f"-{day}"

            # Authors
            authors = []
            for author in article_elem.findall(".//Author"):
                last_name = author.findtext("LastName", "")
                fore_name = author.findtext("ForeName", "")
                if last_name:
                    author_name = f"{fore_name} {last_name}".strip()
                    authors.append(author_name)

                    # Affiliations
                    affiliation = author.findtext(".//Affiliation")
                    if affiliation and "affiliations" not in enriched:
                        enriched["affiliations"] = []
                    if affiliation:
                        enriched["affiliations"].append(affiliation)

            if authors:
                enriched["authors"] = authors

            # Publication types
            pub_types = []
            for pub_type in article_elem.findall(".//PublicationType"):
                pub_type_text = pub_type.text
                if pub_type_text:
                    pub_types.append(pub_type_text)
            if pub_types:
                enriched["publication_types"] = pub_types

        # MeSH terms
        mesh_terms = []
        for mesh in medline.findall(".//MeshHeading"):
            descriptor = mesh.findtext("DescriptorName", "")
            is_major = mesh.find("DescriptorName").get("MajorTopicYN", "N") == "Y"

            mesh_entry = {"descriptor": descriptor, "is_major": is_major}

            # Qualifiers
            qualifiers = []
            for qualifier in mesh.findall("QualifierName"):
                qual_name = qualifier.text
                qual_major = qualifier.get("MajorTopicYN", "N") == "Y"
                if qual_name:
                    qualifiers.append({"name": qual_name, "is_major": qual_major})

            if qualifiers:
                mesh_entry["qualifiers"] = qualifiers

            mesh_terms.append(mesh_entry)

        if mesh_terms:
            enriched["mesh_terms"] = mesh_terms

        # Chemical list
        chemicals = []
        for chemical in medline.findall(".//Chemical"):
            substance = chemical.findtext("NameOfSubstance", "")
            registry_number = chemical.findtext("RegistryNumber", "")
            if substance:
                chem_entry = {"name": substance}
                if registry_number and registry_number != "0":
                    chem_entry["registry_number"] = registry_number
                chemicals.append(chem_entry)

        if chemicals:
            enriched["chemicals"] = chemicals

        # Keywords
        keywords = []
        for keyword in medline.findall(".//Keyword"):
            kw_text = keyword.text
            if kw_text:
                keywords.append(kw_text)
        if keywords:
            enriched["keywords"] = keywords

        # Grants
        grants = []
        for grant in medline.findall(".//Grant"):
            grant_id = grant.findtext("GrantID", "")
            agency = grant.findtext("Agency", "")
            country = grant.findtext("Country", "")
            if grant_id or agency:
                grant_entry = {}
                if grant_id:
                    grant_entry["id"] = grant_id
                if agency:
                    grant_entry["agency"] = agency
                if country:
                    grant_entry["country"] = country
                grants.append(grant_entry)

        if grants:
            enriched["grants"] = grants

        # Data availability
        data_banks = []
        for databank in medline.findall(".//DataBank"):
            bank_name = databank.findtext("DataBankName", "")
            if bank_name:
                accessions = []
                for acc in databank.findall(".//AccessionNumber"):
                    if acc.text:
                        accessions.append(acc.text)
                if accessions:
                    data_banks.append({"name": bank_name, "accession_numbers": accessions})

        if data_banks:
            enriched["data_banks"] = data_banks

        # Comments and corrections
        comments = []
        for comment in medline.findall(".//CommentsCorrectionsList/CommentsCorrections"):
            ref_type = comment.get("RefType", "")
            ref_pmid = comment.findtext("PMID", "")
            if ref_type and ref_pmid:
                comments.append({"type": ref_type, "pmid": ref_pmid})

        if comments:
            enriched["related_articles"] = comments

        # Track statistics
        if mesh_terms:
            self.stats["has_mesh"] += 1
        if chemicals:
            self.stats["has_chemicals"] += 1
        if pub_types:
            for pt in pub_types:
                if "Clinical Trial" in pt:
                    self.stats["clinical_trials"] += 1
                    break
                if "Review" in pt:
                    self.stats["reviews"] += 1
                    break
                if "Meta-Analysis" in pt:
                    self.stats["meta_analyses"] += 1
                    break

        return enriched

    def enrich_batch(
        self, identifiers: list[dict[str, str]], batch_size: int = 20
    ) -> dict[str, dict[str, Any]]:
        """Enrich multiple papers by DOI or PMID.

        Args:
            identifiers: List of dicts with 'doi' and/or 'pmid' keys
            batch_size: Number of PMIDs to fetch at once (max 200)

        Returns:
            Dictionary mapping original identifier to enriched metadata
        """
        results = {}

        # Step 1: Convert DOIs to PMIDs
        pmid_map = {}  # Maps PMID to original identifier
        pmids_to_fetch = []

        for id_dict in identifiers:
            original_key = id_dict.get("doi") or id_dict.get("pmid")

            if id_dict.get("pmid"):
                # Already have PMID
                pmids_to_fetch.append(id_dict["pmid"])
                pmid_map[id_dict["pmid"]] = original_key
            elif id_dict.get("doi"):
                # Convert DOI to PMID
                clean_doi = self._clean_doi(id_dict["doi"])
                if clean_doi:
                    pmid = self._doi_to_pmid(clean_doi)
                    if pmid:
                        pmids_to_fetch.append(pmid)
                        pmid_map[pmid] = original_key
                    else:
                        self.stats["not_in_pubmed"] += 1
                else:
                    self.stats["invalid_doi"] += 1

            # Rate limiting for DOI lookups
            time.sleep(self.delay)

        if not pmids_to_fetch:
            return results

        # Step 2: Fetch metadata in batches
        for i in range(0, len(pmids_to_fetch), batch_size):
            batch_pmids = pmids_to_fetch[i : i + batch_size]

            try:
                # Fetch batch
                params = {"db": "pubmed", "id": ",".join(batch_pmids), "retmode": "xml"}
                if self.api_key:
                    params["api_key"] = self.api_key

                response = self.session.get(f"{self.base_url}/efetch.fcgi", params=params, timeout=60)
                response.raise_for_status()

                # Parse XML response
                root = ET.fromstring(response.content)

                # Process each article
                for article in root.findall(".//PubmedArticle"):
                    pmid_elem = article.find(".//PMID")
                    if pmid_elem is not None and pmid_elem.text:
                        pmid = pmid_elem.text
                        if pmid in pmid_map:
                            enriched = self._parse_pubmed_article(article)
                            enriched["pmid"] = pmid

                            original_key = pmid_map[pmid]
                            results[original_key] = enriched
                            self.stats["enriched"] += 1

            except Exception as e:
                print(f"Error fetching batch: {e}")
                self.stats["batch_error"] += 1

            # Rate limiting between batches
            time.sleep(self.delay)

        # Count failures
        self.stats["failed"] = len(identifiers) - len(results)

        return results

    def get_statistics(self) -> dict[str, Any]:
        """Get enrichment statistics."""
        total = self.stats["enriched"] + self.stats["failed"]

        return {
            "total_processed": total,
            "enriched": self.stats["enriched"],
            "failed": self.stats["failed"],
            "enrichment_rate": f"{(self.stats['enriched'] / total * 100):.1f}%" if total else "0%",
            "not_in_pubmed": self.stats["not_in_pubmed"],
            "has_mesh": self.stats["has_mesh"],
            "mesh_coverage": f"{(self.stats['has_mesh'] / self.stats['enriched'] * 100):.1f}%"
            if self.stats["enriched"]
            else "0%",
            "has_chemicals": self.stats["has_chemicals"],
            "publication_types": {
                "clinical_trials": self.stats.get("clinical_trials", 0),
                "reviews": self.stats.get("reviews", 0),
                "meta_analyses": self.stats.get("meta_analyses", 0),
            },
            "errors": {
                "invalid_doi": self.stats.get("invalid_doi", 0),
                "parse_error": self.stats.get("parse_error", 0),
                "batch_error": self.stats.get("batch_error", 0),
                "other": self.stats.get("error", 0),
            },
        }


def process_directory(input_dir: str, output_dir: str, api_key: str | None = None):
    """Process all papers in a directory with PubMed enrichment.

    Args:
        input_dir: Directory containing paper JSON files
        output_dir: Directory to save enriched papers
        api_key: Optional NCBI API key for higher rate limits
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Initialize enricher
    enricher = PubMedEnricher(api_key=api_key)

    # Load papers
    paper_files = list(input_path.glob("*.json"))
    print(f"Found {len(paper_files)} papers to process")

    # Collect identifiers
    identifiers = []
    papers_by_id = {}

    for paper_file in paper_files:
        # Skip report files
        if "report" in paper_file.name:
            continue

        with open(paper_file) as f:
            paper = json.load(f)

            # Prepare identifier dict
            id_dict = {}
            if paper.get("pmid"):
                id_dict["pmid"] = paper["pmid"]
            elif paper.get("doi"):
                id_dict["doi"] = paper["doi"]

            if id_dict:
                key = id_dict.get("doi") or id_dict.get("pmid")
                identifiers.append(id_dict)
                papers_by_id[key] = (paper_file.stem, paper)

    print(f"Found {len(identifiers)} papers with DOIs or PMIDs")

    # Process in batches
    batch_size = 20
    all_results = {}
    start_time = time.time()

    print("\nProcessing papers with PubMed API...")
    if not api_key:
        print("Note: No API key provided. Using slower rate limit (3 requests/sec)")
        print("Get a free API key at: https://www.ncbi.nlm.nih.gov/account/")

    for i in range(0, len(identifiers), batch_size):
        batch = identifiers[i : i + batch_size]
        batch_num = i // batch_size + 1
        total_batches = (len(identifiers) + batch_size - 1) // batch_size

        print(f"\nProcessing batch {batch_num}/{total_batches} ({len(batch)} papers)...")

        # Enrich batch
        batch_results = enricher.enrich_batch(batch, batch_size=batch_size)
        all_results.update(batch_results)

        # Show progress
        stats = enricher.get_statistics()
        print(f"  Enriched: {stats['enriched']}/{stats['total_processed']}")
        print(f"  MeSH coverage: {stats['mesh_coverage']}")

    # Save enriched papers
    print("\nSaving enriched papers...")
    enriched_count = 0
    for key, (paper_id, original_paper) in papers_by_id.items():
        if key in all_results:
            enrichment = all_results[key]

            # Add PubMed fields with prefix
            for field, value in enrichment.items():
                if value is not None:
                    original_paper[f"pubmed_{field}"] = value

            enriched_count += 1

        # Save paper (enriched or not)
        output_file = output_path / f"{paper_id}.json"
        with open(output_file, "w") as f:
            json.dump(original_paper, f, indent=2)

    elapsed_time = time.time() - start_time

    # Generate report
    final_stats = enricher.get_statistics()
    report = {
        "timestamp": datetime.now().isoformat(),
        "pipeline_stage": "7_pubmed_enrichment",
        "statistics": {
            "total_papers": len(paper_files),
            "papers_with_identifiers": len(identifiers),
            "papers_enriched": final_stats["enriched"],
            "papers_failed": final_stats["failed"],
            "enrichment_rate": final_stats["enrichment_rate"],
            "not_in_pubmed": final_stats["not_in_pubmed"],
            "processing_time_seconds": round(elapsed_time, 1),
        },
        "biomedical_metadata": {
            "mesh_terms": final_stats["has_mesh"],
            "mesh_coverage": final_stats["mesh_coverage"],
            "chemicals": final_stats["has_chemicals"],
            "publication_types": final_stats["publication_types"],
        },
        "errors": final_stats["errors"],
    }

    report_file = output_path / "pubmed_enrichment_report.json"
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)

    print("\nEnrichment complete!")
    print(
        f"  Papers enriched: {final_stats['enriched']}/{len(identifiers)} ({final_stats['enrichment_rate']})"
    )
    print(f"  MeSH term coverage: {final_stats['has_mesh']} papers ({final_stats['mesh_coverage']})")
    print(f"  Clinical trials: {final_stats['publication_types']['clinical_trials']}")
    print(f"  Reviews: {final_stats['publication_types']['reviews']}")
    print(f"  Meta-analyses: {final_stats['publication_types']['meta_analyses']}")
    print(f"  Processing time: {elapsed_time:.1f} seconds")
    print(f"  Report saved to: {report_file}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Enrich papers with PubMed biomedical metadata")
    parser.add_argument("--input", default="unpaywall_enriched_final", help="Input directory with papers")
    parser.add_argument("--output", default="pubmed_enriched", help="Output directory")
    parser.add_argument("--api-key", help="NCBI API key for higher rate limits (free from NCBI)")
    parser.add_argument("--test", action="store_true", help="Test with single paper")

    args = parser.parse_args()

    if args.test:
        # Test with a biomedical paper
        enricher = PubMedEnricher(api_key=args.api_key)

        # Test DOI lookup (COVID-19 paper likely in PubMed)
        test_doi = "10.1038/s41586-020-2012-7"  # COVID-19 origin paper

        print(f"Testing with DOI: {test_doi}")
        result = enricher.enrich_single_by_doi(test_doi)

        if result:
            print("\nEnrichment successful!")
            print(json.dumps(result, indent=2))

            # Show statistics
            stats = enricher.get_statistics()
            print(f"\nStatistics: {json.dumps(stats, indent=2)}")
        else:
            print("Paper not found in PubMed")

            # Try another paper
            test_doi_2 = "10.1056/NEJMoa2001017"  # First COVID-19 clinical report
            print(f"\nTrying another DOI: {test_doi_2}")
            result = enricher.enrich_single_by_doi(test_doi_2)

            if result:
                print("\nEnrichment successful!")
                print(f"Title: {result.get('title', 'N/A')[:60]}")
                print(f"PMID: {result.get('pmid', 'N/A')}")
                print(f"MeSH terms: {len(result.get('mesh_terms', []))}")
                print(f"Publication types: {result.get('publication_types', [])}")
    else:
        process_directory(args.input, args.output, args.api_key)
