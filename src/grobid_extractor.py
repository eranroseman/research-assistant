#!/usr/bin/env python3
"""GROBID Integration for Academic Paper Section Extraction.

This module provides integration with GROBID (GeneRation Of BIbliographic Data)
for extracting structured sections from academic PDFs.

Prerequisites:
    1. Install Docker: https://docs.docker.com/get-docker/
    2. Run GROBID: docker run -t --rm -p 8070:8070 grobid/grobid:0.8.1
    3. Install client: pip install grobid-client-python

Usage:
    python src/grobid_extractor.py --input /path/to/pdfs --output extracted_sections
    python src/grobid_extractor.py --test-single paper.pdf
"""

import json
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import click
import requests
from tqdm import tqdm


class GROBIDExtractor:
    """Extract sections from PDFs using GROBID service."""

    def __init__(self, grobid_url: str = "http://localhost:8070", timeout: int = 60):
        """Initialize GROBID extractor.

        Args:
            grobid_url: URL of GROBID service
            timeout: Request timeout in seconds
        """
        self.grobid_url = grobid_url.rstrip("/")
        self.timeout = timeout
        self.api_base = f"{self.grobid_url}/api"

        # Check if GROBID is running
        if not self.check_service():
            raise ConnectionError(
                f"GROBID service not available at {self.grobid_url}\n"
                "Please start GROBID with: docker run -t --rm -p 8070:8070 grobid/grobid:0.8.1"
            )

    def check_service(self) -> bool:
        """Check if GROBID service is running.

        Returns:
            True if service is available
        """
        try:
            response = requests.get(f"{self.grobid_url}/api/isalive", timeout=5)
            return response.status_code == 200
        except Exception:
            return False

    def process_pdf(self, pdf_path: Path) -> dict[str, Any]:
        """Process a single PDF using GROBID.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Dictionary with extracted sections
        """
        # Read PDF file
        with open(pdf_path, "rb") as f:
            files = {"input": (pdf_path.name, f, "application/pdf")}

            # Process with GROBID fulltext service
            # Options: consolidateHeader=1 improves metadata,
            #          segmentSentences=1 for sentence segmentation
            data = {
                "consolidateHeader": "1",
                "segmentSentences": "1",
                "teiCoordinates": "0",  # Don't need coordinates for text extraction
            }

            try:
                response = requests.post(
                    f"{self.api_base}/processFulltextDocument", files=files, data=data, timeout=self.timeout
                )

                if response.status_code == 200:
                    return self.parse_tei_xml(response.text, pdf_path.name)
                return {"error": f"GROBID returned status {response.status_code}", "filename": pdf_path.name}

            except requests.RequestException as e:
                return {"error": f"Request failed: {e}", "filename": pdf_path.name}

    def parse_tei_xml(self, xml_content: str, filename: str) -> dict[str, Any]:
        """Parse TEI XML response from GROBID.

        Args:
            xml_content: TEI XML string from GROBID
            filename: Original filename for reference

        Returns:
            Dictionary with parsed sections
        """
        try:
            root = ET.fromstring(xml_content)

            # Define namespace
            ns = {"tei": "http://www.tei-c.org/ns/1.0"}

            result = {"filename": filename, "sections": {}, "metadata": {}}

            # Extract metadata
            title_elem = root.find(".//tei:titleStmt/tei:title", ns)
            if title_elem is not None and title_elem.text:
                result["metadata"]["title"] = title_elem.text.strip()

            # Extract authors
            authors = []
            for author in root.findall(".//tei:fileDesc//tei:author", ns):
                name_parts = []
                for name in author.findall(".//tei:persName/*", ns):
                    if name.text:
                        name_parts.append(name.text.strip())
                if name_parts:
                    authors.append(" ".join(name_parts))
            if authors:
                result["metadata"]["authors"] = authors

            # Extract abstract
            abstract = root.find(".//tei:profileDesc/tei:abstract", ns)
            if abstract is not None:
                abstract_text = self._extract_text_from_element(abstract)
                if abstract_text:
                    result["sections"]["abstract"] = abstract_text

            # Extract body sections
            body = root.find(".//tei:text/tei:body", ns)
            if body is not None:
                for div in body.findall(".//tei:div", ns):
                    # Get section heading
                    head = div.find("tei:head", ns)
                    if head is not None and head.text:
                        section_name = head.text.strip().lower()

                        # Map to standard section names
                        section_map = {
                            "introduction": "introduction",
                            "background": "introduction",
                            "related work": "related_work",
                            "literature review": "literature_review",
                            "method": "methods",
                            "methods": "methods",
                            "methodology": "methods",
                            "materials and methods": "methods",
                            "experimental setup": "methods",
                            "result": "results",
                            "results": "results",
                            "findings": "results",
                            "experiments": "results",
                            "discussion": "discussion",
                            "conclusion": "conclusion",
                            "conclusions": "conclusion",
                            "future work": "future_work",
                        }

                        # Get mapped name or use original
                        mapped_name = section_map.get(section_name, section_name.replace(" ", "_"))

                        # Extract section text
                        section_text = self._extract_text_from_element(div)
                        if section_text:
                            result["sections"][mapped_name] = section_text

            # Extract references count
            refs = root.findall(".//tei:listBibl/tei:biblStruct", ns)
            result["metadata"]["reference_count"] = len(refs)

            return result

        except ET.ParseError as e:
            return {"error": f"XML parsing failed: {e}", "filename": filename}

    def _extract_text_from_element(self, element) -> str:
        """Extract all text from an XML element.

        Args:
            element: XML element

        Returns:
            Concatenated text content
        """
        text_parts = []

        # Get text from current element
        if element.text:
            text_parts.append(element.text.strip())

        # Get text from all child elements
        for child in element:
            child_text = self._extract_text_from_element(child)
            if child_text:
                text_parts.append(child_text)
            # Get tail text (text after child element)
            if child.tail:
                text_parts.append(child.tail.strip())

        return " ".join(text_parts)

    def process_directory(
        self, input_dir: Path, output_dir: Path, limit: int | None = None
    ) -> dict[str, Any]:
        """Process all PDFs in a directory.

        Args:
            input_dir: Directory containing PDFs
            output_dir: Directory for output files
            limit: Maximum number of PDFs to process

        Returns:
            Processing statistics
        """
        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)

        # Find all PDFs
        pdf_files = list(input_dir.glob("*.pdf"))
        if limit:
            pdf_files = pdf_files[:limit]

        stats = {"total": len(pdf_files), "successful": 0, "failed": 0, "sections_extracted": {}}

        results = []

        print(f"Processing {len(pdf_files)} PDFs with GROBID...")

        for pdf_file in tqdm(pdf_files, desc="Extracting sections"):
            result = self.process_pdf(pdf_file)

            if "error" not in result:
                stats["successful"] += 1

                # Count sections
                for section in result.get("sections", {}).keys():
                    stats["sections_extracted"][section] = stats["sections_extracted"].get(section, 0) + 1

                # Save individual result
                output_file = output_dir / f"{pdf_file.stem}_sections.json"
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)

            else:
                stats["failed"] += 1

            results.append(result)

            # Small delay to avoid overwhelming the service
            time.sleep(0.1)

        # Save summary
        summary_file = output_dir / "extraction_summary.json"
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump({"stats": stats, "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")}, f, indent=2)

        return stats


