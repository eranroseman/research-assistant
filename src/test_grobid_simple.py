#!/usr/bin/env python3
"""
Simple Grobid extraction test - assumes Grobid is already running on port 8070.

This script:
1. Fetches 100 papers from Zotero
2. Extracts full text using Grobid
3. Compares with current PyMuPDF extraction
4. Generates quality comparison report
"""

import json
import time
import requests
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import xml.etree.ElementTree as ET
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

try:
    from build_kb import KnowledgeBaseBuilder
    import fitz  # PyMuPDF
except ImportError as e:
    print(f"Error importing required modules: {e}")
    print("Please ensure you're in the correct environment")
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
            # Use requests directly instead of session for health check
            response = requests.get(f"{self.grobid_url}/api/isalive", timeout=5)
            return response.status_code == 200
        except requests.RequestException as e:
            print(f"Health check error: {e}")
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
                    return {"error": f"Grobid returned status {response.status_code}"}
                    
        except Exception as e:
            return {"error": f"Extraction failed: {str(e)}"}
    
    def parse_grobid_xml(self, xml_content: str) -> Dict[str, Any]:
        """Parse Grobid TEI XML output into structured sections."""
        try:
            root = ET.fromstring(xml_content)
            ns = {'tei': 'http://www.tei-c.org/ns/1.0'}
            
            # Extract title
            title = ""
            title_elem = root.find('.//tei:titleStmt/tei:title', ns)
            if title_elem is not None and title_elem.text:
                title = title_elem.text.strip()
            
            # Extract abstract
            abstract = ""
            abstract_elem = root.find('.//tei:abstract', ns)
            if abstract_elem is not None:
                abstract = ' '.join(abstract_elem.itertext()).strip()
            
            # Extract body sections
            sections = {}
            body = root.find('.//tei:body', ns)
            if body is not None:
                for div in body.findall('.//tei:div', ns):
                    head = div.find('tei:head', ns)
                    if head is not None and head.text:
                        section_title = head.text.strip().lower()
                        section_text = []
                        
                        for p in div.findall('tei:p', ns):
                            text = ' '.join(p.itertext()).strip()
                            if text:
                                section_text.append(text)
                        
                        if section_text:
                            sections[section_title] = '\n\n'.join(section_text)
            
            # Combine all text
            full_text_parts = []
            if title:
                full_text_parts.append(f"Title: {title}\n")
            if abstract:
                full_text_parts.append(f"Abstract: {abstract}\n")
            
            for section_name, section_content in sections.items():
                full_text_parts.append(f"\n{section_name.title()}:\n{section_content}")
            
            full_text = '\n'.join(full_text_parts)
            
            # Extract references count
            references = len(root.findall('.//tei:listBibl/tei:biblStruct', ns))
            
            return {
                "success": True,
                "title": title,
                "abstract": abstract,
                "sections": sections,
                "full_text": full_text,
                "text_length": len(full_text),
                "num_sections": len(sections),
                "num_references": references,
                "has_methods": 'method' in ' '.join(sections.keys()).lower(),
                "has_results": 'result' in ' '.join(sections.keys()).lower(),
                "has_discussion": 'discussion' in ' '.join(sections.keys()).lower()
            }
            
        except Exception as e:
            return {"error": f"XML parsing failed: {str(e)}"}


def extract_with_pymupdf(pdf_path: Path) -> Dict[str, Any]:
    """Extract text using current PyMuPDF method for comparison."""
    try:
        pdf_doc = fitz.open(pdf_path)
        text_parts = []
        
        for page_num in range(len(pdf_doc)):
            page = pdf_doc[page_num]
            text = page.get_text()
            if text:
                text_parts.append(text)
        
        full_text = '\n'.join(text_parts)
        num_pages = len(pdf_doc)
        pdf_doc.close()
        
        return {
            "success": True,
            "full_text": full_text,
            "text_length": len(full_text),
            "num_pages": num_pages
        }
    except Exception as e:
        return {"error": f"PyMuPDF extraction failed: {str(e)}"}


