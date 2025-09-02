#!/usr/bin/env python3
"""Grobid Overnight Runner - Maximum Data Extraction for Research.

Philosophy: Since Grobid runs are infrequent (overnight/weekend), we optimize for:
1. MAXIMUM data extraction - get EVERYTHING Grobid can provide
2. Complete preservation - save ALL formats for post-processing flexibility
3. Robustness - handle failures gracefully with checkpoint recovery

This replaces partial extraction approaches with comprehensive data capture.
Run this overnight/weekend when you want to process your entire paper collection.
"""

from src import config
import json
from defusedxml import ElementTree
from pathlib import Path
from typing import Any
import requests
import time
from datetime import datetime, UTC
import logging
import sys
from tqdm import tqdm

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(f"grobid_overnight_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


class OvernightGrobidExtractor:
    """Comprehensive Grobid extraction for overnight processing.

    Saves 7 different files per paper for maximum post-processing flexibility.
    """

    def __init__(
        self, grobid_url: str = "http://localhost:8070", output_dir: str = "grobid_overnight_output"
    ):
        """Initialize the overnight extractor with maximum extraction settings.

        Args:
            grobid_url: URL of Grobid service
            output_dir: Base directory for all output files
        """
        self.grobid_url = grobid_url
        self.output_dir = Path(output_dir)
        self.session_dir = self.output_dir / datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        self.session_dir.mkdir(parents=True, exist_ok=True)

        # Checkpoint file for recovery
        self.checkpoint_file = self.session_dir / "checkpoint.json"
        self.processed_files: set[str] = set()
        self.load_checkpoint()

        # Statistics
        self.stats: dict[str, Any] = {
            "total_papers": 0,
            "successful": 0,
            "failed": 0,
            "total_entities": 0,
            "start_time": datetime.now(UTC).isoformat(),
            "extraction_times": [],
        }

        # MAXIMUM extraction parameters - get EVERYTHING
        self.params = {
            # Maximum consolidation for entity enrichment
            "consolidateHeader": "2",  # Biblio-glutton (maximum enrichment)
            "consolidateCitations": "2",  # Full citation consolidation
            "consolidateFunders": "1",  # Extract funding information
            # Preserve all raw data
            "includeRawCitations": "1",
            "includeRawAffiliations": "1",
            "includeRawAuthors": "1",
            "includeRawCopyrights": "1",
            # Extract all structure types
            "processFigures": "1",
            "processTables": "1",
            "processEquations": "1",
            # Maximum text processing
            "segmentSentences": "1",
            "processSubStructures": "1",
            # Full coordinate information
            "teiCoordinates": "all",
            # Complete XML structure
            "generateIDs": "1",
            "addElementId": "1",
            # Experimental features (may not be in all versions)
            "extractDataAvailability": "1",
            "extractAcknowledgements": "1",
            "extractKeywords": "1",
            "extractGrants": "1",
            "extractClinicalTrials": "1",
            "extractSupplementary": "1",
            # Long timeout for complex papers
            "timeout": 300,
        }

        logger.info("=" * 80)
        logger.info("GROBID OVERNIGHT EXTRACTION INITIALIZED")
        logger.info("Mode: MAXIMUM EXTRACTION (7 files per paper)")
        logger.info("Output: %s", self.session_dir)
        logger.info("Parameters: %s maximum extraction flags", len(self.params))
        logger.info("=" * 80)

    def check_grobid_service(self) -> bool:
        """Check if Grobid service is running."""
        try:
            response = requests.get(f"{self.grobid_url}/api/isalive", timeout=5)
            return response.status_code == config.MIN_SECTION_TEXT_LENGTH
        except Exception:
            return False

    def load_checkpoint(self) -> None:
        """Load checkpoint to resume from interruption."""
        if self.checkpoint_file.exists():
            with open(self.checkpoint_file) as f:
                checkpoint = json.load(f)
                self.processed_files = set(checkpoint.get("processed_files", []))
                logger.info(
                    "Resuming from checkpoint: %s papers already processed", len(self.processed_files)
                )

    def save_checkpoint(self) -> None:
        """Save checkpoint for recovery."""
        with open(self.checkpoint_file, "w") as f:
            json.dump(
                {
                    "processed_files": list(self.processed_files),
                    "timestamp": datetime.now(UTC).isoformat(),
                    "stats": self.stats,
                },
                f,
                indent=2,
            )

    def extract_all_entities(self, tei_xml: str) -> dict[str, Any]:
        """Extract ALL possible entities from TEI XML.

        This is comprehensive and captures everything Grobid provides.
        """
        try:
            root = ElementTree.fromstring(tei_xml)
            ns = {"tei": "http://www.tei-c.org/ns/1.0"}

            result: dict[str, Any] = {
                "metadata": {},
                "entities": {},
                "sections": {},
                "coordinates": {},
                "statistics": {},
            }

            # Extract metadata
            result["metadata"] = {
                "title": self._extract_text(root, ".//tei:titleStmt/tei:title", ns),
                "abstract": self._extract_text(root, ".//tei:profileDesc/tei:abstract", ns),
                "doi": self._extract_text(root, './/tei:biblStruct//tei:idno[@type="DOI"]', ns),
                "authors": self._extract_authors(root, ns),
                "affiliations": self._extract_affiliations(root, ns),
                "keywords": self._extract_keywords(root, ns),
                "publication_date": self._extract_text(root, ".//tei:publicationStmt/tei:date", ns),
                "journal": self._extract_text(root, ".//tei:monogr/tei:title", ns),
            }

            # Extract all entity types
            result["entities"] = {
                "persons": self._extract_all_persons(root, ns),
                "organizations": self._extract_all_organizations(root, ns),
                "locations": self._extract_all_locations(root, ns),
                "citations": self._extract_all_citations(root, ns),
                "figures": self._extract_all_figures(root, ns),
                "tables": self._extract_all_tables(root, ns),
                "equations": self._extract_all_equations(root, ns),
                "software": self._extract_software_mentions(root, ns),
                "datasets": self._extract_dataset_mentions(root, ns),
                "funding": self._extract_funding(root, ns),
                "clinical_trials": self._extract_clinical_trials(root, ns),
                "statistics": self._extract_statistical_values(root, ns),
                "urls": self._extract_urls(root, ns),
                "emails": self._extract_emails(root, ns),
                "orcids": self._extract_orcids(root, ns),
            }

            # Extract full text sections
            body = root.find(".//tei:body", ns)
            if body is not None:
                result["sections"] = self._extract_sections(body, ns)

            # Extract coordinates if available
            result["coordinates"] = self._extract_coordinates(root, ns)

            # Count entities
            total_entities = sum(
                len(v) if isinstance(v, list) else 1 for v in result["entities"].values() if v
            )
            result["statistics"]["total_entities"] = total_entities

            return result

        except Exception as e:
            logger.error("Error parsing TEI XML: %s", e)
            return {}

    def _extract_text(self, element: Any, xpath: str, ns: dict[str, str]) -> str:
        """Extract text from element."""
        el = element.find(xpath, ns)
        if el is not None:
            return " ".join(el.itertext()).strip()
        return ""

    def _extract_authors(self, root: Any, ns: dict[str, str]) -> list[dict[str, str]]:
        """Extract all author information."""
        authors = []
        for author in root.findall(".//tei:sourceDesc//tei:author", ns):
            author_data = {
                "name": " ".join(author.itertext()).strip(),
                "first_name": self._extract_text(author, ".//tei:forename", ns),
                "last_name": self._extract_text(author, ".//tei:surname", ns),
                "email": self._extract_text(author, ".//tei:email", ns),
                "orcid": self._extract_text(author, './/tei:idno[@type="ORCID"]', ns),
                "affiliation": self._extract_text(author, ".//tei:affiliation", ns),
            }
            authors.append(author_data)
        return authors

    def _extract_affiliations(self, root: Any, ns: dict[str, str]) -> list[str]:
        """Extract all affiliations."""
        affiliations = []
        for aff in root.findall(".//tei:affiliation", ns):
            affiliations.append(" ".join(aff.itertext()).strip())
        return list(set(affiliations))  # Remove duplicates

    def _extract_keywords(self, root: Any, ns: dict[str, str]) -> list[str]:
        """Extract keywords."""
        keywords = []
        for kw in root.findall(".//tei:keywords//tei:term", ns):
            keywords.append(kw.text)
        return keywords

    def _extract_all_persons(self, root: Any, ns: dict[str, str]) -> list[str]:
        """Extract all person mentions."""
        persons = []
        for person in root.findall(".//tei:persName", ns):
            persons.append(" ".join(person.itertext()).strip())
        return list(set(persons))

    def _extract_all_organizations(self, root: Any, ns: dict[str, str]) -> list[str]:
        """Extract all organization mentions."""
        orgs = []
        for org in root.findall(".//tei:orgName", ns):
            orgs.append(" ".join(org.itertext()).strip())
        return list(set(orgs))

    def _extract_all_locations(self, root: Any, ns: dict[str, str]) -> list[str]:
        """Extract all location mentions."""
        locations = []
        for loc in root.findall(".//tei:placeName", ns):
            locations.append(" ".join(loc.itertext()).strip())
        for country in root.findall(".//tei:country", ns):
            locations.append(" ".join(country.itertext()).strip())
        return list(set(locations))

    def _extract_all_citations(self, root: Any, ns: dict[str, str]) -> list[dict[str, Any]]:
        """Extract all citations with full metadata."""
        citations = []
        for bibl in root.findall(".//tei:listBibl//tei:biblStruct", ns):
            authors_list: list[str] = []
            for author in bibl.findall(".//tei:author", ns):
                authors_list.append(" ".join(author.itertext()).strip())

            citation = {
                "title": self._extract_text(bibl, ".//tei:title", ns),
                "authors": authors_list,
                "year": self._extract_text(bibl, ".//tei:date", ns),
                "doi": self._extract_text(bibl, './/tei:idno[@type="DOI"]', ns),
                "journal": self._extract_text(bibl, ".//tei:monogr/tei:title", ns),
                "raw_text": " ".join(bibl.itertext()).strip(),
            }

            citations.append(citation)
        return citations

    def _extract_all_figures(self, root: Any, ns: dict[str, str]) -> list[dict[str, str]]:
        """Extract all figures with captions."""
        figures = []
        for fig in root.findall('.//tei:figure[@type="figure"]', ns):
            figure_data = {
                "label": self._extract_text(fig, ".//tei:label", ns),
                "caption": self._extract_text(fig, ".//tei:figDesc", ns),
                "id": fig.get("{http://www.w3.org/XML/1998/namespace}id", ""),
            }
            figures.append(figure_data)
        return figures

    def _extract_all_tables(self, root: Any, ns: dict[str, str]) -> list[dict[str, str]]:
        """Extract all tables with captions."""
        tables = []
        for table in root.findall('.//tei:figure[@type="table"]', ns):
            table_data = {
                "label": self._extract_text(table, ".//tei:label", ns),
                "caption": self._extract_text(table, ".//tei:figDesc", ns),
                "content": self._extract_text(table, ".//tei:table", ns),
                "id": table.get("{http://www.w3.org/XML/1998/namespace}id", ""),
            }
            tables.append(table_data)
        return tables

    def _extract_all_equations(self, root: Any, ns: dict[str, str]) -> list[str]:
        """Extract all equations."""
        equations = []
        for formula in root.findall(".//tei:formula", ns):
            equations.append(" ".join(formula.itertext()).strip())
        return equations

    def _extract_software_mentions(self, root: Any, ns: dict[str, str]) -> list[str]:
        """Extract software mentions using patterns."""
        text = " ".join(root.itertext())
        import re

        # Common software patterns
        patterns = [
            r"(?:using|with|via|through)\s+([A-Z][A-Za-z0-9\+\-\.]+)(?:\s+v?[\d\.]+)?",
            r"([A-Z]+[A-Za-z]*)\s+(?:software|package|library|tool)",
            r"(?:R|Python|MATLAB|SPSS|SAS|Stata)\s+(?:package|library)?\s*([A-Za-z0-9_]+)",
        ]

        software = set()
        for pattern in patterns:
            matches = re.findall(pattern, text)
            software.update(matches)

        return list(software)

    def _extract_dataset_mentions(self, root: Any, ns: dict[str, str]) -> list[str]:
        """Extract dataset mentions."""
        text = " ".join(root.itertext())
        import re

        # Dataset patterns
        patterns = [
            r"(?:dataset|database|corpus|repository)[\s:]+([A-Za-z0-9\-_]+)",
            r"(GSE\d+|GEO\d+|TCGA-[A-Z]+)",  # Common bio databases
            r"(?:available at|deposited in|from)\s+([A-Za-z0-9\-_]+)\s+(?:database|repository)",
        ]

        datasets = set()
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            datasets.update(matches)

        return list(datasets)

    def _extract_funding(self, root: Any, ns: dict[str, str]) -> list[str]:
        """Extract funding information."""
        funding = []

        # From acknowledgments
        ack = root.find('.//tei:div[@type="acknowledgement"]', ns)
        if ack:
            text = " ".join(ack.itertext())
            import re

            # Grant patterns
            grant_patterns = [
                r"(?:grant|award)[\s#:]+([A-Z0-9\-/]+)",
                r"(?:NIH|NSF|DOE|NASA|DARPA|ERC)[\s\-]?([A-Z0-9\-]+)",
                r"(?:funded|supported)\s+by\s+([^.,;]+)",
            ]
            for pattern in grant_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                funding.extend(matches)

        return list(set(funding))

    def _extract_clinical_trials(self, root: Any, ns: dict[str, str]) -> list[str]:
        """Extract clinical trial identifiers."""
        text = " ".join(root.itertext())
        import re

        # Clinical trial patterns
        patterns = [
            r"(NCT\d{8})",  # ClinicalTrials.gov
            r"(ISRCTN\d{8})",  # ISRCTN registry
            r"(EudraCT[\s\-]?\d{4}[\s\-]?\d{6}[\s\-]?\d{2})",  # EudraCT
        ]

        trials = set()
        for pattern in patterns:
            matches = re.findall(pattern, text)
            trials.update(matches)

        return list(trials)

    def _extract_statistical_values(self, root: Any, ns: dict[str, str]) -> dict[str, list[Any]]:
        """Extract statistical values (p-values, confidence intervals, etc.)."""
        text = " ".join(root.itertext())
        import re

        stats: dict[str, list[Any]] = {
            "p_values": [],
            "confidence_intervals": [],
            "sample_sizes": [],
            "effect_sizes": [],
        }

        # P-values
        p_patterns = [
            r"[pP][\s=<>≤≥]+([0-9]\.[0-9]+(?:[eE][\-+]?\d+)?)",
            r"[pP]-value[s]?[\s:=]+([0-9]\.[0-9]+(?:[eE][\-+]?\d+)?)",
        ]
        for pattern in p_patterns:
            stats["p_values"].extend(re.findall(pattern, text))

        # Confidence intervals
        ci_pattern = r"(?:CI|confidence interval)[:\s]+\[?([0-9\.\-]+)[\s,]+([0-9\.\-]+)\]?"
        stats["confidence_intervals"].extend(re.findall(ci_pattern, text, re.IGNORECASE))

        # Sample sizes
        n_patterns = [
            r"[nN][\s=]+(\d+)",
            r"sample size[\s:=]+(\d+)",
            r"(\d+)\s+(?:participants|subjects|patients)",
        ]
        for pattern in n_patterns:
            stats["sample_sizes"].extend(re.findall(pattern, text))

        return stats

    def _extract_urls(self, root: Any, ns: dict[str, str]) -> list[str]:
        """Extract all URLs."""
        text = " ".join(root.itertext())
        import re

        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        return list(set(re.findall(url_pattern, text)))

    def _extract_emails(self, root: Any, ns: dict[str, str]) -> list[str]:
        """Extract all email addresses."""
        emails = []
        for email in root.findall(".//tei:email", ns):
            emails.append(email.text)
        return list(set(emails))

    def _extract_orcids(self, root: Any, ns: dict[str, str]) -> list[str]:
        """Extract all ORCID IDs."""
        orcids = []
        for orcid in root.findall('.//tei:idno[@type="ORCID"]', ns):
            orcids.append(orcid.text)
        return list(set(orcids))

    def _extract_sections(self, body: Any, ns: dict[str, str]) -> list[dict[str, str]]:
        """Extract all body sections with their content."""
        sections = []

        for div in body.findall(".//tei:div", ns):
            section_data = {}

            # Get section title
            head = div.find("tei:head", ns)
            if head is not None:
                section_title = " ".join(head.itertext()).strip()
                if section_title:
                    section_data["title"] = section_title

            # Get section content - extract ALL paragraphs
            paragraphs = []
            for p in div.findall("tei:p", ns):
                text = " ".join(p.itertext()).strip()
                if text:
                    paragraphs.append(text)

            if paragraphs:
                section_data["text"] = "\n\n".join(paragraphs)

            # Add section if it has either title or content
            if section_data:
                sections.append(section_data)

        return sections

    def _extract_coordinates(self, root: Any, ns: dict[str, str]) -> dict[str, str]:
        """Extract coordinate information for spatial analysis."""
        coordinates = {}

        # Find all elements with coordinates
        for elem in root.findall(".//*[@coords]"):
            elem_id = elem.get("{http://www.w3.org/XML/1998/namespace}id", "")
            if elem_id:
                coordinates[elem_id] = elem.get("coords", "")

        return coordinates

    def process_pdf(self, pdf_path: Path) -> dict[str, Any] | None:
        """Process a single PDF with maximum extraction and save all outputs.

        Returns:
            Dictionary with extraction results and file paths
        """
        pdf_id = pdf_path.stem

        # Skip if already processed (checkpoint recovery)
        if str(pdf_path) in self.processed_files:
            logger.info("Skipping %s (already processed)", pdf_id)
            return None

        paper_dir = self.session_dir / pdf_id
        paper_dir.mkdir(exist_ok=True)

        logger.info("\nProcessing: %s", pdf_id)
        start_time = time.time()

        try:
            # Call Grobid with maximum parameters
            with open(pdf_path, "rb") as f:
                files = {"input": f}

                response = requests.post(
                    f"{self.grobid_url}/api/processFulltextDocument",
                    files=files,
                    data=self.params,
                    timeout=300,
                )

                if response.status_code != config.MIN_SECTION_TEXT_LENGTH:
                    logger.error("Grobid returned status %s", response.status_code)
                    self.stats["failed"] += 1
                    return None

                tei_xml = response.text

            # Save 1: Raw TEI XML
            (paper_dir / f"{pdf_id}_tei.xml").write_text(tei_xml, encoding="utf-8")
            logger.info("  ✓ Saved TEI XML (%.1f KB)", len(tei_xml) / 1024)

            # Extract all entities
            extracted_data = self.extract_all_entities(tei_xml)

            # Save 2: Complete JSON
            with open(paper_dir / f"{pdf_id}_complete.json", "w") as f:
                json.dump(extracted_data, f, indent=2, ensure_ascii=False)
            logger.info("  ✓ Saved complete JSON")

            # Save 3: Entities only
            with open(paper_dir / f"{pdf_id}_entities.json", "w") as f:
                json.dump(extracted_data.get("entities", {}), f, indent=2, ensure_ascii=False)
            logger.info("  ✓ Saved entities JSON")

            # Save 4: Metadata only
            with open(paper_dir / f"{pdf_id}_metadata.json", "w") as f:
                json.dump(extracted_data.get("metadata", {}), f, indent=2, ensure_ascii=False)
            logger.info("  ✓ Saved metadata JSON")

            # Save 5: Sections text
            sections_text = "\n\n".join(
                [f"## {title}\n\n{content}" for title, content in extracted_data.get("sections", {}).items()]
            )
            (paper_dir / f"{pdf_id}_sections.txt").write_text(sections_text, encoding="utf-8")
            logger.info("  ✓ Saved sections text")

            # Save 6: Coordinates (if any)
            if extracted_data.get("coordinates"):
                with open(paper_dir / f"{pdf_id}_coordinates.json", "w") as f:
                    json.dump(extracted_data["coordinates"], f, indent=2)
                logger.info("  ✓ Saved coordinates JSON")

            # Save 7: Statistics
            stats = {
                "extraction_time": time.time() - start_time,
                "file_size": pdf_path.stat().st_size,
                "total_entities": extracted_data.get("statistics", {}).get("total_entities", 0),
                "sections_found": len(extracted_data.get("sections", {})),
                "citations_found": len(extracted_data.get("entities", {}).get("citations", [])),
                "figures_found": len(extracted_data.get("entities", {}).get("figures", [])),
                "tables_found": len(extracted_data.get("entities", {}).get("tables", [])),
            }
            with open(paper_dir / f"{pdf_id}_stats.json", "w") as f:
                json.dump(stats, f, indent=2)
            logger.info("  ✓ Saved statistics")

            # Update global stats
            self.stats["successful"] += 1
            self.stats["total_entities"] += stats["total_entities"]
            self.stats["extraction_times"].append(stats["extraction_time"])

            # Mark as processed and save checkpoint
            self.processed_files.add(str(pdf_path))
            self.save_checkpoint()

            logger.info(
                "  ✓ Completed in %.1fs - %s entities extracted",
                stats["extraction_time"],
                stats["total_entities"],
            )

            return {"pdf_id": pdf_id, "success": True, "stats": stats, "output_dir": str(paper_dir)}

        except Exception as e:
            logger.error("Failed to process %s: %s", pdf_id, e)
            self.stats["failed"] += 1
            return None

    def process_batch(self, pdf_files: list[Path], batch_size: int = 10) -> list[dict[str, Any]]:
        """Process multiple PDFs with progress tracking.

        Args:
            pdf_files: List of PDF file paths
            batch_size: Number of papers to process before saving checkpoint
        """
        self.stats["total_papers"] = len(pdf_files)

        logger.info("\nProcessing %s papers...", len(pdf_files))
        logger.info("Checkpoint recovery enabled - safe to interrupt")

        results = []

        with tqdm(total=len(pdf_files), desc="Processing papers") as pbar:
            for i, pdf_file in enumerate(pdf_files):
                result = self.process_pdf(pdf_file)
                if result:
                    results.append(result)

                pbar.update(1)

                # Save checkpoint every batch_size papers
                if (i + 1) % batch_size == 0:
                    self.save_checkpoint()
                    logger.info("Checkpoint saved at %s papers", i + 1)

                # Add delay to be nice to the Grobid server
                time.sleep(0.5)

        # Final statistics
        self.stats["end_time"] = datetime.now(UTC).isoformat()

        # Save final report
        report_path = self.session_dir / "extraction_report.json"
        with open(report_path, "w") as f:
            json.dump({"stats": self.stats, "results": results}, f, indent=2)

        # Print summary
        logger.info("")
        logger.info("=" * 80)
        logger.info("EXTRACTION COMPLETE")
        logger.info("=" * 80)
        logger.info("Total papers: %s", self.stats["total_papers"])
        logger.info("Successful: %s", self.stats["successful"])
        logger.info("Failed: %s", self.stats["failed"])
        logger.info("Total entities: %s", f"{self.stats['total_entities']:,}")
        if self.stats["extraction_times"]:
            avg_time = sum(self.stats["extraction_times"]) / len(self.stats["extraction_times"])
            logger.info("Avg time per paper: %.1fs", avg_time)
        logger.info("Output directory: %s", self.session_dir)
        logger.info("=" * 80)

        return results


def main() -> None:
    """Main entry point for overnight processing."""
    import argparse

    parser = argparse.ArgumentParser(description="Grobid Overnight Runner - Maximum extraction for research")
    parser.add_argument("--input-dir", type=str, help="Directory containing PDF files")
    parser.add_argument("--input-list", type=str, help="Text file with list of PDF paths")
    parser.add_argument(
        "--output-dir",
        type=str,
        default="grobid_overnight_output",
        help="Output directory (default: grobid_overnight_output)",
    )
    parser.add_argument(
        "--grobid-url",
        type=str,
        default="http://localhost:8070",
        help="Grobid service URL (default: http://localhost:8070)",
    )
    parser.add_argument("--limit", type=int, help="Limit number of papers to process")
    parser.add_argument("--check-only", action="store_true", help="Just check if Grobid is running")

    args = parser.parse_args()

    # Initialize extractor
    extractor = OvernightGrobidExtractor(grobid_url=args.grobid_url, output_dir=args.output_dir)

    # Check Grobid service
    if not extractor.check_grobid_service():
        logger.error("Grobid service not available!")
        logger.error("Please start Grobid with:")
        logger.error("docker run -t --rm -p 8070:8070 lfoppiano/grobid:0.8.1")
        sys.exit(1)

    if args.check_only:
        logger.info("✓ Grobid service is running")
        sys.exit(0)

    # Collect PDF files
    pdf_files = []

    if args.input_list:
        with open(args.input_list) as f:
            for line in f:
                pdf_path = Path(line.strip())
                if pdf_path.exists() and pdf_path.suffix.lower() == ".pdf":
                    pdf_files.append(pdf_path)

    elif args.input_dir:
        input_dir = Path(args.input_dir)
        pdf_files = list(input_dir.glob("**/*.pdf"))

    else:
        # Default: Use Zotero storage
        zotero_storage = Path.home() / "Zotero" / "storage"
        if zotero_storage.exists():
            pdf_files = list(zotero_storage.glob("*/*.pdf"))
            logger.info("Using Zotero storage: %s", zotero_storage)
        else:
            logger.error("No input specified and Zotero storage not found")
            sys.exit(1)

    if not pdf_files:
        logger.error("No PDF files found!")
        sys.exit(1)

    # Apply limit if specified
    if args.limit:
        pdf_files = pdf_files[: args.limit]

    logger.info("Found %s PDF files", len(pdf_files))

    # Estimate time
    estimated_time = len(pdf_files) * 25 / 60  # ~25 seconds per paper
    logger.info("Estimated time: %.1f minutes (%.1f hours)", estimated_time, estimated_time / 60)
    logger.info("This is designed for overnight/weekend processing")

    # Confirm
    response = input("\nProceed with extraction? (yes/no): ")
    if response.lower() != "yes":
        logger.info("Cancelled")
        sys.exit(0)

    # Process papers
    extractor.process_batch(pdf_files)

    logger.info("\n✓ Overnight extraction complete!")
    logger.info("Results saved to: %s", extractor.session_dir)


if __name__ == "__main__":
    main()
