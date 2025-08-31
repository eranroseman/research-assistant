#!/usr/bin/env python3
"""Extract entire Zotero library with Grobid
Uses consolidation=2 (biblio-glutton) for maximum enrichment with minimal overhead

Aug 2025 - Based on Azure testing showing <1s overhead for biblio-glutton
"""

import json
import time
import requests
from pathlib import Path
from datetime import datetime
import xml.etree.ElementTree as ET
import sys
import traceback


class ZoteroGrobidExtractor:
    """Extract all PDFs from Zotero library using Grobid with maximum extraction"""

    def __init__(
        self, grobid_url: str = "http://localhost:8070", output_dir: Path | None = None, max_workers: int = 1
    ):
        """Initialize extractor

        Args:
            grobid_url: Grobid service URL
            output_dir: Output directory (defaults to timestamped folder)
            max_workers: Number of parallel workers (1 is safest for Grobid)
        """
        self.grobid_url = grobid_url
        self.max_workers = max_workers

        # Create output directory
        if output_dir is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.output_dir = Path(f"zotero_extraction_{timestamp}")
        else:
            self.output_dir = Path(output_dir)

        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Create subdirectories
        (self.output_dir / "tei_xml").mkdir(exist_ok=True)
        (self.output_dir / "json").mkdir(exist_ok=True)
        (self.output_dir / "errors").mkdir(exist_ok=True)

        # Maximum extraction parameters (consolidation=2 for biblio-glutton)
        self.grobid_params = {
            "consolidateHeader": "2",  # Biblio-glutton - tested <1s overhead
            "consolidateCitations": "2",  # Full citation enrichment
            "consolidateFunders": "1",  # Extract funding
            "processFigures": "1",  # Extract figures
            "processTables": "1",  # Extract tables
            "processEquations": "1",  # Extract equations
            "segmentSentences": "1",  # Sentence segmentation
            "includeRawCitations": "1",  # Raw citation strings
            "includeRawAffiliations": "1",  # Raw affiliations
            "includeRawAuthors": "1",  # Raw authors
            "includeRawCopyrights": "1",  # Raw copyrights
            "teiCoordinates": "all",  # All coordinates
            "generateIDs": "1",  # Generate IDs
            "addElementId": "1",  # Add element IDs
            "timeout": 120,  # 2 minute timeout
        }

        # Tracking
        self.stats = {
            "total_pdfs": 0,
            "processed": 0,
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "total_time": 0,
            "times": [],
        }

        # Checkpoint file for resuming
        self.checkpoint_file = self.output_dir / "checkpoint.json"
        self.processed_files = self.load_checkpoint()

    def load_checkpoint(self) -> set:
        """Load checkpoint to resume interrupted processing"""
        if self.checkpoint_file.exists():
            try:
                with open(self.checkpoint_file) as f:
                    data = json.load(f)
                    print(f"Resuming from checkpoint: {len(data['processed'])} already processed")
                    return set(data["processed"])
            except:
                return set()
        return set()

    def save_checkpoint(self):
        """Save checkpoint for resuming"""
        with open(self.checkpoint_file, "w") as f:
            json.dump(
                {
                    "processed": list(self.processed_files),
                    "stats": self.stats,
                    "timestamp": datetime.now().isoformat(),
                },
                f,
                indent=2,
            )

    def find_zotero_pdfs(self) -> list[Path]:
        """Find all PDFs in Zotero storage"""
        zotero_path = Path.home() / "Zotero" / "storage"

        if not zotero_path.exists():
            print(f"❌ Zotero storage not found at: {zotero_path}")
            return []

        # Find all PDFs
        pdf_files = list(zotero_path.glob("*/*.pdf"))

        # Filter out already processed files
        pdf_files = [p for p in pdf_files if str(p) not in self.processed_files]

        print(f"📚 Found {len(pdf_files)} unprocessed PDFs in Zotero library")
        if self.processed_files:
            print(f"   (Skipping {len(self.processed_files)} already processed)")

        return sorted(pdf_files)

    def extract_single_pdf(self, pdf_path: Path) -> tuple[bool, str | None, float]:
        """Extract single PDF with Grobid

        Returns:
            (success, tei_xml, processing_time)
        """
        start_time = time.time()

        try:
            with open(pdf_path, "rb") as f:
                response = requests.post(
                    f"{self.grobid_url}/api/processFulltextDocument",
                    files={"input": f},
                    data=self.grobid_params,
                    timeout=120,
                )

            processing_time = time.time() - start_time

            if response.status_code == 200:
                return True, response.text, processing_time
            error_msg = f"HTTP {response.status_code}"
            self.save_error(pdf_path, error_msg)
            return False, None, processing_time

        except requests.Timeout:
            self.save_error(pdf_path, "Timeout after 120s")
            return False, None, 120
        except Exception as e:
            self.save_error(pdf_path, str(e))
            return False, None, time.time() - start_time

    def save_error(self, pdf_path: Path, error_msg: str):
        """Save error information for failed extraction"""
        error_file = self.output_dir / "errors" / f"{pdf_path.stem}_error.txt"
        error_file.write_text(f"PDF: {pdf_path}\nError: {error_msg}\n")

    def save_extraction_results(self, pdf_path: Path, tei_xml: str, proc_time: float):
        """Save extraction results in multiple formats"""
        pdf_id = pdf_path.parent.name  # Use Zotero folder name as ID

        # Save TEI XML
        xml_file = self.output_dir / "tei_xml" / f"{pdf_id}.xml"
        xml_file.write_text(tei_xml, encoding="utf-8")

        # Parse and save as JSON
        try:
            parsed_data = self.parse_tei_xml(tei_xml)
            parsed_data["_metadata"] = {
                "pdf_path": str(pdf_path),
                "pdf_id": pdf_id,
                "processing_time": proc_time,
                "extraction_date": datetime.now().isoformat(),
            }

            json_file = self.output_dir / "json" / f"{pdf_id}.json"
            json_file.write_text(json.dumps(parsed_data, indent=2), encoding="utf-8")

            # Quick stats
            stats = {
                "has_abstract": bool(parsed_data.get("abstract")),
                "num_authors": len(parsed_data.get("authors", [])),
                "num_references": len(parsed_data.get("references", [])),
                "num_sections": len(parsed_data.get("sections", [])),
                "has_doi": bool(parsed_data.get("doi")),
                "has_pmid": bool(parsed_data.get("pmid")),
            }
            return stats

        except Exception as e:
            print(f"  ⚠️ Failed to parse XML: {e}")
            return {}

    def parse_tei_xml(self, tei_xml: str) -> dict:
        """Parse TEI XML to extract key information"""
        try:
            root = ET.fromstring(tei_xml)
            ns = {"tei": "http://www.tei-c.org/ns/1.0"}

            data = {}

            # Title
            title_elem = root.find(".//tei:titleStmt/tei:title", ns)
            if title_elem is not None and title_elem.text:
                data["title"] = title_elem.text.strip()

            # Abstract
            abstract_elem = root.find(".//tei:abstract", ns)
            if abstract_elem is not None:
                abstract_text = " ".join(abstract_elem.itertext()).strip()
                if abstract_text:
                    data["abstract"] = abstract_text

            # Authors
            authors = []
            for author in root.findall(".//tei:fileDesc//tei:author", ns):
                author_data = {}

                # Name
                forename = author.find(".//tei:forename", ns)
                surname = author.find(".//tei:surname", ns)
                if forename is not None and surname is not None:
                    author_data["name"] = f"{forename.text} {surname.text}"

                # Email
                email = author.find(".//tei:email", ns)
                if email is not None and email.text:
                    author_data["email"] = email.text

                # ORCID
                orcid = author.find('.//tei:idno[@type="ORCID"]', ns)
                if orcid is not None and orcid.text:
                    author_data["orcid"] = orcid.text

                if author_data:
                    authors.append(author_data)

            if authors:
                data["authors"] = authors

            # DOI, PMID, etc.
            for idno in root.findall(".//tei:sourceDesc//tei:idno", ns):
                id_type = idno.get("type")
                if id_type and idno.text:
                    data[id_type.lower()] = idno.text

            # References count
            references = root.findall('.//tei:text//tei:ref[@type="bibr"]', ns)
            data["num_references"] = len(references)

            # Sections
            sections = []
            for div in root.findall(".//tei:text//tei:div", ns):
                head = div.find("tei:head", ns)
                if head is not None and head.text:
                    sections.append(head.text.strip())
            if sections:
                data["sections"] = sections

            return data

        except Exception as e:
            return {"parse_error": str(e)}

    def process_batch(self, pdf_files: list[Path], batch_size: int = 50):
        """Process PDFs in batches with checkpointing"""
        total = len(pdf_files)
        self.stats["total_pdfs"] = total + len(self.processed_files)

        print(f"\n{'=' * 70}")
        print(f"PROCESSING {total} PDFs")
        print(f"{'=' * 70}")
        print(f"Output directory: {self.output_dir}")
        print(f"Grobid URL: {self.grobid_url}")
        print("Configuration: consolidation=2 (biblio-glutton)")
        print(f"{'=' * 70}\n")

        start_time = time.time()

        for i, pdf_path in enumerate(pdf_files, 1):
            # Progress
            print(f"[{i}/{total}] {pdf_path.name[:50]}...", end=" ")

            # Extract
            success, tei_xml, proc_time = self.extract_single_pdf(pdf_path)

            if success and tei_xml:
                # Save results
                stats = self.save_extraction_results(pdf_path, tei_xml, proc_time)

                # Update tracking
                self.stats["successful"] += 1
                self.stats["times"].append(proc_time)
                self.processed_files.add(str(pdf_path))

                # Print result
                print(f"✅ {proc_time:.1f}s", end="")
                if stats:
                    if stats.get("has_doi"):
                        print(" [DOI]", end="")
                    if stats.get("has_pmid"):
                        print(" [PMID]", end="")
                print()
            else:
                self.stats["failed"] += 1
                self.processed_files.add(str(pdf_path))  # Don't retry failures
                print("❌ Failed")

            self.stats["processed"] += 1

            # Save checkpoint every batch_size papers
            if i % batch_size == 0:
                self.save_checkpoint()
                self.print_progress_summary()

        # Final checkpoint
        self.save_checkpoint()

        # Final summary
        self.stats["total_time"] = time.time() - start_time
        self.print_final_summary()

    def print_progress_summary(self):
        """Print progress summary"""
        if self.stats["times"]:
            avg_time = sum(self.stats["times"]) / len(self.stats["times"])
            print(f"\n--- Progress: {self.stats['processed']}/{self.stats['total_pdfs']} processed")
            print(
                f"    Success rate: {self.stats['successful']}/{self.stats['processed']} "
                f"({self.stats['successful'] / self.stats['processed'] * 100:.1f}%)"
            )
            print(f"    Average time: {avg_time:.1f}s per paper")

            # Estimate remaining time
            remaining = self.stats["total_pdfs"] - self.stats["processed"]
            if remaining > 0:
                est_seconds = remaining * avg_time
                est_hours = est_seconds / 3600
                print(f"    Estimated remaining: {est_hours:.1f} hours for {remaining} papers\n")

    def print_final_summary(self):
        """Print final summary"""
        print(f"\n{'=' * 70}")
        print("EXTRACTION COMPLETE")
        print(f"{'=' * 70}")
        print(f"Total PDFs: {self.stats['total_pdfs']}")
        print(f"Processed: {self.stats['processed']}")
        print(f"Successful: {self.stats['successful']}")
        print(f"Failed: {self.stats['failed']}")

        if self.stats["times"]:
            avg_time = sum(self.stats["times"]) / len(self.stats["times"])
            min_time = min(self.stats["times"])
            max_time = max(self.stats["times"])

            print("\nTiming:")
            print(f"  Average: {avg_time:.1f}s per paper")
            print(f"  Min/Max: {min_time:.1f}s / {max_time:.1f}s")
            print(f"  Total: {self.stats['total_time'] / 3600:.1f} hours")

        print(f"\nOutput saved to: {self.output_dir}")
        print(f"  TEI XML files: {self.output_dir}/tei_xml/")
        print(f"  JSON files: {self.output_dir}/json/")
        print(f"  Errors: {self.output_dir}/errors/")

        # Save final stats
        stats_file = self.output_dir / "extraction_stats.json"
        stats_file.write_text(json.dumps(self.stats, indent=2))


