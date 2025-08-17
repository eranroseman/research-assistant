#!/usr/bin/env python3
"""
Test PDF extraction libraries to compare speed and quality
"""

import sqlite3
import sys
import time
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))


def get_test_pdfs(limit=10):
    """Get first N PDFs from Zotero library"""
    zotero_dir = Path.home() / "Zotero"
    db_path = zotero_dir / "zotero.sqlite"
    storage_path = zotero_dir / "storage"

    if not db_path.exists():
        print(f"Error: Zotero database not found at {db_path}")
        sys.exit(1)

    pdfs = []

    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        cursor = conn.cursor()

        query = """
        SELECT 
            parent.key as paper_key,
            child.key as attachment_key
        FROM itemAttachments ia
        JOIN items parent ON ia.parentItemID = parent.itemID
        JOIN items child ON ia.itemID = child.itemID
        WHERE ia.contentType = 'application/pdf'
        LIMIT ?
        """

        cursor.execute(query, (limit,))

        for paper_key, attachment_key in cursor.fetchall():
            pdf_dir = storage_path / attachment_key
            if pdf_dir.exists():
                pdf_files = list(pdf_dir.glob("*.pdf"))
                if pdf_files:
                    pdfs.append((pdf_files[0], f"Paper {paper_key}"))

        conn.close()

    except sqlite3.Error as e:
        print(f"Database error: {e}")
        sys.exit(1)

    return pdfs

def test_pypdfium2(pdf_path):
    """Test pypdfium2 extraction"""
    try:
        import pypdfium2 as pdfium

        start = time.time()
        pdf = pdfium.PdfDocument(str(pdf_path))
        text = ""
        for page in pdf:
            textpage = page.get_textpage()
            text += textpage.get_text_range() + "\n"
            textpage.close()
            page.close()
        pdf.close()
        elapsed = time.time() - start

        return text, elapsed, None
    except Exception as e:
        return None, 0, str(e)

def test_pymupdf(pdf_path):
    """Test PyMuPDF extraction"""
    try:
        import fitz

        start = time.time()
        pdf = fitz.open(str(pdf_path))
        text = ""
        for page in pdf:
            text += page.get_text() + "\n"
        pdf.close()
        elapsed = time.time() - start

        return text, elapsed, None
    except Exception as e:
        return None, 0, str(e)

def test_pdfplumber(pdf_path):
    """Test current pdfplumber extraction"""
    try:
        import pdfplumber

        start = time.time()
        with pdfplumber.open(str(pdf_path)) as pdf:
            text = ""
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        elapsed = time.time() - start

        return text, elapsed, None
    except Exception as e:
        return None, 0, str(e)

def main():
    print("PDF Extraction Library Comparison")
    print("=" * 50)

    # Get test PDFs
    print("\nFetching test PDFs from Zotero...")
    test_pdfs = get_test_pdfs(10)

    if not test_pdfs:
        print("No PDFs found in Zotero library")
        sys.exit(1)

    print(f"Found {len(test_pdfs)} PDFs to test\n")

    # Check which libraries are installed
    libraries = []

    try:
        import pypdfium2
        libraries.append(("pypdfium2", test_pypdfium2))
        print("✓ pypdfium2 installed")
    except ImportError:
        print("✗ pypdfium2 not installed (pip install pypdfium2)")

    try:
        import fitz
        libraries.append(("PyMuPDF", test_pymupdf))
        print("✓ PyMuPDF installed")
    except ImportError:
        print("✗ PyMuPDF not installed (pip install PyMuPDF)")

    try:
        import pdfplumber
        libraries.append(("pdfplumber (current)", test_pdfplumber))
        print("✓ pdfplumber installed")
    except ImportError:
        print("✗ pdfplumber not installed")

    if not libraries:
        print("\nNo PDF libraries installed. Install at least one to test.")
        sys.exit(1)

    print("\n" + "=" * 50)

    # Test each library
    results = {lib[0]: {"times": [], "chars": [], "errors": 0} for lib in libraries}

    for i, (pdf_path, title) in enumerate(test_pdfs, 1):
        print(f"\nPaper {i}/10: {title[:50]}...")
        print(f"File: {pdf_path.name}")

        for lib_name, test_func in libraries:
            text, elapsed, error = test_func(pdf_path)

            if error:
                results[lib_name]["errors"] += 1
                print(f"  {lib_name}: ERROR - {error}")
            else:
                results[lib_name]["times"].append(elapsed)
                results[lib_name]["chars"].append(len(text))
                print(f"  {lib_name}: {elapsed:.3f}s ({len(text):,} chars)")

    # Summary
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)

    for lib_name in results:
        r = results[lib_name]
        if r["times"]:
            avg_time = sum(r["times"]) / len(r["times"])
            total_time = sum(r["times"])
            avg_chars = sum(r["chars"]) / len(r["chars"])

            print(f"\n{lib_name}:")
            print(f"  Average time: {avg_time:.3f}s per PDF")
            print(f"  Total time: {total_time:.3f}s")
            print(f"  Average text: {avg_chars:,.0f} characters")
            print(f"  Errors: {r['errors']}/{len(test_pdfs)}")

            # Estimate for full library
            if avg_time > 0:
                est_2000 = (avg_time * 2000) / 60
                print(f"  Estimated for 2000 papers: {est_2000:.1f} minutes")
        else:
            print(f"\n{lib_name}: All extractions failed")

    # Quality comparison (if multiple libraries succeeded)
    successful_libs = [(name, results[name]) for name in results if results[name]["chars"]]

    if len(successful_libs) > 1:
        print("\n" + "=" * 50)
        print("QUALITY COMPARISON")
        print("=" * 50)

        # Compare character counts
        base_lib = successful_libs[0][0]
        base_chars = successful_libs[0][1]["chars"]

        for lib_name, r in successful_libs[1:]:
            if r["chars"] and base_chars:
                diffs = []
                for i in range(min(len(r["chars"]), len(base_chars))):
                    diff_pct = ((r["chars"][i] - base_chars[i]) / base_chars[i]) * 100
                    diffs.append(diff_pct)

                if diffs:
                    avg_diff = sum(diffs) / len(diffs)
                    print(f"\n{lib_name} vs {base_lib}:")
                    print(f"  Average text difference: {avg_diff:+.1f}%")
                    if avg_diff > 5:
                        print(f"  → {lib_name} extracts MORE text")
                    elif avg_diff < -5:
                        print(f"  → {lib_name} extracts LESS text")
                    else:
                        print("  → Similar text extraction")

if __name__ == "__main__":
    main()
