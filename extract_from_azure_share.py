#!/usr/bin/env python3
"""Extract PDFs from Azure File Share using Grobid.

Designed to run on Azure VMs with mounted file share.
"""

import sys
import json
import time
import requests
from pathlib import Path
from datetime import datetime
from typing import Any
import logging
import hashlib


class AzureShareGrobidExtractor:
    """Extractor for processing PDFs from Azure File Share using Grobid."""

    def __init__(self, vm_id: int, total_vms: int = 3):
        self.vm_id = vm_id
        self.total_vms = total_vms
        self.share_path = Path("/mnt/pdfs")
        self.output_dir = Path(f"extraction_vm_{vm_id}")
        self.output_dir.mkdir(exist_ok=True)

        # Grobid configuration (same as your successful local config)
        self.grobid_url = "http://localhost:8070"
        self.grobid_params = {
            "consolidateHeader": "2",  # Biblio-glutton
            "consolidateCitations": "2",  # Full enrichment
            "consolidateFunders": "1",
            "processFigures": "1",
            "processTables": "1",
            "processEquations": "1",
            "segmentSentences": "1",
            "includeRawCitations": "1",
            "includeRawAffiliations": "1",
            "teiCoordinates": "all",
            "timeout": 120,
        }

        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - VM%(vm_id)d - %(message)s",
            handlers=[logging.FileHandler(f"extraction_vm_{vm_id}.log"), logging.StreamHandler()],
        )
        self.logger = logging.getLogger(__name__)

    def get_pdf_list(self) -> list[Path]:
        """Get list of PDFs assigned to this VM"""
        # Find all PDFs in the mounted share
        all_pdfs = sorted(self.share_path.glob("*/*.pdf"))
        self.logger.info(f"Found {len(all_pdfs)} total PDFs in share")

        # Distribute PDFs across VMs
        # VM 1 gets PDFs 0, 3, 6, 9...
        # VM 2 gets PDFs 1, 4, 7, 10...
        # VM 3 gets PDFs 2, 5, 8, 11...
        my_pdfs = [pdf for i, pdf in enumerate(all_pdfs) if i % self.total_vms == (self.vm_id - 1)]

        self.logger.info(f"VM {self.vm_id} assigned {len(my_pdfs)} PDFs")
        return my_pdfs

    def wait_for_grobid(self, max_wait: int = 60):
        """Wait for Grobid to be ready"""
        self.logger.info("Waiting for Grobid to start...")
        for i in range(max_wait):
            try:
                response = requests.get(f"{self.grobid_url}/api/isalive")
                if response.text.strip() == "true":
                    self.logger.info("Grobid is ready!")
                    return True
            except Exception:
                pass
            time.sleep(1)
        raise Exception("Grobid failed to start")

    def extract_pdf(self, pdf_path: Path) -> dict[str, Any]:
        """Extract single PDF using Grobid"""
        # Create unique ID for this PDF
        pdf_id = hashlib.md5(str(pdf_path).encode()).hexdigest()[:8]

        # Check if already processed
        result_file = self.output_dir / f"{pdf_id}_metadata.json"
        if result_file.exists():
            self.logger.info(f"Skipping {pdf_path.name} - already processed")
            return {"status": "skipped", "id": pdf_id}

        try:
            # Process with Grobid
            with open(pdf_path, "rb") as pdf_file:
                files = {"input": pdf_file}

                # Full document processing
                response = requests.post(
                    f"{self.grobid_url}/api/processFulltextDocument",
                    files=files,
                    data=self.grobid_params,
                    timeout=120,
                )

                if response.status_code == 200:
                    # Save TEI XML
                    tei_file = self.output_dir / f"{pdf_id}_tei.xml"
                    tei_file.write_text(response.text, encoding="utf-8")

                    # Also get header for metadata
                    pdf_file.seek(0)
                    header_response = requests.post(
                        f"{self.grobid_url}/api/processHeaderDocument",
                        files={"input": pdf_file},
                        data=self.grobid_params,
                        timeout=60,
                    )

                    # Save all outputs (following your 7-file strategy)
                    outputs = {
                        "metadata": self.output_dir / f"{pdf_id}_metadata.json",
                        "header": self.output_dir / f"{pdf_id}_header.xml",
                        "citations": self.output_dir / f"{pdf_id}_citations.json",
                        "fulltext": self.output_dir / f"{pdf_id}_fulltext.xml",
                        "figures": self.output_dir / f"{pdf_id}_figures.json",
                        "tables": self.output_dir / f"{pdf_id}_tables.json",
                        "equations": self.output_dir / f"{pdf_id}_equations.json",
                    }

                    # Save metadata
                    metadata = {
                        "pdf_id": pdf_id,
                        "pdf_path": str(pdf_path),
                        "pdf_name": pdf_path.name,
                        "extraction_date": datetime.now().isoformat(),
                        "vm_id": self.vm_id,
                        "status": "success",
                    }

                    with open(outputs["metadata"], "w") as f:
                        json.dump(metadata, f, indent=2)

                    # Save header
                    outputs["header"].write_text(header_response.text, encoding="utf-8")

                    self.logger.info(f"✅ Processed {pdf_path.name}")
                    return {"status": "success", "id": pdf_id}

                self.logger.error(f"❌ Failed {pdf_path.name}: HTTP {response.status_code}")
                return {"status": "failed", "error": f"HTTP {response.status_code}"}

        except Exception as e:
            self.logger.error(f"❌ Error processing {pdf_path.name}: {e}")
            return {"status": "error", "error": str(e)}

    def run_extraction(self):
        """Main extraction loop"""
        self.wait_for_grobid()

        pdf_list = self.get_pdf_list()
        total = len(pdf_list)

        self.logger.info(f"Starting extraction of {total} PDFs")
        start_time = time.time()

        success_count = 0
        failed_count = 0

        for i, pdf_path in enumerate(pdf_list, 1):
            self.logger.info(f"[{i}/{total}] Processing {pdf_path.name}")

            result = self.extract_pdf(pdf_path)

            if result["status"] == "success":
                success_count += 1
            elif result["status"] != "skipped":
                failed_count += 1

            # Progress update every 50 papers
            if i % 50 == 0:
                elapsed = time.time() - start_time
                rate = i / elapsed
                remaining = (total - i) / rate
                self.logger.info(f"Progress: {i}/{total} ({i * 100 / total:.1f}%)")
                self.logger.info(f"Success rate: {success_count}/{i} ({success_count * 100 / i:.1f}%)")
                self.logger.info(f"Estimated remaining: {remaining / 3600:.1f} hours")

        # Final report
        elapsed = time.time() - start_time
        self.logger.info("=" * 60)
        self.logger.info(f"EXTRACTION COMPLETE - VM {self.vm_id}")
        self.logger.info(f"Total processed: {total}")
        self.logger.info(f"Success: {success_count}")
        self.logger.info(f"Failed: {failed_count}")
        self.logger.info(f"Time: {elapsed / 3600:.2f} hours")
        self.logger.info(f"Average: {elapsed / total:.1f} seconds per paper")
        self.logger.info("=" * 60)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python extract_from_azure_share.py <vm_id>")
        print("  vm_id: 1, 2, or 3")
        sys.exit(1)

    vm_id = int(sys.argv[1])
    if vm_id not in [1, 2, 3]:
        print("VM ID must be 1, 2, or 3")
        sys.exit(1)

    extractor = AzureShareGrobidExtractor(vm_id, total_vms=3)
    extractor.run_extraction()