def compare_extraction(pdf_path: Path, paper_title: str, grobid: GrobidExtractor) -> Dict[str, Any]:
    """Compare Grobid vs PyMuPDF extraction for a single paper."""
    
    # Extract with both methods
    start_time = time.time()
    grobid_result = grobid.extract_full_text(pdf_path)
    grobid_time = time.time() - start_time
    
    start_time = time.time()
    pymupdf_result = extract_with_pymupdf(pdf_path)
    pymupdf_time = time.time() - start_time
    
    comparison = {
        "title": paper_title[:100],  # Truncate long titles
        "pdf_path": str(pdf_path),
        "grobid": {
            "success": grobid_result.get("success", False),
            "text_length": grobid_result.get("text_length", 0),
            "num_sections": grobid_result.get("num_sections", 0),
            "has_methods": grobid_result.get("has_methods", False),
            "has_results": grobid_result.get("has_results", False),
            "has_discussion": grobid_result.get("has_discussion", False),
            "extraction_time": grobid_time,
            "error": grobid_result.get("error")
        },
        "pymupdf": {
            "success": pymupdf_result.get("success", False),
            "text_length": pymupdf_result.get("text_length", 0),
            "extraction_time": pymupdf_time,
            "error": pymupdf_result.get("error")
        }
    }
    
    # Calculate improvement metrics
    if grobid_result.get("success") and pymupdf_result.get("success"):
        grobid_len = grobid_result.get("text_length", 0)
        pymupdf_len = pymupdf_result.get("text_length", 0)
        
        if pymupdf_len > 0:
            comparison["text_increase_pct"] = ((grobid_len - pymupdf_len) / pymupdf_len) * 100
        else:
            comparison["text_increase_pct"] = 100 if grobid_len > 0 else 0
    
    return comparison


