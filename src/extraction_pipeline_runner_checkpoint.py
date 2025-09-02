#!/usr/bin/env python3
"""Extraction Pipeline Runner with full checkpoint support.

This enhanced version uses checkpoint-enabled scripts for all stages,
allowing seamless resume after interruptions.
"""

from src import config
import sys
import subprocess
import shlex
from pathlib import Path
from datetime import datetime, UTC
import argparse
import time
import json
from typing import Any


def wait_for_stage_completion(
    output_dir: Path, expected_count: int | None = None, timeout: int = 300, stage_name: str = ""
) -> int:
    """Wait for a stage to complete by monitoring file count stability."""
    print(f"Waiting for {stage_name} to complete...")

    stable_count = 0
    stable_iterations = 0
    required_stable_iterations = 3  # Need 3 consecutive checks with same count

    start_time = time.time()
    while time.time() - start_time < timeout:
        current_count = len(list(output_dir.glob("*.json")))

        if current_count == stable_count:
            stable_iterations += 1
            if stable_iterations >= required_stable_iterations:
                print(f"✓ Stage stabilized with {current_count} files")
                return current_count
        else:
            stable_count = current_count
            stable_iterations = 0

        print(f"  Current file count: {current_count}")
        time.sleep(2)

    print(f"Warning: Stage timeout after {timeout}s with {stable_count} files")
    return stable_count


def run_command_sync(
    cmd: str | list[str], description: str, output_dir: Path, input_dir: Path | None = None
) -> bool:
    """Run a command synchronously and wait for completion."""
    print(f"\n{'=' * 60}")
    print(f"Running: {description}")
    print(f"Command: {cmd}")
    print("=" * 60)

    # Count input files if provided
    input_count = 0
    if input_dir and input_dir.exists():
        # Exclude report and checkpoint files
        input_count = len(
            [f for f in input_dir.glob("*.json") if "report" not in f.name and not f.name.startswith(".")]
        )
        print(f"Input files: {input_count}")

    # Convert string command to list for security
    if isinstance(cmd, str):
        cmd = shlex.split(cmd)

    # Run the command and wait for it to complete
    result = subprocess.run(cmd, check=False, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"ERROR: {description} failed!")
        print(result.stderr)
        return False

    # Wait for files to appear and stabilize
    if output_dir.exists():
        output_count = wait_for_stage_completion(
            output_dir, expected_count=input_count, stage_name=description
        )

        # Verify reasonable output count
        if input_count > 0:
            loss_rate = (input_count - output_count) / input_count
            if loss_rate > config.LOW_CONFIDENCE_THRESHOLD:  # Alert if >25% file loss
                print(
                    f"⚠ Warning: Significant file loss detected ({input_count} → {output_count}, {loss_rate * 100:.1f}% loss)"
                )
                print("This may indicate incomplete processing. Consider re-running this stage.")

    print(f"✓ {description} completed successfully")
    return True


def verify_stage_completion(stage_dir: Path, min_files: int = 1) -> bool:
    """Verify a stage has completed with expected output."""
    if not stage_dir.exists():
        return False

    json_files = [
        f for f in stage_dir.glob("*.json") if "report" not in f.name and not f.name.startswith(".")
    ]
    xml_files = list(stage_dir.glob("*.xml"))

    total_files = len(json_files) + len(xml_files)
    return total_files >= min_files


