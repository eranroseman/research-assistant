#!/usr/bin/env python3
"""
Test Grobid extraction on 100 papers to validate v5.0 approach.

This script:
1. Checks if Grobid Docker container is running
2. Fetches 100 papers from Zotero
3. Extracts full text using Grobid
4. Compares with current PyMuPDF extraction
5. Generates quality comparison report
"""

import json
import time
import requests
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import xml.etree.ElementTree as ET
import sys
import os

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
        # Configure for better performance
        self.session.headers.update({
            'Accept': 'application/xml'
        })
    
    def check_grobid_health(self) -> bool:
        """Check if Grobid service is running and healthy."""
        try:
            response = self.session.get(f"{self.grobid_url}/api/isalive")
            return response.status_code == 200
        except requests.RequestException:
            return False
    
    def start_grobid_docker(self) -> bool:
        """Start Grobid Docker container if not running."""
        print("Checking Docker...")
        
        # Detect if we need sudo for Docker
        use_sudo = False
        try:
            result = subprocess.run(
                ["docker", "info"],
                capture_output=True,
                text=True,
                check=False
            )
            if result.returncode != 0:
                # Try with sudo
                result = subprocess.run(
                    ["sudo", "docker", "info"],
                    capture_output=True,
                    text=True,
                    check=False
                )
                if result.returncode == 0:
                    use_sudo = True
                    print("ℹ️  Using sudo for Docker commands")
                else:
                    print("❌ Docker is not accessible. Try: sudo usermod -aG docker $USER")
                    return False
        except FileNotFoundError:
            print("❌ Docker not found. Please install Docker.")
            return False
        
        # Build docker command prefix
        docker_cmd = ["sudo", "docker"] if use_sudo else ["docker"]
        
        # Check if Grobid container exists
        result = subprocess.run(
            docker_cmd + ["ps", "-a", "--filter", "name=grobid", "--format", "{{.Names}}"],
            capture_output=True,
            text=True
        )
        
        if "grobid" not in result.stdout:
            print("📦 Pulling Grobid Docker image (this may take a few minutes)...")
            subprocess.run(
                docker_cmd + ["pull", "grobid/grobid:0.7.3"],
                check=True
            )
            print("✓ Grobid image downloaded")
        
        # Check if container is running
        result = subprocess.run(
            docker_cmd + ["ps", "--filter", "name=grobid", "--format", "{{.Names}}"],
            capture_output=True,
            text=True
        )
        
        if "grobid" not in result.stdout:
            print("🚀 Starting Grobid container...")
            subprocess.run(
                docker_cmd + [
                    "run", "-d",
                    "--name", "grobid",
                    "-p", "8070:8070",
                    "grobid/grobid:0.7.3"
                ],
                check=True
            )
            print("⏳ Waiting for Grobid to initialize...")
            time.sleep(10)  # Give Grobid time to start
        
        # Verify it's healthy
        for i in range(30):  # Wait up to 30 seconds
            if self.check_grobid_health():
                print("✅ Grobid is running and healthy!")
                return True
            time.sleep(1)
        
        print("❌ Grobid failed to start properly")
        return False
    
    def extract_full_text(self, pdf_path: Path) -> Dict[str, Any]:
        """Extract structured text from PDF using Grobid."""
        if not pdf_path.exists():
            return {"error": f"PDF not found: {pdf_path}"}
        
        try:
            with open(pdf_path, 'rb') as pdf_file:
                files = {'input': pdf_file}
                
                # Use processFulltextDocument for complete extraction
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
            
            # Define TEI namespace
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
        pdf_doc.close()
        
        return {
            "success": True,
            "full_text": full_text,
            "text_length": len(full_text),
            "num_pages": len(pdf_doc)
        }
    except Exception as e:
        return {"error": f"PyMuPDF extraction failed: {str(e)}"}


