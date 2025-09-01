#!/usr/bin/env python3
"""Extraction Pipeline Runner - Organized directory structure.

This script runs the complete paper extraction and enrichment pipeline,
saving all outputs in an organized directory structure.
"""

import sys
import subprocess
from pathlib import Path
from datetime import datetime
import argparse


def run_command(cmd, description):
    """Run a command and handle output."""
    print(f"\n{'=' * 60}")
    print(f"Running: {description}")
    print(f"Command: {cmd}")
    print("=" * 60)

    result = subprocess.run(cmd, check=False, shell=True, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"ERROR: {description} failed!")
        print(result.stderr)
        return False

    print(f"✓ {description} completed successfully")
    return True


def main():
    parser = argparse.ArgumentParser(description="Run paper extraction pipeline")
    parser.add_argument(
        "--pipeline-dir", default=None, help="Pipeline directory (default: extraction_pipeline_YYYYMMDD)"
    )
    parser.add_argument(
        "--start-from",
        default="tei_extraction",
        choices=["tei_extraction", "zotero", "crossref", "s2", "openalex"],
        help="Start from specific stage",
    )
    parser.add_argument(
        "--stop-after",
        default=None,
        choices=["tei_extraction", "zotero", "crossref", "s2", "openalex"],
        help="Stop after specific stage",
    )

    args = parser.parse_args()

    # Set up pipeline directory
    if args.pipeline_dir:
        pipeline_dir = Path(args.pipeline_dir)
    else:
        pipeline_dir = Path(f"extraction_pipeline_{datetime.now().strftime('%Y%m%d')}")

    # Create directory structure
    stages = [
        "01_tei_xml",
        "02_json_extraction",
        "03_zotero_recovery",
        "04_crossref_enrichment",
        "05_s2_enrichment",
        "06_openalex_enrichment",
        "07_unpaywall_enrichment",
        "08_pubmed_enrichment",
        "09_arxiv_enrichment",
        "10_final_output",
    ]

    for stage in stages:
        (pipeline_dir / stage).mkdir(parents=True, exist_ok=True)

    print(f"Pipeline directory: {pipeline_dir}")

    # Define pipeline stages
    pipeline_stages = {
        "tei_extraction": {
            "description": "TEI to JSON extraction",
            "command": f"python comprehensive_tei_extractor.py --input-dir {pipeline_dir}/01_tei_xml --output-dir {pipeline_dir}/02_json_extraction",
            "check": lambda: len(list((pipeline_dir / "02_json_extraction").glob("*.json"))) > 0,
        },
        "zotero": {
            "description": "Zotero metadata recovery",
            "command": f"python run_full_zotero_recovery.py --input {pipeline_dir}/02_json_extraction --output {pipeline_dir}/03_zotero_recovery",
            "check": lambda: len(list((pipeline_dir / "03_zotero_recovery").glob("*.json"))) > 0,
        },
        "crossref": {
            "description": "CrossRef batch enrichment",
            "command": f"python crossref_batch_enrichment.py --input {pipeline_dir}/03_zotero_recovery --output {pipeline_dir}/04_crossref_enrichment --batch-size 50",
            "check": lambda: len(list((pipeline_dir / "04_crossref_enrichment").glob("*.json"))) > 0,
        },
        "s2": {
            "description": "Semantic Scholar enrichment",
            "command": f"python s2_batch_enrichment.py --input {pipeline_dir}/04_crossref_enrichment --output {pipeline_dir}/05_s2_enrichment",
            "check": lambda: len(list((pipeline_dir / "05_s2_enrichment").glob("*.json"))) > 0,
        },
        "openalex": {
            "description": "OpenAlex enrichment",
            "command": f"python v5_openalex_pipeline.py --input {pipeline_dir}/05_s2_enrichment --output {pipeline_dir}/06_openalex_enrichment",
            "check": lambda: len(list((pipeline_dir / "06_openalex_enrichment").glob("*.json"))) > 0,
        },
    }

    # Determine which stages to run
    stage_order = ["tei_extraction", "zotero", "crossref", "s2", "openalex"]
    start_idx = stage_order.index(args.start_from)
    end_idx = stage_order.index(args.stop_after) + 1 if args.stop_after else len(stage_order)

    stages_to_run = stage_order[start_idx:end_idx]

    print(f"\nStages to run: {', '.join(stages_to_run)}")

    # Run pipeline stages
    for stage_name in stages_to_run:
        stage = pipeline_stages[stage_name]

        # Check if stage already completed
        if stage["check"]():
            print(f"\n✓ {stage['description']} already completed, skipping...")
            continue

        # Run the stage
        if not run_command(stage["command"], stage["description"]):
            print(f"\nPipeline stopped at {stage_name}")
            sys.exit(1)

    print("\n" + "=" * 60)
    print("PIPELINE COMPLETED SUCCESSFULLY!")
    print("=" * 60)

    # Print summary
    print("\nPipeline Summary:")
    for stage_dir in sorted(pipeline_dir.glob("*/")):
        count = len(list(stage_dir.glob("*.json"))) + len(list(stage_dir.glob("*.xml")))
        if count > 0:
            print(f"  {stage_dir.name}: {count} files")


if __name__ == "__main__":
    main()