def main() -> None:
    """Run the main program."""
    parser = argparse.ArgumentParser(description="Run extraction pipeline with checkpoint support")
    parser.add_argument(
        "--pipeline-dir",
        default=None,
        help="Pipeline directory (default: extraction_pipeline_checkpoint_YYYYMMDD)",
    )
    parser.add_argument(
        "--start-from",
        default="tei_extraction",
        choices=["tei_extraction", "zotero", "crossref", "s2", "openalex", "unpaywall", "pubmed", "arxiv"],
        help="Start from specific stage",
    )
    parser.add_argument(
        "--stop-after",
        default=None,
        choices=["tei_extraction", "zotero", "crossref", "s2", "openalex", "unpaywall", "pubmed", "arxiv"],
        help="Stop after specific stage",
    )
    parser.add_argument("--force", action="store_true", help="Force re-run even if stage appears complete")
    parser.add_argument(
        "--reset-checkpoints", action="store_true", help="Reset all checkpoints and start fresh"
    )

    args = parser.parse_args()

    # Set up pipeline directory
    if args.pipeline_dir:
        pipeline_dir = Path(args.pipeline_dir)
    else:
        pipeline_dir = Path(f"extraction_pipeline_checkpoint_{datetime.now(UTC).strftime('%Y%m%d')}")

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
    print("Checkpoint support: ENABLED for all stages")

    if args.reset_checkpoints:
        print("⚠ Will reset all checkpoints and start fresh")

    # Add reset flag to commands if requested
    reset_flag = " --reset" if args.reset_checkpoints else ""

    # Define pipeline stages with checkpoint-enabled scripts
    pipeline_stages: dict[str, dict[str, Any]] = {
        "tei_extraction": {
            "description": "TEI to JSON extraction (with checkpoint)",
            "command": f"python comprehensive_tei_extractor_checkpoint.py --input-dir {pipeline_dir}/01_tei_xml --output-dir {pipeline_dir}/02_json_extraction{reset_flag}",
            "input_dir": pipeline_dir / "01_tei_xml",
            "output_dir": pipeline_dir / "02_json_extraction",
        },
        "zotero": {
            "description": "Zotero metadata recovery (with checkpoint)",
            "command": f"python run_full_zotero_recovery.py --input {pipeline_dir}/02_json_extraction --output {pipeline_dir}/03_zotero_recovery{reset_flag}",
            "input_dir": pipeline_dir / "02_json_extraction",
            "output_dir": pipeline_dir / "03_zotero_recovery",
        },
        "crossref": {
            "description": "CrossRef batch enrichment (with checkpoint)",
            "command": f"python crossref_batch_enrichment_checkpoint.py --input {pipeline_dir}/03_zotero_recovery --output {pipeline_dir}/04_crossref_enrichment --batch-size 50{reset_flag}",
            "input_dir": pipeline_dir / "03_zotero_recovery",
            "output_dir": pipeline_dir / "04_crossref_enrichment",
        },
        "s2": {
            "description": "Semantic Scholar enrichment (with checkpoint)",
            "command": f"python s2_batch_enrichment.py --input {pipeline_dir}/04_crossref_enrichment --output {pipeline_dir}/05_s2_enrichment",
            "input_dir": pipeline_dir / "04_crossref_enrichment",
            "output_dir": pipeline_dir / "05_s2_enrichment",
        },
        "openalex": {
            "description": "OpenAlex enrichment",
            "command": f"python v5_openalex_pipeline.py --input {pipeline_dir}/05_s2_enrichment --output {pipeline_dir}/06_openalex_enrichment",
            "input_dir": pipeline_dir / "05_s2_enrichment",
            "output_dir": pipeline_dir / "06_openalex_enrichment",
        },
        "unpaywall": {
            "description": "Unpaywall OA discovery (with checkpoint)",
            "command": f"python v5_unpaywall_pipeline.py --input {pipeline_dir}/06_openalex_enrichment --output {pipeline_dir}/07_unpaywall_enrichment --email eran-roseman@uiowa.edu",
            "input_dir": pipeline_dir / "06_openalex_enrichment",
            "output_dir": pipeline_dir / "07_unpaywall_enrichment",
        },
        "pubmed": {
            "description": "PubMed enrichment (with checkpoint)",
            "command": f"python v5_pubmed_pipeline.py --input {pipeline_dir}/07_unpaywall_enrichment --output {pipeline_dir}/08_pubmed_enrichment",
            "input_dir": pipeline_dir / "07_unpaywall_enrichment",
            "output_dir": pipeline_dir / "08_pubmed_enrichment",
        },
        "arxiv": {
            "description": "arXiv enrichment",
            "command": f"python v5_arxiv_pipeline.py --input {pipeline_dir}/08_pubmed_enrichment --output {pipeline_dir}/09_arxiv_enrichment",
            "input_dir": pipeline_dir / "08_pubmed_enrichment",
            "output_dir": pipeline_dir / "09_arxiv_enrichment",
        },
    }

    # Determine which stages to run
    stage_order = ["tei_extraction", "zotero", "crossref", "s2", "openalex", "unpaywall", "pubmed", "arxiv"]
    start_idx = stage_order.index(args.start_from)
    end_idx = stage_order.index(args.stop_after) + 1 if args.stop_after else len(stage_order)

    stages_to_run = stage_order[start_idx:end_idx]

    print(f"\nStages to run: {', '.join(stages_to_run)}")
    print("\nCheckpoint Status by Stage:")
    print("-" * 60)

    # Check for existing checkpoints
    for stage_name in stages_to_run:
        stage_check_info = pipeline_stages[stage_name]
        checkpoint_files = list(stage_check_info["output_dir"].glob(".*checkpoint*.json"))
        if checkpoint_files:
            print(f"  {stage_name}: ✓ Checkpoint exists")
        else:
            print(f"  {stage_name}: ✗ No checkpoint")

    # Track file counts through pipeline
    file_counts: dict[str, int] = {}

    # Run pipeline stages
    for stage_name in stages_to_run:
        stage_info: dict[str, Any] = pipeline_stages[stage_name]

        # Check if stage already completed (unless forcing)
        if not args.force and verify_stage_completion(stage_info["output_dir"], min_files=100):
            existing_count = len(
                [
                    f
                    for f in stage_info["output_dir"].glob("*.json")
                    if "report" not in f.name and not f.name.startswith(".")
                ]
            )
            print(f"\n✓ {stage_info['description']} already has {existing_count} files")

            # Check for checkpoint
            checkpoint_files = list(stage_info["output_dir"].glob(".*checkpoint*.json"))
            if checkpoint_files:
                print("  Checkpoint found - will resume from where it left off if re-run")

            file_counts[stage_name] = existing_count
            continue

        # Run the stage synchronously
        if not run_command_sync(
            stage_info["command"],
            stage_info["description"],
            stage_info["output_dir"],
            stage_info.get("input_dir"),
        ):
            print(f"\nPipeline stopped at {stage_name}")
            print("Note: You can resume from this point thanks to checkpoint support!")
            sys.exit(1)

        # Record output count
        output_count = len(
            [
                f
                for f in stage_info["output_dir"].glob("*.json")
                if "report" not in f.name and not f.name.startswith(".")
            ]
        )
        file_counts[stage_name] = output_count

    print("\n" + "=" * 60)
    print("PIPELINE COMPLETED SUCCESSFULLY!")
    print("=" * 60)

    # Print detailed summary
    print("\nPipeline Summary:")
    print("-" * 60)
    print(f"{'Stage':<30} {'Files':<10} {'Status'}")
    print("-" * 60)

    for stage_dir in sorted(pipeline_dir.glob("*/")):
        json_count = len(
            [f for f in stage_dir.glob("*.json") if "report" not in f.name and not f.name.startswith(".")]
        )
        xml_count = len(list(stage_dir.glob("*.xml")))
        total_count = json_count + xml_count

        if total_count > 0:
            status = "✓ Complete"

            # Check for checkpoint
            checkpoint_files = list(stage_dir.glob(".*checkpoint*.json"))
            if checkpoint_files:
                status += " (checkpoint saved)"

            # Check for significant file loss
            if stage_dir.name in ["03_zotero_recovery", "04_crossref_enrichment"]:
                prev_stage = {
                    "03_zotero_recovery": "02_json_extraction",
                    "04_crossref_enrichment": "03_zotero_recovery",
                }.get(stage_dir.name)

                if prev_stage:
                    prev_dir = pipeline_dir / prev_stage
                    prev_count = len(
                        [
                            f
                            for f in prev_dir.glob("*.json")
                            if "report" not in f.name and not f.name.startswith(".")
                        ]
                    )
                    if prev_count > 0:
                        loss_rate = (prev_count - total_count) / prev_count
                        if loss_rate > config.VERY_LOW_THRESHOLD:  # >5% loss
                            status = f"⚠ {loss_rate * 100:.1f}% loss"

            print(f"{stage_dir.name:<30} {total_count:<10} {status}")

    # Final statistics
    print("\n" + "=" * 60)
    print("File Count Tracking:")
    for stage, count in file_counts.items():
        print(f"  {stage}: {count} files")

    # Save pipeline report
    report = {
        "timestamp": datetime.now(UTC).isoformat(),
        "pipeline_dir": str(pipeline_dir),
        "stages_run": stages_to_run,
        "file_counts": file_counts,
        "checkpoint_enabled": True,
        "checkpoints_reset": args.reset_checkpoints,
        "summary": {
            "initial_files": file_counts.get("tei_extraction", 0),
            "final_files": file_counts.get(stages_to_run[-1], 0),
            "retention_rate": file_counts.get(stages_to_run[-1], 0)
            / max(file_counts.get("tei_extraction", 1), 1)
            * 100,
        },
    }

    report_path = pipeline_dir / "pipeline_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nReport saved to: {report_path}")

    print("\n" + "=" * 60)
    print("CHECKPOINT SUPPORT ENABLED")
    print("=" * 60)
    print("This pipeline can be safely interrupted and resumed at any time.")
    print("Each stage will automatically continue from where it left off.")
    print("Use --reset-checkpoints to start completely fresh.")


if __name__ == "__main__":
    main()
