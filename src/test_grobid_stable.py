#!/usr/bin/env python3
"""
Stable Grobid test with proper error handling and smaller batches.
Tests extraction on 20 papers to avoid overwhelming the container.
"""

import json
import time
import requests
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
import xml.etree.ElementTree as ET
import sys

sys.path.insert(0, str(Path(__file__).parent))

try:
    from build_kb import KnowledgeBaseBuilder
    import fitz  # PyMuPDF
except ImportError as e:
    print(f"Error importing: {e}")
    sys.exit(1)


class GrobidExtractor:
    """Extract structured text from PDFs using Grobid with retry logic."""
    
    def __init__(self, grobid_url: str = "http://localhost:8070"):
        self.grobid_url = grobid_url
        # Don't use session to avoid connection pooling issues
    
    def check_health(self) -> bool:
        """Check if Grobid service is healthy."""
        try:
            response = requests.get(f"{self.grobid_url}/api/isalive", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def extract_full_text(self, pdf_path: Path, retry_count: int = 3) -> Dict[str, Any]:
        """Extract structured text from PDF with retries."""
        if not pdf_path.exists():
            return {"error": f"PDF not found"}
        
        for attempt in range(retry_count):
            try:
                # Add delay between attempts
                if attempt > 0:
                    time.sleep(attempt * 2)  # Exponential backoff
                
                with open(pdf_path, 'rb') as pdf_file:
                    files = {'input': pdf_file}
                    
                    # Fresh request each time (no session)
                    response = requests.post(
                        f"{self.grobid_url}/api/processFulltextDocument",
                        files=files,
                        timeout=30  # Shorter timeout
                    )
                    
                    if response.status_code == 200:
                        return self.parse_grobid_xml(response.text)
                    elif response.status_code == 503:
                        # Service temporarily unavailable, retry
                        if attempt < retry_count - 1:
                            time.sleep(2)
                            continue
                    else:
                        return {"error": f"HTTP {response.status_code}"}
                        
            except requests.exceptions.Timeout:
                if attempt < retry_count - 1:
                    continue
                return {"error": "Timeout"}
            except requests.exceptions.ConnectionError as e:
                if attempt < retry_count - 1:
                    time.sleep(2)
                    continue
                return {"error": "Connection failed"}
            except Exception as e:
                return {"error": str(e)[:50]}
        
        return {"error": "Max retries exceeded"}
    
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
                        paragraphs = []
                        for p in div.findall('tei:p', ns):
                            text = ' '.join(p.itertext()).strip()
                            if text:
                                paragraphs.append(text)
                        if paragraphs:
                            sections[section_title] = '\n\n'.join(paragraphs)
            
            # Combine text
            full_text = f"Title: {title}\n\nAbstract: {abstract}\n\n"
            for name, content in sections.items():
                full_text += f"\n{name.title()}:\n{content}\n"
            
            # Count references
            refs = len(root.findall('.//tei:listBibl/tei:biblStruct', ns))
            
            return {
                "success": True,
                "title": title,
                "abstract": abstract,
                "sections": sections,
                "full_text": full_text,
                "text_length": len(full_text),
                "num_sections": len(sections),
                "num_references": refs,
                "has_methods": 'method' in ' '.join(sections.keys()).lower(),
                "has_results": 'result' in ' '.join(sections.keys()).lower(),
                "has_discussion": 'discussion' in ' '.join(sections.keys()).lower()
            }
            
        except Exception as e:
            return {"error": f"XML parse: {str(e)[:30]}"}


def extract_with_pymupdf(pdf_path: Path) -> Dict[str, Any]:
    """Extract text using PyMuPDF."""
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
        return {"error": str(e)[:50]}


def main():
    """Test Grobid extraction on a smaller batch."""
    print("=" * 60)
    print("🧪 GROBID v0.7.3 EXTRACTION TEST")
    print("=" * 60)
    
    # Check Grobid
    print("\n🔍 Checking Grobid...")
    grobid = GrobidExtractor()
    if not grobid.check_health():
        print("❌ Grobid not responding")
        return
    print("✅ Grobid v0.7.3 is healthy!")
    
    # Load papers
    print("\n📚 Loading papers from Zotero...")
    kb_builder = KnowledgeBaseBuilder()
    
    try:
        papers = kb_builder.process_zotero_local_library("http://localhost:23119/api")
    except Exception as e:
        print(f"❌ Failed to load papers: {e}")
        return
    
    print(f"✓ Found {len(papers)} papers")
    
    # Get PDF paths
    print("\n📁 Finding PDFs...")
    pdf_map = kb_builder.get_pdf_paths_from_sqlite()
    
    if not pdf_map:
        print("❌ No PDFs found")
        return
    
    print(f"✓ Found {len(pdf_map)} PDFs")
    
    # Test smaller batch with delays
    results = []
    tested = 0
    target = 20  # Smaller batch
    
    print(f"\n🔬 Testing {target} papers (with 1-second delays)...")
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
        title = paper.get('title', 'Untitled')[:40]
        print(f"[{tested:2d}/{target}] {title}...", end=" ", flush=True)
        
        # Add delay between PDFs to avoid overwhelming Grobid
        if tested > 1:
            time.sleep(1)
        
        # Extract with both methods
        start = time.time()
        grobid_result = grobid.extract_full_text(pdf_path)
        grobid_time = time.time() - start
        
        start = time.time()
        pymupdf_result = extract_with_pymupdf(pdf_path)
        pymupdf_time = time.time() - start
        
        # Compare
        result = {
            "title": paper.get('title', 'Untitled'),
            "grobid": {
                "success": grobid_result.get("success", False),
                "text_length": grobid_result.get("text_length", 0),
                "num_sections": grobid_result.get("num_sections", 0),
                "num_references": grobid_result.get("num_references", 0),
                "has_methods": grobid_result.get("has_methods", False),
                "has_results": grobid_result.get("has_results", False),
                "time": grobid_time,
                "error": grobid_result.get("error")
            },
            "pymupdf": {
                "success": pymupdf_result.get("success", False),
                "text_length": pymupdf_result.get("text_length", 0),
                "time": pymupdf_time
            }
        }
        
        if grobid_result.get("success") and pymupdf_result.get("success"):
            g_len = grobid_result.get("text_length", 0)
            p_len = pymupdf_result.get("text_length", 0)
            if p_len > 0:
                result["change_pct"] = ((g_len - p_len) / p_len) * 100
        
        results.append(result)
        
        # Show result
        if grobid_result.get("success"):
            sections = grobid_result.get("num_sections", 0)
            refs = grobid_result.get("num_references", 0)
            print(f"✅ ({sections} sections, {refs} refs)")
        else:
            error = grobid_result.get("error", "Unknown")[:20]
            print(f"❌ ({error})")
    
    # Results summary
    print("\n" + "=" * 60)
    print("📊 RESULTS SUMMARY")
    print("=" * 60)
    
    total = len(results)
    grobid_success = sum(1 for r in results if r["grobid"]["success"])
    success_rate = grobid_success * 100 / total if total > 0 else 0
    
    print(f"\n✅ Success Rate: {grobid_success}/{total} ({success_rate:.1f}%)")
    
    # Quality metrics for successful extractions
    successful = [r for r in results if r["grobid"]["success"]]
    if successful:
        avg_sections = sum(r["grobid"]["num_sections"] for r in successful) / len(successful)
        avg_refs = sum(r["grobid"]["num_references"] for r in successful) / len(successful)
        with_methods = sum(1 for r in successful if r["grobid"]["has_methods"])
        with_results = sum(1 for r in successful if r["grobid"]["has_results"])
        
        print(f"\n📚 Structure Detection (for {len(successful)} successful):")
        print(f"  • Average sections: {avg_sections:.1f}")
        print(f"  • Average references: {avg_refs:.1f}")
        print(f"  • Papers with Methods: {with_methods}/{len(successful)}")
        print(f"  • Papers with Results: {with_results}/{len(successful)}")
    
    # Text quality
    changes = [r.get("change_pct", 0) for r in results if "change_pct" in r]
    if changes:
        avg_change = sum(changes) / len(changes)
        print(f"\n📈 Text Volume: {avg_change:+.1f}% average change vs PyMuPDF")
    
    # Performance
    avg_grobid = sum(r["grobid"]["time"] for r in results) / total
    avg_pymupdf = sum(r["pymupdf"]["time"] for r in results) / total
    print(f"\n⏱️ Performance:")
    print(f"  • Grobid: {avg_grobid:.2f}s per paper")
    print(f"  • PyMuPDF: {avg_pymupdf:.3f}s per paper")
    print(f"  • Speed factor: {avg_grobid/avg_pymupdf:.1f}x slower")
    
    # Save report
    report_path = Path("exports/grobid_stable_test.json")
    report_path.parent.mkdir(exist_ok=True)
    
    with open(report_path, 'w') as f:
        json.dump({
            "date": datetime.now().isoformat(),
            "grobid_version": "0.7.3",
            "summary": {
                "total_tested": total,
                "success_count": grobid_success,
                "success_rate": success_rate,
                "avg_sections": avg_sections if successful else 0,
                "avg_references": avg_refs if successful else 0
            },
            "results": results
        }, f, indent=2)
    
    print(f"\n💾 Report saved to: {report_path}")
    
    # Final verdict
    print("\n" + "=" * 60)
    if success_rate >= 90:
        print("🎉 EXCELLENT: Grobid achieves >90% extraction rate!")
    elif success_rate >= 70:
        print("✅ GOOD: Grobid significantly improves extraction")
    elif success_rate >= 50:
        print("🟡 MODERATE: Grobid works but needs tuning")
    else:
        print("❌ POOR: Grobid extraction needs investigation")
    print("=" * 60)


if __name__ == "__main__":
    main()