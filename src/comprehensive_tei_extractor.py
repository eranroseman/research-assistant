#!/usr/bin/env python3
"""Comprehensive TEI XML to JSON extractor that captures ALL information.

This script fixes the critical bug where important metadata (year, journal, keywords, etc.)
was not being extracted from TEI XML files.
"""

from src import config
import json
from defusedxml import ElementTree
from pathlib import Path
from datetime import datetime, UTC
import re
from typing import Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class ComprehensiveTEIExtractor:
    """Extract ALL information from TEI XML files."""

    def __init__(self) -> None:
        """Initialize the TEI extractor with XML namespace."""
        self.ns = {"tei": "http://www.tei-c.org/ns/1.0"}
        self.stats: dict[str, Any] = {"total": 0, "successful": 0, "failed": 0, "fields_extracted": {}}

    def extract_year_from_date(self, date_str: str) -> int | None:
        """Extract year from various date formats."""
        if not date_str:
            return None

        # Try ISO format first (YYYY-MM-DD or YYYY)
        year_match = re.match(r"^(\d{4})", date_str)
        if year_match:
            year = int(year_match.group(1))
            if config.MIN_YEAR_VALID <= year <= datetime.now(UTC).year + 1:
                return year

        # Try finding 4-digit year anywhere
        year_match = re.search(r"\b(19\d{2}|20\d{2})\b", date_str)
        if year_match:
            year = int(year_match.group(1))
            if config.MIN_YEAR_VALID <= year <= datetime.now(UTC).year + 1:
                return year

        return None

    def parse_tei_xml(self, tei_file: Path) -> dict[str, Any]:
        """Comprehensively parse TEI XML to extract ALL information."""
        try:
            tree = ElementTree.parse(tei_file)
            root = tree.getroot()

            data: dict[str, Any] = {"paper_id": tei_file.stem}

            # ============= 1. BASIC METADATA =============

            # Title (multiple sources)
            title = None
            # Try main title first
            title_elem = root.find(".//tei:fileDesc/tei:titleStmt/tei:title", self.ns)
            if title_elem is not None and title_elem.text:
                title = title_elem.text.strip()
            # Fallback to analytic title
            if not title:
                title_elem = root.find(".//tei:analytic/tei:title", self.ns)
                if title_elem is not None and title_elem.text:
                    title = title_elem.text.strip()
            if title:
                data["title"] = title

            # Abstract
            abstract_elem = root.find(".//tei:abstract", self.ns)
            if abstract_elem is not None:
                abstract_text = " ".join(abstract_elem.itertext()).strip()
                if abstract_text:
                    data["abstract"] = abstract_text

            # ============= config.MIN_MATCH_COUNT. DATE/YEAR EXTRACTION =============

            year = None
            date_string = None

            # Try multiple locations for dates
            date_locations = [
                ".//tei:biblStruct//tei:monogr/tei:imprint/tei:date[@when]",
                ".//tei:publicationStmt/tei:date[@when]",
                ".//tei:sourceDesc//tei:date[@when]",
                ".//tei:biblStruct//tei:date[@when]",
            ]

            for location in date_locations:
                date_elem = root.find(location, self.ns)
                if date_elem is not None:
                    when = date_elem.get("when")
                    if when:
                        extracted_year = self.extract_year_from_date(when)
                        if extracted_year:
                            year = extracted_year
                            date_string = when
                            break
                    # Also try text content
                    if date_elem.text:
                        extracted_year = self.extract_year_from_date(date_elem.text)
                        if extracted_year and not year:
                            year = extracted_year
                            date_string = date_elem.text

            if year:
                data["year"] = year
            if date_string:
                data["date"] = date_string

            # ============= config.MAX_RETRIES_DEFAULT. AUTHORS WITH AFFILIATIONS =============

            authors: list[dict[str, Any]] = []
            for author in root.findall(".//tei:fileDesc//tei:author", self.ns):
                author_data: dict[str, Any] = {}

                # Name
                forename = author.find(".//tei:forename", self.ns)
                surname = author.find(".//tei:surname", self.ns)
                if forename is not None and surname is not None:
                    fname = forename.text if forename.text else ""
                    sname = surname.text if surname.text else ""
                    author_data["name"] = f"{fname} {sname}".strip()

                # Email
                email = author.find(".//tei:email", self.ns)
                if email is not None and email.text:
                    author_data["email"] = email.text.strip()

                # ORCID
                orcid = author.find('.//tei:idno[@type="ORCID"]', self.ns)
                if orcid is not None and orcid.text:
                    author_data["orcid"] = orcid.text.strip()

                # Affiliation
                affiliation_data: dict[str, Any] = {}
                affiliation = author.find(".//tei:affiliation", self.ns)
                if affiliation is not None:
                    # Organization name
                    org_name = affiliation.find(".//tei:orgName", self.ns)
                    if org_name is not None and org_name.text:
                        affiliation_data["organization"] = org_name.text.strip()

                    # Department
                    dept = affiliation.find('.//tei:orgName[@type="department"]', self.ns)
                    if dept is not None and dept.text:
                        affiliation_data["department"] = dept.text.strip()

                    # Institution
                    inst = affiliation.find('.//tei:orgName[@type="institution"]', self.ns)
                    if inst is not None and inst.text:
                        affiliation_data["institution"] = inst.text.strip()

                    # Address
                    address_parts = []
                    for addr_elem in affiliation.findall(".//tei:address/*", self.ns):
                        if addr_elem.text:
                            address_parts.append(addr_elem.text.strip())
                    if address_parts:
                        affiliation_data["address"] = ", ".join(address_parts)

                    if affiliation_data:
                        author_data["affiliation"] = affiliation_data

                if author_data:
                    authors.append(author_data)

            if authors:
                data["authors"] = authors

            # ============= 4. IDENTIFIERS =============

            # DOI - try multiple locations
            doi = None
            doi_locations = [
                './/tei:sourceDesc//tei:idno[@type="DOI"]',
                './/tei:biblStruct//tei:idno[@type="DOI"]',
                './/tei:publicationStmt//tei:idno[@type="DOI"]',
            ]

            for location in doi_locations:
                doi_elem = root.find(location, self.ns)
                if doi_elem is not None and doi_elem.text:
                    doi_text = doi_elem.text.strip()
                    # Clean DOI
                    doi_text = re.sub(r"^https?://doi\.org/", "", doi_text)
                    doi_text = re.sub(r"^doi:", "", doi_text, flags=re.IGNORECASE)
                    if doi_text:
                        doi = doi_text
                        break

            if doi:
                data["doi"] = doi

            # Other identifiers
            for idno in root.findall(".//tei:sourceDesc//tei:idno", self.ns):
                id_type = idno.get("type")
                if id_type and idno.text and id_type != "DOI":
                    # Store other identifiers
                    id_key = id_type.lower().replace(" ", "_")
                    data[id_key] = idno.text.strip()

            # ============= config.DEFAULT_MAX_RESULTS. PUBLICATION DETAILS =============

            publication = {}

            # Find monogr element (contains journal/book info)
            # First try sourceDesc (where it SHOULD be)
            monogr = root.find(".//tei:sourceDesc/tei:biblStruct//tei:monogr", self.ns)

            # If not in sourceDesc, check if we can infer from references
            # (Grobid sometimes doesn't extract journal to sourceDesc)
            if monogr is not None:
                # Journal title
                journal = monogr.find('.//tei:title[@level="j"]', self.ns)
                if journal is not None and journal.text:
                    publication["journal"] = journal.text.strip()

                # Book/Proceedings title
                book = monogr.find('.//tei:title[@level="m"]', self.ns)
                if book is not None and book.text:
                    publication["book_title"] = book.text.strip()

                # Meeting/Conference
                meeting = monogr.find(".//tei:meeting", self.ns)
                if meeting is not None:
                    meeting_text = " ".join(meeting.itertext()).strip()
                    if meeting_text:
                        publication["conference"] = meeting_text

                # Publisher
                publisher = monogr.find(".//tei:publisher", self.ns)
                if publisher is not None and publisher.text:
                    publication["publisher"] = publisher.text.strip()

                # Publication place
                pub_place = monogr.find(".//tei:pubPlace", self.ns)
                if pub_place is not None and pub_place.text:
                    publication["publication_place"] = pub_place.text.strip()

                # Imprint details (volume, issue, pages)
                imprint = monogr.find(".//tei:imprint", self.ns)
                if imprint is not None:
                    # Volume
                    volume = imprint.find('.//tei:biblScope[@unit="volume"]', self.ns)
                    if volume is not None and volume.text:
                        publication["volume"] = volume.text.strip()

                    # Issue
                    issue = imprint.find('.//tei:biblScope[@unit="issue"]', self.ns)
                    if issue is not None and issue.text:
                        publication["issue"] = issue.text.strip()

                    # Pages
                    pages = imprint.find('.//tei:biblScope[@unit="page"]', self.ns)
                    if pages is not None:
                        if pages.text:
                            publication["pages"] = pages.text.strip()
                        else:
                            # Try from/to attributes
                            from_page = pages.get("from")
                            to_page = pages.get("to")
                            if from_page and to_page:
                                publication["pages"] = f"{from_page}-{to_page}"
                            elif from_page:
                                publication["pages"] = from_page

            # FALLBACK: If no journal found in sourceDesc, try to infer from references
            # This handles cases where Grobid didn't extract the main article's journal
            if not publication.get("journal"):
                # Look for the most common journal in references (likely self-citations)
                ref_journals: dict[str, int] = {}
                for ref_bibl in root.findall(".//tei:listBibl/tei:biblStruct", self.ns):
                    ref_journal = ref_bibl.find('.//tei:monogr/tei:title[@level="j"]', self.ns)
                    if ref_journal is not None and ref_journal.text:
                        journal_name = ref_journal.text.strip()
                        ref_journals[journal_name] = ref_journals.get(journal_name, 0) + 1

                # If we found journals in references and still no main journal
                if ref_journals and not publication.get("journal"):
                    # Use the most frequently cited journal as a hint
                    most_common = max(ref_journals.items(), key=lambda x: x[1])
                    if (
                        most_common[1] >= config.MIN_MATCH_COUNT
                    ):  # At least config.MIN_MATCH_COUNT citations to same journal
                        publication["journal"] = most_common[0]
                        publication["journal_inferred"] = True

            if publication:
                data["publication"] = publication

            # ============= 6. KEYWORDS =============

            keywords = []
            for term in root.findall(".//tei:keywords/tei:term", self.ns):
                if term.text:
                    keywords.append(term.text.strip())

            if keywords:
                data["keywords"] = keywords

            # ============= 7. FUNDING INFORMATION =============

            funding = []
            for funder in root.findall(".//tei:funder", self.ns):
                if funder.text:
                    funding.append(funder.text.strip())

            # Also check for funding statements in text
            for funding_elem in root.findall('.//tei:div[@type="acknowledgement"]', self.ns):
                funding_text = " ".join(funding_elem.itertext()).strip()
                if (
                    funding_text and len(funding_text) < config.MIN_FULL_TEXT_LENGTH_THRESHOLD
                ):  # Reasonable length
                    funding.append(funding_text)

            if funding:
                data["funding"] = funding

            # ============= 8. SECTIONS WITH FULL TEXT =============

            sections = []
            for div in root.findall(".//tei:text//tei:div", self.ns):
                section_data = {}

                # Section number
                n = div.get("n")
                if n:
                    section_data["number"] = n

                # Section type
                div_type = div.get("type")
                if div_type:
                    section_data["type"] = div_type

                # Section title
                head = div.find("tei:head", self.ns)
                if head is not None:
                    # Get head text and number if present
                    head_n = head.get("n")
                    head_text = head.text if head.text else ""
                    if head_n and head_text:
                        section_data["title"] = f"{head_n}. {head_text}".strip()
                    elif head_text:
                        section_data["title"] = head_text.strip()

                # Extract all paragraphs
                paragraphs = []
                for p in div.findall("tei:p", self.ns):
                    # Get all text including nested elements
                    text = " ".join(p.itertext()).strip()
                    if text:
                        paragraphs.append(text)

                # Combine paragraphs
                if paragraphs:
                    section_data["text"] = "\n\n".join(paragraphs)

                # Only add section if it has content
                if section_data and (section_data.get("text") or section_data.get("title")):
                    sections.append(section_data)

            if sections:
                data["sections"] = sections

            # ============= 9. REFERENCES =============

            references = []
            for bibl in root.findall(".//tei:listBibl/tei:biblStruct", self.ns):
                ref_data = {}

                # Title
                ref_title = bibl.find(".//tei:title", self.ns)
                if ref_title is not None and ref_title.text:
                    ref_data["title"] = ref_title.text.strip()

                # Authors
                ref_authors = []
                for author in bibl.findall(".//tei:author", self.ns):
                    forename = author.find(".//tei:forename", self.ns)
                    surname = author.find(".//tei:surname", self.ns)
                    if forename is not None and surname is not None:
                        name = f"{forename.text or ''} {surname.text or ''}".strip()
                        if name:
                            ref_authors.append(name)

                if ref_authors:
                    ref_data["authors"] = ref_authors

                # Year
                ref_date = bibl.find(".//tei:date[@when]", self.ns)
                if ref_date is not None:
                    when = ref_date.get("when")
                    if when:
                        ref_year = self.extract_year_from_date(when)
                        if ref_year:
                            ref_data["year"] = ref_year

                # DOI
                ref_doi = bibl.find('.//tei:idno[@type="DOI"]', self.ns)
                if ref_doi is not None and ref_doi.text:
                    ref_data["doi"] = ref_doi.text.strip()

                # Journal
                ref_journal = bibl.find('.//tei:monogr/tei:title[@level="j"]', self.ns)
                if ref_journal is not None and ref_journal.text:
                    ref_data["journal"] = ref_journal.text.strip()

                # Volume, Issue, Pages
                ref_imprint = bibl.find(".//tei:monogr/tei:imprint", self.ns)
                if ref_imprint is not None:
                    vol = ref_imprint.find('.//tei:biblScope[@unit="volume"]', self.ns)
                    if vol is not None and vol.text:
                        ref_data["volume"] = vol.text.strip()

                    issue = ref_imprint.find('.//tei:biblScope[@unit="issue"]', self.ns)
                    if issue is not None and issue.text:
                        ref_data["issue"] = issue.text.strip()

                    pages = ref_imprint.find('.//tei:biblScope[@unit="page"]', self.ns)
                    if pages is not None and pages.text:
                        ref_data["pages"] = pages.text.strip()

                # Raw text fallback
                ref_text = " ".join(bibl.itertext()).strip()
                if ref_text:
                    ref_data["raw"] = ref_text

                if ref_data:
                    references.append(ref_data)

            if references:
                data["references"] = references
                data["num_references"] = len(references)

            # ============= config.DEFAULT_TIMEOUT. FIGURES AND TABLES =============

            # Figures
            figures = []
            for figure in root.findall(".//tei:figure", self.ns):
                fig_data = {}

                # Figure ID/number
                fig_id = figure.get("xml:id") or figure.get("n")
                if fig_id:
                    fig_data["id"] = fig_id

                # Figure type
                fig_type = figure.get("type")
                if fig_type:
                    fig_data["type"] = fig_type

                # Head/Caption
                fig_head = figure.find(".//tei:head", self.ns)
                if fig_head is not None:
                    caption = " ".join(fig_head.itertext()).strip()
                    if caption:
                        fig_data["caption"] = caption

                # Description
                fig_desc = figure.find(".//tei:figDesc", self.ns)
                if fig_desc is not None:
                    desc = " ".join(fig_desc.itertext()).strip()
                    if desc:
                        fig_data["description"] = desc

                if fig_data:
                    figures.append(fig_data)

            if figures:
                data["figures"] = figures
                data["num_figures"] = len(figures)

            # Tables
            tables = []
            for table in root.findall(".//tei:table", self.ns):
                table_data = {}

                # Table ID/number
                table_id = table.get("xml:id") or table.get("n")
                if table_id:
                    table_data["id"] = table_id

                # Table head/caption
                table_head = table.find(".//tei:head", self.ns)
                if table_head is not None:
                    caption = " ".join(table_head.itertext()).strip()
                    if caption:
                        table_data["caption"] = caption

                # Table content (simplified)
                table_text = " ".join(table.itertext()).strip()
                if table_text and len(table_text) < config.LONG_TEXT_THRESHOLD:  # Reasonable size
                    table_data["content"] = table_text

                if table_data:
                    tables.append(table_data)

            if tables:
                data["tables"] = tables
                data["num_tables"] = len(tables)

            # ============= 11. ADDITIONAL METADATA =============

            # Language
            lang = root.get("{http://www.w3.org/XML/1998/namespace}lang")
            if lang:
                data["language"] = lang

            # License/Availability
            availability = root.find(".//tei:availability", self.ns)
            if availability is not None:
                license_text = " ".join(availability.itertext()).strip()
                if license_text:
                    data["license"] = license_text
                    # Also extract license type if specified
                    status = availability.get("status")
                    if status:
                        data["license_type"] = status

            # Formulas/Equations
            formulas = []
            for formula in root.findall(".//tei:formula", self.ns):
                formula_data = {}
                formula_id = formula.get("xml:id") or formula.get("n")
                if formula_id:
                    formula_data["id"] = formula_id

                formula_text = " ".join(formula.itertext()).strip()
                if formula_text:
                    formula_data["text"] = formula_text

                # Check for notation type
                notation = formula.get("notation")
                if notation:
                    formula_data["notation"] = notation

                if formula_data:
                    formulas.append(formula_data)

            if formulas:
                data["formulas"] = formulas
                data["num_formulas"] = len(formulas)

            # Citations in text (references to bibliography)
            citations = root.findall('.//tei:text//tei:ref[@type="bibr"]', self.ns)
            if citations:
                data["num_citations"] = len(citations)
                # Extract unique cited references
                cited_refs = set()
                for ref in citations:
                    target = ref.get("target")
                    if target:
                        cited_refs.add(target.replace("#", ""))
                if cited_refs:
                    data["cited_references"] = list(cited_refs)

            # Note/Comments
            notes = []
            for note in root.findall(".//tei:note", self.ns):
                note_text = " ".join(note.itertext()).strip()
                note_type = note.get("type")
                if note_text and len(note_text) < config.LARGE_BATCH_SIZE:  # Reasonable size
                    if note_type:
                        notes.append(f"[{note_type}] {note_text}")
                    else:
                        notes.append(note_text)

            if notes:
                data["notes"] = notes

            # Editor information
            editors = []
            for editor in root.findall(".//tei:editor", self.ns):
                editor_name = " ".join(editor.itertext()).strip()
                if editor_name:
                    editors.append(editor_name)

            if editors:
                data["editors"] = editors

            # Series information
            series = root.find(".//tei:series", self.ns)
            if series is not None:
                series_title = series.find(".//tei:title", self.ns)
                if series_title is not None and series_title.text:
                    data["series"] = series_title.text.strip()

            # Edition information
            edition = root.find(".//tei:edition", self.ns)
            if edition is not None and edition.text:
                data["edition"] = edition.text.strip()

            # Application info (software used for processing)
            app_info = {}
            for app in root.findall(".//tei:appInfo/tei:application", self.ns):
                app_name = app.get("ident")
                app_version = app.get("version")
                if app_name:
                    app_info[app_name] = app_version or "unknown"

            if app_info:
                data["processing_software"] = app_info

            # Update stats
            for key in data:
                if key not in self.stats["fields_extracted"]:
                    self.stats["fields_extracted"][key] = 0
                self.stats["fields_extracted"][key] += 1

            return data

        except Exception as e:
            logger.error("Error parsing %s: %s", tei_file, e)
            return {"paper_id": tei_file.stem, "parse_error": str(e)}

    def process_directory(self, tei_dir: Path, output_dir: Path) -> None:
        """Process all TEI XML files in a directory."""
        tei_files = list(tei_dir.glob("*.xml"))
        logger.info("Found %d TEI XML files", len(tei_files))

        output_dir.mkdir(exist_ok=True, parents=True)

        for i, tei_file in enumerate(tei_files, 1):
            if i % config.MIN_CONTENT_LENGTH == 0:
                logger.info("Processing %d/%d...", i, len(tei_files))

            self.stats["total"] += 1

            # Extract data
            data = self.parse_tei_xml(tei_file)

            if "parse_error" in data:
                self.stats["failed"] += 1
                logger.error("Failed: %s", tei_file.name)
            else:
                self.stats["successful"] += 1

            # Save JSON
            output_file = output_dir / f"{tei_file.stem}.json"
            with open(output_file, "w") as f:
                json.dump(data, f, indent=2)

        # Print summary
        self.print_summary()

    def print_summary(self) -> None:
        """Print extraction summary."""
        print("\n" + "=" * 70)
        print("EXTRACTION COMPLETE")
        print("=" * 70)
        print(f"Total files: {self.stats['total']}")
        print(f"Successful: {self.stats['successful']}")
        print(f"Failed: {self.stats['failed']}")

        print("\nFields extracted (coverage):")
        for field, count in sorted(self.stats["fields_extracted"].items()):
            coverage = (
                count / self.stats["successful"] * config.MIN_CONTENT_LENGTH
                if self.stats["successful"] > 0
                else 0
            )
            print(f"  {field}: {count} ({coverage:.1f}%)")


def main() -> None:
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Comprehensive TEI XML to JSON extractor")
    parser.add_argument(
        "--input-dir",
        type=str,
        default="zotero_extraction_20250830_235521/tei_xml",
        help="Input directory with TEI XML files",
    )
    parser.add_argument("--output-dir", type=str, default=None, help="Output directory for JSON files")

    args = parser.parse_args()

    # Set output directory
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        output_dir = Path(f"comprehensive_extraction_{timestamp}")

    # Process files
    extractor = ComprehensiveTEIExtractor()
    extractor.process_directory(Path(args.input_dir), output_dir)

    print(f"\n✅ Output saved to: {output_dir}")
    print("\n📊 Next steps:")
    print(
        f"1. Review extracted data: ls {output_dir}/*.json | head | xargs -I {{}} python -m json.tool {{}} | head -50"
    )
    print(f"2. Run CrossRef enrichment: python crossref_enrichment.py --input {output_dir}")
    print(f"3. Build KB: python src/build_kb.py --input {output_dir}")


if __name__ == "__main__":
    main()
