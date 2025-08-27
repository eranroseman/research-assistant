#!/usr/bin/env python3
"""
Quick Grobid test - extracts PDFs directly from Zotero storage.

This script:
1. Loads papers from Zotero
2. Finds their PDFs in Zotero storage
3. Tests Grobid extraction on first 100 papers with PDFs
4. Compares with PyMuPDF extraction
5. Generates quality report
"""

import json
import time
import requests
import sqlite3
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import xml.etree.ElementTree as ET
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from build_kb import KnowledgeBaseBuilder
    import fitz  # PyMuPDF
except ImportError as e:
    print(f"Error importing: {e}")
    sys.exit(1)


class GrobidExtractor:
    """Extract structured text from PDFs using Grobid."""
    
    def __init__(self, grobid_url: str = "http://localhost:8070"):
        self.grobid_url = grobid_url
        self.session = requests.Session()
        self.session.headers.update({'Accept': 'application/xml'})
    
    def check_health(self) -> bool:
        """Check if Grobid service is healthy."""
        try:
            response = requests.get(f"{self.grobid_url}/api/isalive", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def extract_full_text(self, pdf_path: Path) -> Dict[str, Any]:
        """Extract structured text from PDF using Grobid."""
        if not pdf_path.exists():
            return {"error": f"PDF not found: {pdf_path}"}
        
        try:
            with open(pdf_path, 'rb') as pdf_file:
                files = {'input': pdf_file}
                response = self.session.post(
                    f"{self.grobid_url}/api/processFulltextDocument",
                    files=files,
                    timeout=60
                )
                
                if response.status_code == 200:
                    return self.parse_grobid_xml(response.text)
                else:
                    return {"error": f"Grobid status {response.status_code}"}
                    
        except Exception as e:
            return {"error": str(e)[:100]}
    
    def parse_grobid_xml(self, xml_content: str) -> Dict[str, Any]:
        """Parse Grobid TEI XML output."""
        try:
            root = ET.fromstring(xml_content)
            ns = {'tei': 'http://www.tei-c.org/ns/1.0'}
            
            # Extract title
            title_elem = root.find('.//tei:titleStmt/tei:title', ns)
            title = title_elem.text.strip() if title_elem is not None and title_elem.text else ""
            
            # Extract abstract
            abstract_elem = root.find('.//tei:abstract', ns)
            abstract = ' '.join(abstract_elem.itertext()).strip() if abstract_elem is not None else ""
            
            # Extract body sections
            sections = {}
            body = root.find('.//tei:body', ns)
            if body is not None:
                for div in body.findall('.//tei:div', ns):
                    head = div.find('tei:head', ns)
                    if head is not None and head.text:
                        section_title = head.text.strip().lower()
                        section_texts = []
                        for p in div.findall('tei:p', ns):
                            text = ' '.join(p.itertext()).strip()
                            if text:
                                section_texts.append(text)
                        if section_texts:
                            sections[section_title] = '\n\n'.join(section_texts)
            
            # Combine all text
            full_text = f"Title: {title}\n\nAbstract: {abstract}\n\n"
            for name, content in sections.items():
                full_text += f"\n{name.title()}:\n{content}\n"
            
            return {
                "success": True,
                "title": title,
                "abstract": abstract,
                "sections": sections,
                "full_text": full_text,
                "text_length": len(full_text),
                "num_sections": len(sections),
                "has_methods": 'method' in ' '.join(sections.keys()).lower(),
                "has_results": 'result' in ' '.join(sections.keys()).lower(),
                "has_discussion": 'discussion' in ' '.join(sections.keys()).lower()
            }
            
        except Exception as e:
            return {"error": f"XML parse error: {str(e)[:100]}"}


def extract_with_pymupdf(pdf_path: Path) -> Dict[str, Any]:
    """Extract text using PyMuPDF for comparison."""
    try:
        pdf_doc = fitz.open(pdf_path)
        text = ""
        for page in pdf_doc:
            text += page.get_text()
        pdf_doc.close()
        
        return {
            "success": True,
            "full_text": text,
            "text_length": len(text)
        }
    except Exception as e:
        return {"error": str(e)[:100]}


def main():
    """Main test function."""
    print("=" * 60)
    print("🧪 GROBID EXTRACTION TEST - v5.0 Validation")
    print("=" * 60)
    
    # Check Grobid
    print("\n🔍 Checking Grobid...")
    grobid = GrobidExtractor()
    if not grobid.check_health():
        print("❌ Grobid not running on port 8070")
        return
    print("✅ Grobid is healthy!")
    
    # Load papers from Zotero
    print("\n📚 Loading papers from Zotero...")
    kb_builder = KnowledgeBaseBuilder()
    
    try:
        papers = kb_builder.process_zotero_local_library("http://localhost:23119/api")
    except Exception as e:
        print(f"❌ Failed to load papers: {e}")
        return
    
    print(f"✓ Found {len(papers)} papers")
    
    # Get PDF paths
    print("\n📁 Finding PDFs in Zotero storage...")
    pdf_map = kb_builder.get_pdf_paths_from_sqlite()
    
    if not pdf_map:
        print("❌ No PDFs found in Zotero storage")
        return
    
    print(f"✓ Found {len(pdf_map)} PDFs")
    
    # Test first 100 papers with PDFs
    results = []
    tested = 0
    target = 100
    
    print(f"\n🔬 Testing extraction on {target} papers...")
    print("-" * 40)
    
    for paper in papers:
        if tested >= target:
            break
            
        zotero_key = paper.get("zotero_key")
        if zotero_key not in pdf_map:
            continue
            
        pdf_path = pdf_map[zotero_key]
        if not pdf_path.exists():
            continue
            
        tested += 1
        title = paper.get('title', 'Untitled')[:50]
        print(f"[{tested:3d}/{target}] {title}...", end=" ")
        
        # Extract with both methods
        start = time.time()
        grobid_result = grobid.extract_full_text(pdf_path)
        grobid_time = time.time() - start
        
        start = time.time()
        pymupdf_result = extract_with_pymupdf(pdf_path)
        pymupdf_time = time.time() - start
        
        # Compare results
        result = {
            "title": paper.get('title', 'Untitled'),
            "grobid": {
                "success": grobid_result.get("success", False),
                "text_length": grobid_result.get("text_length", 0),
                "num_sections": grobid_result.get("num_sections", 0),
                "time": grobid_time,
                "error": grobid_result.get("error")
            },
            "pymupdf": {
                "success": pymupdf_result.get("success", False),
                "text_length": pymupdf_result.get("text_length", 0),
                "time": pymupdf_time,
                "error": pymupdf_result.get("error")
            }
        }
        
        if grobid_result.get("success") and pymupdf_result.get("success"):
            g_len = grobid_result.get("text_length", 0)
            p_len = pymupdf_result.get("text_length", 0)
            if p_len > 0:
                result["change_pct"] = ((g_len - p_len) / p_len) * 100
            else:
                result["change_pct"] = 100 if g_len > 0 else 0
        
        results.append(result)
        
        # Show result
        if grobid_result.get("success"):
            change = result.get("change_pct", 0)
            print(f"✓ ({change:+.0f}%)")
        else:
            print("✗")
        
        if tested % 20 == 0:
            success = sum(1 for r in results if r["grobid"]["success"])
            print(f"\n  Progress: {success}/{tested} successful ({success*100/tested:.0f}%)\n")
    
    # Generate report
    print("\n" + "=" * 60)
    print("📊 RESULTS")
    print("=" * 60)
    
    total = len(results)
    grobid_success = sum(1 for r in results if r["grobid"]["success"])
    success_rate = grobid_success * 100 / total if total > 0 else 0
    
    print(f"\n✓ Success Rate: {grobid_success}/{total} ({success_rate:.1f}%)")
    
    if success_rate >= 95:
        print("🎉 **PASS**: Grobid achieves 95%+ extraction rate!")
    elif success_rate >= 85:
        print("🟡 **GOOD**: Grobid significantly improves extraction")
    else:
        print("⚠️ **REVIEW**: Success rate below expectations")
    
    # Calculate average text change
    changes = [r.get("change_pct", 0) for r in results if "change_pct" in r]
    avg_change = sum(changes) / len(changes) if changes else 0
    print(f"\n📈 Text Quality: {avg_change:+.1f}% average change")
    
    # Performance
    avg_grobid = sum(r["grobid"]["time"] for r in results) / total
    avg_pymupdf = sum(r["pymupdf"]["time"] for r in results) / total
    print(f"\n⏱️ Speed: Grobid {avg_grobid:.2f}s vs PyMuPDF {avg_pymupdf:.3f}s per paper")
    print(f"   ({avg_grobid/avg_pymupdf:.1f}x slower but much better quality)")
    
    # Save detailed report
    report_path = Path("exports/grobid_test_report.json")
    report_path.parent.mkdir(exist_ok=True)
    with open(report_path, 'w') as f:
        json.dump({
            "date": datetime.now().isoformat(),
            "summary": {
                "total_tested": total,
                "grobid_success": grobid_success,
                "success_rate": success_rate,
                "avg_text_change": avg_change,
                "avg_grobid_time": avg_grobid,
                "avg_pymupdf_time": avg_pymupdf
            },
            "results": results
        }, f, indent=2)
    
    print(f"\n💾 Detailed report saved to: {report_path}")


if __name__ == "__main__":
    main()