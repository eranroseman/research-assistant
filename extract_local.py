#!/usr/bin/env python3
import sys
import json
import time
import requests
from pathlib import Path
from datetime import datetime


class GrobidExtractor:
    def __init__(self, vm_id):
        self.vm_id = vm_id
        self.grobid_url = "http://localhost:8070"
        self.output_dir = Path(f"extraction_vm_{vm_id}")
        self.output_dir.mkdir(exist_ok=True)

        # Checkpoint file
        self.checkpoint_file = self.output_dir / "checkpoint.json"
        self.processed_files = self.load_checkpoint()

        # Log file
        self.log_file = self.output_dir / f"extraction_vm_{vm_id}.log"

    def load_checkpoint(self):
        if self.checkpoint_file.exists():
            with open(self.checkpoint_file) as f:
                return set(json.load(f))
        return set()

    def save_checkpoint(self):
        with open(self.checkpoint_file, "w") as f:
            json.dump(list(self.processed_files), f)

    def log(self, message):
        timestamp = datetime.now().isoformat()
        log_msg = f"[{timestamp}] {message}"
        print(log_msg)
        with open(self.log_file, "a") as f:
            f.write(log_msg + "\n")

    def wait_for_grobid(self):
        """Wait for Grobid to be ready"""
        self.log("Waiting for Grobid to be ready...")
        max_attempts = 60
        for i in range(max_attempts):
            try:
                response = requests.get(f"{self.grobid_url}/api/isalive")
                if response.status_code == 200:
                    self.log("Grobid is ready!")
                    return True
            except Exception:
                pass
            time.sleep(5)
        return False

    def extract_pdf(self, pdf_path):
        """Extract all data from PDF using Grobid"""
        pdf_name = pdf_path.name
        output_base = self.output_dir / pdf_path.parent.name / pdf_path.stem
        output_base.parent.mkdir(parents=True, exist_ok=True)

        # Skip if already processed
        if str(pdf_path) in self.processed_files:
            return True

        try:
            with open(pdf_path, "rb") as f:
                files = {"input": (pdf_name, f, "application/pdf")}

                # Full text extraction with all options
                params = {
                    "consolidateHeader": "2",
                    "consolidateCitations": "2",
                    "consolidateFunders": "1",
                    "processFigures": "1",
                    "processTables": "1",
                    "processEquations": "1",
                    "segmentSentences": "1",
                    "includeRawCitations": "1",
                    "includeRawAffiliations": "1",
                    "teiCoordinates": "all",
                }

                response = requests.post(
                    f"{self.grobid_url}/api/processFulltextDocument", files=files, data=params, timeout=120
                )

                if response.status_code == 200:
                    # Save TEI XML
                    with open(f"{output_base}_full.xml", "w") as out:
                        out.write(response.text)

                    # Mark as processed
                    self.processed_files.add(str(pdf_path))

                    # Save checkpoint every 10 files
                    if len(self.processed_files) % 10 == 0:
                        self.save_checkpoint()

                    return True
                self.log(f"Failed to process {pdf_name}: {response.status_code}")
                return False

        except Exception as e:
            self.log(f"Error processing {pdf_name}: {e}")
            return False

    def run(self):
        """Main extraction loop"""
        if not self.wait_for_grobid():
            self.log("Grobid failed to start!")
            return

        # Find all PDFs
        pdf_dir = Path.home() / "pdfs"
        pdf_files = sorted(list(pdf_dir.glob("*/*.pdf")))

        self.log(f"Found {len(pdf_files)} PDFs to process")
        self.log(f"Already processed: {len(self.processed_files)}")

        # Process PDFs with progress
        failed = []
        for i, pdf_path in enumerate(pdf_files):
            if not self.extract_pdf(pdf_path):
                failed.append(pdf_path)

            # Log progress every 50 files
            if (i + 1) % 50 == 0:
                self.log(f"Progress: {i + 1}/{len(pdf_files)} processed")

        # Final checkpoint
        self.save_checkpoint()

        # Report results
        self.log("Extraction complete!")
        self.log(f"Processed: {len(self.processed_files)}")
        self.log(f"Failed: {len(failed)}")

        if failed:
            self.log("Failed files:")
            for f in failed:
                self.log(f"  - {f}")


if __name__ == "__main__":
    vm_id = sys.argv[1] if len(sys.argv) > 1 else "1"
    extractor = GrobidExtractor(vm_id)
    extractor.run()
