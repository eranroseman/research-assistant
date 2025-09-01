#!/usr/bin/env python3
"""Raw PDF Text Extractor for Research Assistant.

This script extracts raw text from all PDFs in the Zotero library without any
section division or processing. The extracted text is saved as plain text files
for analysis.

Usage:
    python src/extract_raw_text.py
    python src/extract_raw_text.py --output-dir raw_texts
    python src/extract_raw_text.py --limit 10
"""

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import click
import fitz  # PyMuPDF
from tqdm import tqdm

# Default paths
DEFAULT_ZOTERO_PATH = Path.home() / "Zotero"
DEFAULT_OUTPUT_DIR = Path("raw_texts")


class RawTextExtractor:
    """Extract raw text from PDFs without section processing."""

    def __init__(self, zotero_path: Path | None = None, output_dir: Path | None = None):
        """Initialize the extractor.

        Args:
            zotero_path: Path to Zotero directory (defaults to ~/Zotero)
            output_dir: Directory to save extracted texts (defaults to raw_texts)
        """
        self.zotero_path = Path(zotero_path) if zotero_path else DEFAULT_ZOTERO_PATH
        self.output_dir = Path(output_dir) if output_dir else DEFAULT_OUTPUT_DIR
        self.zotero_db_path = self.zotero_path / "zotero.sqlite"
        self.storage_path = self.zotero_path / "storage"

        # Create output directory if it doesn't exist
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def get_pdf_paths_from_sqlite(self) -> dict[str, Path]:
        """Get mapping of paper keys to PDF file paths from Zotero SQLite database.

        Returns:
            Dictionary mapping Zotero paper keys to PDF file paths
        """
        if not self.zotero_db_path.exists():
            raise FileNotFoundError(f"Zotero database not found at {self.zotero_db_path}")

        pdf_map = {}

        conn = sqlite3.connect(str(self.zotero_db_path))
        cursor = conn.cursor()

        # Query to get PDF attachments for each item
        query = """
        SELECT
            parentItems.key as parent_key,
            attachmentItems.key as attachment_key,
            itemAttachments.path as attachment_path
        FROM items parentItems
        JOIN itemAttachments ON parentItems.itemID = itemAttachments.parentItemID
        JOIN items attachmentItems ON itemAttachments.itemID = attachmentItems.itemID
        WHERE itemAttachments.contentType = 'application/pdf'
        AND parentItems.itemTypeID IN (
            SELECT itemTypeID FROM itemTypes WHERE typeName IN (
                'journalArticle', 'conferencePaper', 'bookSection',
                'book', 'thesis', 'report', 'preprint'
            )
        )
        AND itemAttachments.path IS NOT NULL
        """

        cursor.execute(query)
        results = cursor.fetchall()

        for parent_key, attachment_key, attachment_path in results:
            # Handle different path formats
            if attachment_path.startswith("storage:"):
                # Format: storage:filename
                filename = attachment_path.replace("storage:", "")
                pdf_path = self.storage_path / attachment_key / filename
            else:
                # Absolute or relative path
                pdf_path = Path(attachment_path)
                if not pdf_path.is_absolute():
                    pdf_path = self.storage_path / attachment_key / pdf_path

            if pdf_path.exists():
                # Use the first PDF found for each parent
                if parent_key not in pdf_map:
                    pdf_map[parent_key] = pdf_path

        conn.close()
        return pdf_map

    def get_paper_metadata_from_sqlite(self) -> dict[str, dict[str, Any]]:
        """Get basic metadata for papers from Zotero SQLite database.

        Returns:
            Dictionary mapping paper keys to metadata (title, authors, year)
        """
        if not self.zotero_db_path.exists():
            raise FileNotFoundError(f"Zotero database not found at {self.zotero_db_path}")

        metadata_map = {}

        conn = sqlite3.connect(str(self.zotero_db_path))
        cursor = conn.cursor()

        # Get basic item metadata
        query = """
        SELECT
            items.key,
            COALESCE(itemDataValues.value, '') as title,
            items.dateAdded
        FROM items
        LEFT JOIN itemData ON items.itemID = itemData.itemID
        LEFT JOIN itemDataValues ON itemData.valueID = itemDataValues.valueID
        LEFT JOIN fields ON itemData.fieldID = fields.fieldID
        WHERE items.itemTypeID IN (
            SELECT itemTypeID FROM itemTypes WHERE typeName IN (
                'journalArticle', 'conferencePaper', 'bookSection',
                'book', 'thesis', 'report', 'preprint'
            )
        )
        AND fields.fieldName = 'title'
        """

        cursor.execute(query)
        results = cursor.fetchall()

        for key, title, date_added in results:
            metadata_map[key] = {"key": key, "title": title or "Untitled", "date_added": date_added}

        # Get authors
        query = """
        SELECT
            items.key,
            GROUP_CONCAT(
                creators.firstName || ' ' || creators.lastName,
                ', '
            ) as authors
        FROM items
        LEFT JOIN itemCreators ON items.itemID = itemCreators.itemID
        LEFT JOIN creators ON itemCreators.creatorID = creators.creatorID
        WHERE items.itemTypeID IN (
            SELECT itemTypeID FROM itemTypes WHERE typeName IN (
                'journalArticle', 'conferencePaper', 'bookSection',
                'book', 'thesis', 'report', 'preprint'
            )
        )
        GROUP BY items.key
        """

        cursor.execute(query)
        results = cursor.fetchall()

        for key, authors in results:
            if key in metadata_map:
                metadata_map[key]["authors"] = authors or "Unknown"

        conn.close()
        return metadata_map

    def extract_pdf_text(self, pdf_path: Path) -> str | None:
        """Extract raw text from PDF file.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Extracted text or None if extraction fails
        """
        try:
            pdf = fitz.open(str(pdf_path))
            text = ""
            for page_num, page in enumerate(pdf, 1):
                page_text = page.get_text()
                if page_text:
                    text += f"\n\n--- Page {page_num} ---\n\n"
                    text += page_text
            pdf.close()
            return text.strip() if text else None
        except Exception as e:
            print(f"Error extracting PDF {pdf_path}: {e}")
            return None

    def sanitize_filename(self, text: str, max_length: int = 100) -> str:
        """Sanitize text for use as filename.

        Args:
            text: Text to sanitize
            max_length: Maximum length of filename

        Returns:
            Sanitized filename
        """
        # Remove invalid filename characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            text = text.replace(char, "_")

        # Truncate if too long
        if len(text) > max_length:
            text = text[:max_length]

        # Remove trailing spaces and dots
        text = text.strip(". ")

        return text if text else "untitled"

    def run(self, limit: int | None = None, verbose: bool = True) -> dict[str, Any]:
        """Extract raw text from all PDFs.

        Args:
            limit: Maximum number of PDFs to process (None for all)
            verbose: Show progress bar and detailed output

        Returns:
            Statistics about the extraction process
        """
        stats = {
            "total_papers": 0,
            "papers_with_pdfs": 0,
            "successful_extractions": 0,
            "failed_extractions": 0,
            "extraction_errors": [],
            "timestamp": datetime.now(UTC).isoformat(),
        }

        # Get PDF paths from database
        if verbose:
            print(f"Connecting to Zotero database at {self.zotero_db_path}")
        pdf_map = self.get_pdf_paths_from_sqlite()

        if not pdf_map:
            print("No PDFs found in Zotero database")
            return stats

        # Get metadata for papers
        metadata_map = self.get_paper_metadata_from_sqlite()

        stats["total_papers"] = len(metadata_map)
        stats["papers_with_pdfs"] = len(pdf_map)

        if verbose:
            print(f"Found {len(pdf_map):,} PDFs in {len(metadata_map):,} papers")
            if limit:
                print(f"Processing first {limit} PDFs")

        # Create index file for mapping
        index_data = []

        # Process PDFs
        items_to_process = list(pdf_map.items())
        if limit:
            items_to_process = items_to_process[:limit]

        if verbose:
            pbar = tqdm(items_to_process, desc="Extracting text from PDFs")
        else:
            pbar = items_to_process

        for paper_key, pdf_path in pbar:
            # Get metadata
            metadata = metadata_map.get(paper_key, {})
            title = metadata.get("title", "Untitled")
            authors = metadata.get("authors", "Unknown")

            # Extract text
            text = self.extract_pdf_text(pdf_path)

            if text:
                # Create filename based on title and key
                safe_title = self.sanitize_filename(title)
                filename = f"{paper_key}_{safe_title}.txt"
                output_path = self.output_dir / filename

                # Save text file
                output_path.write_text(text, encoding="utf-8")

                # Add to index
                index_entry = {
                    "key": paper_key,
                    "title": title,
                    "authors": authors,
                    "pdf_path": str(pdf_path),
                    "output_file": filename,
                    "text_length": len(text),
                    "extraction_date": datetime.now(UTC).isoformat(),
                }
                index_data.append(index_entry)

                stats["successful_extractions"] += 1

                if verbose and hasattr(pbar, "set_description"):
                    pbar.set_description(f"Extracted: {safe_title[:50]}")
            else:
                stats["failed_extractions"] += 1
                stats["extraction_errors"].append(
                    {
                        "key": paper_key,
                        "title": title,
                        "pdf_path": str(pdf_path),
                        "error": "Failed to extract text",
                    }
                )

        # Save index file
        index_path = self.output_dir / "extraction_index.json"
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "extraction_date": datetime.now(UTC).isoformat(),
                    "total_files": len(index_data),
                    "papers": index_data,
                },
                f,
                indent=2,
            )

        # Save statistics
        stats_path = self.output_dir / "extraction_stats.json"
        with open(stats_path, "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=2)

        if verbose:
            print("\n✓ Extraction complete:")
            print(f"  - Total papers: {stats['total_papers']:,}")
            print(f"  - Papers with PDFs: {stats['papers_with_pdfs']:,}")
            print(f"  - Successful extractions: {stats['successful_extractions']:,}")
            print(f"  - Failed extractions: {stats['failed_extractions']:,}")
            print(f"  - Output directory: {self.output_dir}")
            print(f"  - Index file: {index_path}")

        return stats


@click.command()
@click.option(
    "--zotero-path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    default=None,
    help="Path to Zotero directory (defaults to ~/Zotero)",
)
@click.option(
    "--output-dir",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    default="raw_texts",
    help="Directory to save extracted texts (defaults to raw_texts)",
)
@click.option("--limit", type=int, default=None, help="Maximum number of PDFs to process (for testing)")
@click.option("--quiet", is_flag=True, help="Suppress progress output")
def main(zotero_path: Path | None, output_dir: Path, limit: int | None, quiet: bool):
    """Extract raw text from all PDFs in Zotero library."""
    try:
        extractor = RawTextExtractor(zotero_path, output_dir)
        stats = extractor.run(limit=limit, verbose=not quiet)

        if stats["failed_extractions"] > 0:
            print(f"\n⚠ Warning: {stats['failed_extractions']} PDFs failed to extract")
            print("Check extraction_stats.json for details")

    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        click.echo("\nMake sure Zotero is installed and the path is correct.", err=True)
        click.echo("Default path: ~/Zotero", err=True)
        click.echo("You can specify a custom path with --zotero-path", err=True)
        return 1
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