def print_usage_instructions():
    """Print instructions for setting up and using GROBID."""
    instructions = """
    ╔══════════════════════════════════════════════════════════════╗
    ║                 GROBID SETUP INSTRUCTIONS                     ║
    ╚══════════════════════════════════════════════════════════════╝

    1. INSTALL DOCKER (if not already installed):
       - Linux: https://docs.docker.com/engine/install/
       - Windows: https://docs.docker.com/desktop/install/windows/
       - Mac: https://docs.docker.com/desktop/install/mac/

    2. START GROBID SERVICE:
       docker run -t --rm -p 8070:8070 grobid/grobid:0.8.1

       For GPU support (Linux only):
       docker run -t --rm --gpus all -p 8070:8070 grobid/grobid:0.8.1

    3. TEST SERVICE:
       Open http://localhost:8070 in your browser

    4. RUN THIS SCRIPT:
       python src/grobid_extractor.py --help

    ═══════════════════════════════════════════════════════════════
    """
    print(instructions)


@click.command()
@click.option(
    "--input", "input_path", type=click.Path(exists=True, path_type=Path), help="Input PDF file or directory"
)
@click.option(
    "--output",
    "output_path",
    type=click.Path(path_type=Path),
    default="grobid_output",
    help="Output directory for extracted sections",
)
@click.option("--grobid-url", default="http://localhost:8070", help="GROBID service URL")
@click.option("--limit", type=int, help="Maximum number of PDFs to process")
@click.option(
    "--test-single", type=click.Path(exists=True, path_type=Path), help="Test with a single PDF file"
)
@click.option("--setup-help", is_flag=True, help="Show GROBID setup instructions")
def main(input_path, output_path, grobid_url, limit, test_single, setup_help):
    """Extract sections from academic PDFs using GROBID."""
    if setup_help:
        print_usage_instructions()
        return None

    try:
        extractor = GROBIDExtractor(grobid_url=grobid_url)
    except ConnectionError as e:
        click.echo(f"❌ {e}", err=True)
        print_usage_instructions()
        return 1

    click.echo(f"✅ GROBID service connected at {grobid_url}")

    if test_single:
        # Test with single file
        click.echo(f"\nTesting with: {test_single}")
        result = extractor.process_pdf(Path(test_single))

        if "error" in result:
            click.echo(f"❌ Error: {result['error']}")
        else:
            click.echo("✅ Successfully extracted sections:")
            for section, content in result.get("sections", {}).items():
                click.echo(f"  - {section}: {len(content)} characters")

            # Save result
            output_dir = Path(output_path)
            output_dir.mkdir(parents=True, exist_ok=True)
            output_file = output_dir / f"{Path(test_single).stem}_sections.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            click.echo(f"\n📁 Saved to: {output_file}")

    elif input_path:
        # Process directory or file
        input_path = Path(input_path)
        output_path = Path(output_path)

        if input_path.is_file():
            # Single file
            result = extractor.process_pdf(input_path)
            output_path.mkdir(parents=True, exist_ok=True)
            output_file = output_path / f"{input_path.stem}_sections.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            click.echo(f"✅ Saved to: {output_file}")

        else:
            # Directory
            stats = extractor.process_directory(input_path, output_path, limit)

            click.echo("\n" + "=" * 50)
            click.echo("EXTRACTION COMPLETE")
            click.echo("=" * 50)
            click.echo(f"Total PDFs: {stats['total']}")
            click.echo(
                f"Successful: {stats['successful']} ({stats['successful'] / stats['total'] * 100:.1f}%)"
            )
            click.echo(f"Failed: {stats['failed']}")

            if stats["sections_extracted"]:
                click.echo("\nSections extracted:")
                for section, count in sorted(stats["sections_extracted"].items()):
                    percentage = count / stats["successful"] * 100 if stats["successful"] > 0 else 0
                    click.echo(f"  {section}: {count} ({percentage:.1f}%)")

            click.echo(f"\n📁 Results saved to: {output_path}")
    else:
        click.echo("Please provide --input or --test-single option")
        click.echo("Use --help for more information")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
