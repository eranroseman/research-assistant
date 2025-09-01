#!/usr/bin/env python3
"""V5 Extraction Pipeline - Complete workflow from PDFs to clean KB.

This script consolidates all stages of the v5 extraction pipeline:
1. Grobid extraction from Zotero PDFs
2. Full text recovery (bug fix)
3. Quality filtering
4. CrossRef enrichment
5. Non-article filtering
6. Malformed DOI cleaning
7. Final KB preparation

Usage:
    python v5_extraction_pipeline.py [--skip-extraction] [--output-dir DIR]
"""

import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime, UTC
import time
import shutil


class V5Pipeline:
    """Complete v5 extraction pipeline."""

    def __init__(self, output_dir: str = None, skip_extraction: bool = False):
        self.timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        self.output_dir = Path(output_dir) if output_dir else Path(f"kb_v5_{self.timestamp}")
        self.skip_extraction = skip_extraction
        self.stats = {"start_time": time.time(), "stages_completed": [], "errors": []}

    def run_command(self, cmd: str, stage_name: str) -> bool:
        """Run a command and track its success."""
        print(f"\n{'=' * 70}")
        print(f"STAGE: {stage_name}")
        print(f"{'=' * 70}")
        print(f"Running: {cmd}")

        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
            print(result.stdout)
            if result.stderr:
                print(f"Warnings: {result.stderr}")

            self.stats["stages_completed"].append(stage_name)
            return True

        except subprocess.CalledProcessError as e:
            print(f"ERROR in {stage_name}:")
            print(e.stdout)
            print(e.stderr)
            self.stats["errors"].append(
                {"stage": stage_name, "error": str(e), "stdout": e.stdout, "stderr": e.stderr}
            )
            return False

    def check_prerequisites(self) -> bool:
        """Check that required scripts exist."""
        required_scripts = [
            "v5_design/implementations/extract_zotero_library.py",
            "reprocess_tei_xml.py",
            "pdf_quality_filter.py",
            "crossref_enrichment.py",
            "filter_non_articles.py",
            "fix_malformed_dois.py",
        ]

        if not self.skip_extraction:
            # Check if Grobid is running
            try:
                import requests

                response = requests.get("http://localhost:8070/api/isalive", timeout=5)
                if response.status_code != 200:
                    print("ERROR: Grobid is not running!")
                    print("Start it with: docker run -t --rm -p 8070:8070 lfoppiano/grobid:0.8.2-full")
                    return False
            except Exception:
                print("ERROR: Cannot connect to Grobid on localhost:8070")
                print("Start it with: docker run -t --rm -p 8070:8070 lfoppiano/grobid:0.8.2-full")
                return False

        missing = []
        for script in required_scripts:
            if not Path(script).exists():
                missing.append(script)

        if missing:
            print("ERROR: Missing required scripts:")
            for script in missing:
                print(f"  - {script}")
            return False

        return True

    def run_pipeline(self):
        """Run the complete v5 extraction pipeline."""
        print("=" * 70)
        print("V5 EXTRACTION PIPELINE")
        print("=" * 70)
        print(f"Output directory: {self.output_dir}")
        print(f"Skip extraction: {self.skip_extraction}")

        # Check prerequisites
        if not self.check_prerequisites():
            print("\nFailed prerequisite checks. Exiting.")
            return False

        # Stage 1: Grobid Extraction (if not skipped)
        if not self.skip_extraction:
            if not self.run_command(
                "python v5_design/implementations/extract_zotero_library.py", "1. Grobid Extraction"
            ):
                print("\nPipeline failed at Grobid extraction.")
                return False
        else:
            print("\nSkipping Grobid extraction (using existing data)")
            self.stats["stages_completed"].append("1. Grobid Extraction (skipped)")

        # Stage 2: Full Text Recovery
        if not self.run_command("python reprocess_tei_xml.py", "2. Full Text Recovery"):
            print("\nPipeline failed at text recovery.")
            return False

        # Stage 3: Quality Filtering
        if not self.run_command("python pdf_quality_filter.py", "3. Quality Filtering"):
            print("\nPipeline failed at quality filtering.")
            return False

        # Stage 4: CrossRef Enrichment
        if not self.run_command("python crossref_enrichment.py", "4. CrossRef Enrichment"):
            print("\nPipeline failed at CrossRef enrichment.")
            return False

        # Stage 5: Non-Article Filtering
        if not self.run_command("python filter_non_articles.py", "5. Non-Article Filtering"):
            print("\nPipeline failed at non-article filtering.")
            return False

        # Stage 6: Malformed DOI Cleaning
        if not self.run_command("python fix_malformed_dois.py", "6. Malformed DOI Cleaning"):
            print("\nPipeline failed at DOI cleaning.")
            return False

        # Stage 7: Prepare Final Output
        print(f"\n{'=' * 70}")
        print("STAGE: 7. Final Output Preparation")
        print(f"{'=' * 70}")

        # Find the latest kb_articles_only directory
        kb_dirs = sorted(Path(".").glob("kb_articles_only_*"))
        if not kb_dirs:
            print("ERROR: No kb_articles_only directory found!")
            return False

        latest_kb = kb_dirs[-1]
        print(f"Using KB directory: {latest_kb}")

        # Copy to output directory
        if self.output_dir != latest_kb:
            print(f"Copying to: {self.output_dir}")
            if self.output_dir.exists():
                shutil.rmtree(self.output_dir)
            shutil.copytree(latest_kb, self.output_dir)

        self.stats["stages_completed"].append("7. Final Output Preparation")

        # Generate final report
        self.generate_report()

        return True

    def generate_report(self):
        """Generate a final pipeline report."""
        # Count articles
        json_files = list(self.output_dir.glob("*.json"))
        article_count = len([f for f in json_files if "report" not in f.name])

        # Analyze coverage
        missing_titles = 0
        missing_dois = 0
        total_chars = 0

        for f in json_files:
            if "report" in f.name:
                continue
            with open(f) as file:
                data = json.load(file)
                if not data.get("title", "").strip():
                    missing_titles += 1
                if not data.get("doi", "").strip():
                    missing_dois += 1

                # Count text
                for section in data.get("sections", []):
                    if isinstance(section, dict):
                        total_chars += len(section.get("text", ""))

        # Calculate runtime
        runtime = time.time() - self.stats["start_time"]
        hours = int(runtime // 3600)
        minutes = int((runtime % 3600) // 60)
        seconds = int(runtime % 60)

        # Generate report
        report = {
            "timestamp": self.timestamp,
            "runtime": f"{hours}h {minutes}m {seconds}s",
            "runtime_seconds": runtime,
            "stages_completed": self.stats["stages_completed"],
            "errors": self.stats["errors"],
            "statistics": {
                "total_articles": article_count,
                "articles_with_titles": article_count - missing_titles,
                "title_coverage": f"{(article_count - missing_titles) / article_count * 100:.2f}%",
                "articles_with_dois": article_count - missing_dois,
                "doi_coverage": f"{(article_count - missing_dois) / article_count * 100:.2f}%",
                "total_text_chars": total_chars,
                "avg_chars_per_article": int(total_chars / article_count) if article_count > 0 else 0,
            },
            "output_directory": str(self.output_dir),
        }

        # Save report
        report_path = self.output_dir / "pipeline_report.json"
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)

        # Print summary
        print(f"\n{'=' * 70}")
        print("PIPELINE COMPLETE")
        print(f"{'=' * 70}")
        print(f"Runtime: {report['runtime']}")
        print(f"Articles processed: {article_count}")
        print(f"Title coverage: {report['statistics']['title_coverage']}")
        print(f"DOI coverage: {report['statistics']['doi_coverage']}")
        print(f"Total text: {total_chars:,} characters")
        print(f"Output: {self.output_dir}")
        print(f"Report: {report_path}")

        if self.stats["errors"]:
            print(f"\n⚠️ WARNING: {len(self.stats['errors'])} errors occurred:")
            for error in self.stats["errors"]:
                print(f"  - {error['stage']}: {error['error'][:100]}")

        print("\n✅ Ready to build KB:")
        print(f"   python src/build_kb.py --input {self.output_dir}/")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="V5 Extraction Pipeline - Complete workflow from PDFs to clean KB"
    )
    parser.add_argument(
        "--skip-extraction", action="store_true", help="Skip Grobid extraction (use existing TEI XML files)"
    )
    parser.add_argument(
        "--output-dir", type=str, help="Output directory for final KB (default: kb_v5_TIMESTAMP)"
    )

    args = parser.parse_args()

    # Run pipeline
    pipeline = V5Pipeline(output_dir=args.output_dir, skip_extraction=args.skip_extraction)

    success = pipeline.run_pipeline()

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