def compare_extraction_methods(pdf_path: Path, paper_title: str, grobid_extractor: GrobidExtractor) -> Dict[str, Any]:
    """Compare Grobid vs PyMuPDF extraction for a single paper."""
    print(f"  Processing: {paper_title[:60]}...")
    
    # Extract with both methods
    start_time = time.time()
    grobid_result = grobid_extractor.extract_full_text(pdf_path)
    grobid_time = time.time() - start_time
    
    start_time = time.time()
    pymupdf_result = extract_with_pymupdf(pdf_path)
    pymupdf_time = time.time() - start_time
    
    comparison = {
        "title": paper_title,
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


def generate_test_report(results: List[Dict], output_path: Path) -> None:
    """Generate comprehensive comparison report."""
    
    # Calculate statistics
    total_papers = len(results)
    grobid_success = sum(1 for r in results if r["grobid"]["success"])
    pymupdf_success = sum(1 for r in results if r["pymupdf"]["success"])
    both_success = sum(1 for r in results if r["grobid"]["success"] and r["pymupdf"]["success"])
    
    # Text extraction improvements
    text_improvements = []
    for r in results:
        if "text_increase_pct" in r:
            text_improvements.append(r["text_increase_pct"])
    
    avg_text_increase = sum(text_improvements) / len(text_improvements) if text_improvements else 0
    
    # Section detection
    papers_with_methods = sum(1 for r in results if r["grobid"].get("has_methods"))
    papers_with_results = sum(1 for r in results if r["grobid"].get("has_results"))
    papers_with_discussion = sum(1 for r in results if r["grobid"].get("has_discussion"))
    
    # Performance
    avg_grobid_time = sum(r["grobid"]["extraction_time"] for r in results) / len(results)
    avg_pymupdf_time = sum(r["pymupdf"]["extraction_time"] for r in results) / len(results)
    
    # Generate report
    report = []
    report.append("# Grobid Extraction Test Report\n")
    report.append(f"**Test Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    report.append(f"**Papers Tested:** {total_papers}\n")
    
    report.append("## Success Rates\n")
    report.append(f"- **Grobid Success:** {grobid_success}/{total_papers} ({grobid_success*100/total_papers:.1f}%)")
    report.append(f"- **PyMuPDF Success:** {pymupdf_success}/{total_papers} ({pymupdf_success*100/total_papers:.1f}%)")
    report.append(f"- **Both Successful:** {both_success}/{total_papers} ({both_success*100/total_papers:.1f}%)\n")
    
    report.append("## Text Extraction Quality\n")
    report.append(f"- **Average Text Increase:** {avg_text_increase:.1f}%")
    report.append(f"- **Papers with >20% more text:** {sum(1 for t in text_improvements if t > 20)}")
    report.append(f"- **Papers with >50% more text:** {sum(1 for t in text_improvements if t > 50)}\n")
    
    report.append("## Structure Detection (Grobid)\n")
    report.append(f"- **Methods Section Found:** {papers_with_methods}/{total_papers} ({papers_with_methods*100/total_papers:.1f}%)")
    report.append(f"- **Results Section Found:** {papers_with_results}/{total_papers} ({papers_with_results*100/total_papers:.1f}%)")
    report.append(f"- **Discussion Section Found:** {papers_with_discussion}/{total_papers} ({papers_with_discussion*100/total_papers:.1f}%)\n")
    
    report.append("## Performance\n")
    report.append(f"- **Average Grobid Time:** {avg_grobid_time:.2f} seconds")
    report.append(f"- **Average PyMuPDF Time:** {avg_pymupdf_time:.3f} seconds")
    report.append(f"- **Speed Difference:** {avg_grobid_time/avg_pymupdf_time:.1f}x slower\n")
    
    # Detailed failures
    grobid_failures = [r for r in results if not r["grobid"]["success"]]
    if grobid_failures:
        report.append("## Grobid Failures\n")
        for failure in grobid_failures[:10]:  # Show first 10
            report.append(f"- {failure['title'][:60]}: {failure['grobid'].get('error', 'Unknown error')}")
        if len(grobid_failures) > 10:
            report.append(f"... and {len(grobid_failures) - 10} more\n")
    
    # Papers with significant improvements
    significant_improvements = sorted(
        [r for r in results if r.get("text_increase_pct", 0) > 50],
        key=lambda x: x["text_increase_pct"],
        reverse=True
    )[:10]
    
    if significant_improvements:
        report.append("## Top Improvements (>50% more text)\n")
        for imp in significant_improvements:
            report.append(f"- {imp['title'][:60]}: +{imp['text_increase_pct']:.0f}%")
    
    # Save report
    with open(output_path, 'w') as f:
        f.write('\n'.join(report))
    
    # Also save raw results as JSON
    json_path = output_path.parent / f"{output_path.stem}_data.json"
    with open(json_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n✅ Report saved to: {output_path}")
    print(f"📊 Raw data saved to: {json_path}")


def main():
    """Main test function."""
    print("=" * 60)
    print("Grobid Extraction Test - v5.0 Validation")
    print("=" * 60)
    
    # Initialize Grobid
    grobid = GrobidExtractor()
    
    # Check/start Grobid
    if not grobid.check_grobid_health():
        print("\n🔧 Grobid not running. Attempting to start...")
        if not grobid.start_grobid_docker():
            print("\n❌ Failed to start Grobid. Please ensure Docker is running.")
            return
    
    # Initialize KB builder to get papers
    print("\n📚 Loading papers from Zotero...")
    kb_builder = KnowledgeBaseBuilder()
    
    try:
        papers = kb_builder.process_zotero_local_library("http://127.0.0.1:23119/api/zotero")
    except Exception as e:
        print(f"❌ Failed to load papers: {e}")
        print("Please ensure Zotero is running with local API enabled")
        return
    
    print(f"✓ Found {len(papers)} papers in Zotero")
    
    # Filter to papers with PDFs and take first 100
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
    
    print(f"✓ Found {len(papers_with_pdfs)} papers with PDFs")
    print(f"🧪 Testing first {min(100, len(papers_with_pdfs))} papers...\n")
    
    # Test extraction on each paper
    results = []
    for i, paper in enumerate(papers_with_pdfs[:100], 1):
        print(f"[{i:3d}/100]", end=" ")
        result = compare_extraction_methods(
            paper['pdf_path'],
            paper.get('title', 'Untitled'),
            grobid
        )
        results.append(result)
        
        # Show progress
        if i % 10 == 0:
            successful = sum(1 for r in results if r["grobid"]["success"])
            print(f"\n  Progress: {successful}/{i} successful extractions")
    
    # Generate report
    print("\n📊 Generating report...")
    report_path = Path("exports/grobid_test_report.md")
    report_path.parent.mkdir(exist_ok=True)
    generate_test_report(results, report_path)
    
    # Print summary
    grobid_success = sum(1 for r in results if r["grobid"]["success"])
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)
    print(f"✅ Grobid Success Rate: {grobid_success}/{len(results)} ({grobid_success*100/len(results):.1f}%)")
    
    avg_increase = sum(r.get("text_increase_pct", 0) for r in results) / len(results)
    print(f"📈 Average Text Increase: {avg_increase:.1f}%")
    
    if grobid_success >= 95:
        print("🎉 SUCCESS: Grobid achieves target 95%+ extraction rate!")
    else:
        print(f"⚠️  Grobid success rate ({grobid_success}%) below target (95%)")


if __name__ == "__main__":
    main()