def generate_report(results: List[Dict], output_path: Path) -> None:
    """Generate comprehensive comparison report."""
    
    # Calculate statistics
    total = len(results)
    grobid_success = sum(1 for r in results if r["grobid"]["success"])
    pymupdf_success = sum(1 for r in results if r["pymupdf"]["success"])
    both_success = sum(1 for r in results if r["grobid"]["success"] and r["pymupdf"]["success"])
    
    # Text improvements for successful extractions
    text_improvements = [r["text_increase_pct"] for r in results if "text_increase_pct" in r]
    avg_text_increase = sum(text_improvements) / len(text_improvements) if text_improvements else 0
    
    # Section detection
    papers_with_methods = sum(1 for r in results if r["grobid"].get("has_methods"))
    papers_with_results = sum(1 for r in results if r["grobid"].get("has_results"))
    papers_with_discussion = sum(1 for r in results if r["grobid"].get("has_discussion"))
    
    # Performance
    avg_grobid_time = sum(r["grobid"]["extraction_time"] for r in results) / total
    avg_pymupdf_time = sum(r["pymupdf"]["extraction_time"] for r in results) / total
    
    # Generate report
    report = []
    report.append("# Grobid Extraction Test Report\n")
    report.append(f"**Test Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    report.append(f"**Papers Tested:** {total}\n")
    
    report.append("## 🎯 Success Rates\n")
    report.append(f"- **Grobid Success:** {grobid_success}/{total} ({grobid_success*100/total:.1f}%)")
    report.append(f"- **PyMuPDF Success:** {pymupdf_success}/{total} ({pymupdf_success*100/total:.1f}%)")
    report.append(f"- **Both Successful:** {both_success}/{total} ({both_success*100/total:.1f}%)\n")
    
    if grobid_success >= 95:
        report.append("✅ **PASS: Grobid achieves target 95%+ extraction rate!**\n")
    else:
        report.append(f"⚠️ **Grobid below 95% target (achieved {grobid_success}%)**\n")
    
    report.append("## 📈 Text Extraction Quality\n")
    report.append(f"- **Average Text Change:** {avg_text_increase:+.1f}%")
    report.append(f"- **Papers with MORE text:** {sum(1 for t in text_improvements if t > 0)}")
    report.append(f"- **Papers with LESS text:** {sum(1 for t in text_improvements if t < 0)}")
    report.append(f"- **Papers with >20% more:** {sum(1 for t in text_improvements if t > 20)}\n")
    
    report.append("## 📊 Structure Detection (Grobid)\n")
    report.append(f"- **Methods Section:** {papers_with_methods}/{total} ({papers_with_methods*100/total:.1f}%)")
    report.append(f"- **Results Section:** {papers_with_results}/{total} ({papers_with_results*100/total:.1f}%)")
    report.append(f"- **Discussion Section:** {papers_with_discussion}/{total} ({papers_with_discussion*100/total:.1f}%)\n")
    
    report.append("## ⏱️ Performance\n")
    report.append(f"- **Avg Grobid Time:** {avg_grobid_time:.2f}s per paper")
    report.append(f"- **Avg PyMuPDF Time:** {avg_pymupdf_time:.3f}s per paper")
    report.append(f"- **Speed Factor:** {avg_grobid_time/avg_pymupdf_time:.1f}x slower")
    report.append(f"- **Total Test Time:** {sum(r['grobid']['extraction_time'] for r in results):.1f}s\n")
    
    # Grobid failures
    grobid_failures = [r for r in results if not r["grobid"]["success"]]
    if grobid_failures:
        report.append("## ❌ Grobid Failures\n")
        for i, failure in enumerate(grobid_failures[:5], 1):
            report.append(f"{i}. {failure['title']}: {failure['grobid'].get('error', 'Unknown')}")
        if len(grobid_failures) > 5:
            report.append(f"... and {len(grobid_failures)-5} more\n")
    
    # Top improvements
    improvements = sorted([r for r in results if r.get("text_increase_pct", 0) > 50], 
                         key=lambda x: x["text_increase_pct"], reverse=True)[:5]
    
    if improvements:
        report.append("## 🌟 Top Improvements (>50% more text)\n")
        for i, imp in enumerate(improvements, 1):
            report.append(f"{i}. {imp['title']}: **+{imp['text_increase_pct']:.0f}%**")
    
    # Save report
    with open(output_path, 'w') as f:
        f.write('\n'.join(report))
    
    # Save raw data
    json_path = output_path.parent / f"{output_path.stem}_data.json"
    with open(json_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n📄 Report saved to: {output_path}")
    print(f"💾 Raw data saved to: {json_path}")


def main():
    """Main test function."""
    print("=" * 60)
    print("🧪 Grobid Extraction Test - v5.0 Validation")
    print("=" * 60)
    
    # Initialize Grobid
    grobid = GrobidExtractor()
    
    # Check Grobid health
    print("\n🔍 Checking Grobid status...")
    if not grobid.check_health():
        print("❌ Grobid is not responding on port 8070")
        print("Please ensure Grobid Docker container is running:")
        print("  docker run -d --name grobid -p 8070:8070 grobid/grobid:0.7.3")
        return
    print("✅ Grobid is healthy and ready!")
    
    # Load papers from Zotero
    print("\n📚 Loading papers from Zotero...")
    kb_builder = KnowledgeBaseBuilder()
    
    try:
        papers = kb_builder.process_zotero_local_library("http://localhost:23119/api")
    except Exception as e:
        print(f"❌ Failed to load papers: {e}")
        print("Please ensure Zotero is running with local API enabled")
        return
    
    print(f"✓ Found {len(papers)} papers in Zotero")
    
    # Filter to papers with PDFs
    papers_with_pdfs = []
    for paper in papers:
        pdf_path = kb_builder.find_pdf_for_paper(paper)
        if pdf_path and pdf_path.exists():
            paper['pdf_path'] = pdf_path
            papers_with_pdfs.append(paper)
            if len(papers_with_pdfs) >= 100:
                break
    
    if not papers_with_pdfs:
        print("❌ No papers with PDFs found")
        return
    
    test_count = min(100, len(papers_with_pdfs))
    print(f"✓ Testing {test_count} papers with PDFs\n")
    
    # Test extraction
    results = []
    print("🔬 Starting extraction comparison...")
    print("-" * 40)
    
    for i, paper in enumerate(papers_with_pdfs[:test_count], 1):
        title = paper.get('title', 'Untitled')
        print(f"[{i:3d}/{test_count}] {title[:50]}...", end=" ")
        
        result = compare_extraction(
            paper['pdf_path'],
            title,
            grobid
        )
        results.append(result)
        
        # Show inline result
        if result["grobid"]["success"]:
            change = result.get("text_increase_pct", 0)
            print(f"✓ ({change:+.0f}%)")
        else:
            print("✗")
        
        # Progress update every 20 papers
        if i % 20 == 0:
            successful = sum(1 for r in results if r["grobid"]["success"])
            print(f"\n  Progress: {successful}/{i} successful ({successful*100/i:.0f}%)\n")
    
    # Generate report
    print("\n" + "=" * 60)
    print("📊 Generating report...")
    
    report_path = Path("exports/grobid_test_report.md")
    report_path.parent.mkdir(exist_ok=True)
    generate_report(results, report_path)
    
    # Print summary
    success_count = sum(1 for r in results if r["grobid"]["success"])
    success_rate = success_count * 100 / len(results)
    
    print("\n" + "=" * 60)
    print("🏁 TEST COMPLETE")
    print("=" * 60)
    print(f"Success Rate: {success_count}/{len(results)} ({success_rate:.1f}%)")
    
    if success_rate >= 95:
        print("✅ **PASS**: Grobid achieves 95%+ extraction rate!")
    elif success_rate >= 85:
        print("🟡 **GOOD**: Grobid significantly improves extraction")
    else:
        print(f"⚠️ **NEEDS REVIEW**: Success rate below expectations")
    
    avg_increase = sum(r.get("text_increase_pct", 0) for r in results if "text_increase_pct" in r)
    avg_increase = avg_increase / len([r for r in results if "text_increase_pct" in r]) if results else 0
    print(f"Text Quality: {avg_increase:+.1f}% average change")


if __name__ == "__main__":
    main()