def main():
    """Main extraction function"""
    # Check if Grobid is running
    try:
        response = requests.get("http://localhost:8070/api/version", timeout=5)
        if response.status_code == 200:
            print(f"✅ Grobid is running: {response.text.strip()}")
        else:
            print("❌ Grobid is not responding properly")
            print("Start Grobid with: docker run -t --rm -p 8070:8070 grobid/grobid:0.8.2")
            sys.exit(1)
    except Exception:
        print("❌ Grobid is not running on localhost:8070")
        print("Start Grobid with: docker run -t --rm -p 8070:8070 grobid/grobid:0.8.2")
        sys.exit(1)

    # Create extractor
    extractor = ZoteroGrobidExtractor(
        max_workers=1  # Single-threaded is safest for Grobid
    )

    # Find PDFs
    pdf_files = extractor.find_zotero_pdfs()

    if not pdf_files:
        print("No PDFs found to process")
        return

    # Confirm before starting
    print(f"\nReady to process {len(pdf_files)} PDFs")
    print(f"Estimated time: {len(pdf_files) * 18 / 3600:.1f} hours (at ~18s/paper)")

    response = input("\nProceed? (y/n): ")
    if response.lower() != "y":
        print("Aborted")
        return

    # Process all PDFs
    try:
        extractor.process_batch(pdf_files)
    except KeyboardInterrupt:
        print("\n\n⚠️ Interrupted! Progress saved to checkpoint.")
        print(f"Run again to resume from paper {extractor.stats['processed'] + 1}")
        extractor.save_checkpoint()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        traceback.print_exc()
        extractor.save_checkpoint()


if __name__ == "__main__":
    main()
