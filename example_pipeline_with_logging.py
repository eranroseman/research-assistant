#!/usr/bin/env python3
"""Example of how to use the new logging and display system."""

import time
import random
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, "src")

from pipeline_logger import PipelineLogger, PipelineDashboard, MinimalProgressBar


def simulate_crossref_enrichment():
    """Simulate CrossRef enrichment with new logging."""
    # Initialize logging and display
    logger = PipelineLogger("crossref")
    dashboard = PipelineDashboard(total_stages=8)

    # Add all stages to dashboard
    stages = [
        ("CrossRef", 2000),
        ("S2", 2000),
        ("OpenAlex", 2000),
        ("Unpaywall", 2000),
        ("PubMed", 2000),
        ("arXiv", 2000),
        ("TEI", 2000),
        ("PostProc", 2000),
    ]

    for name, total in stages:
        dashboard.add_stage(name, total)

    # Start CrossRef stage
    logger.info("Starting CrossRef enrichment", to_master=True)
    dashboard.update_stage("CrossRef", status="Running", start_time=time.time())

    # Simulate processing papers
    total_papers = 2000
    succeeded = 0
    failed = 0

    for i in range(1, total_papers + 1):
        paper_id = f"paper_{i:04d}"

        # Log detailed processing (file only)
        logger.debug(f"Processing {paper_id}: Loading from disk")
        logger.debug(f"Querying CrossRef API for DOI: 10.1234/test{i}")

        # Simulate success/failure
        if random.random() > 0.05:  # 95% success rate
            succeeded += 1
            logger.success(paper_id, "Enriched with 25 fields")

            # Update dashboard
            dashboard.update_stage(
                "CrossRef", current=i, succeeded=succeeded, failed=failed, current_file=f"{paper_id}.json"
            )

            # Add event occasionally
            if i % 100 == 0:
                dashboard.add_event(f"✓ Batch {i // 100} complete")
        else:
            failed += 1
            error = random.choice(["DOI not found", "API timeout", "Invalid response"])
            logger.failure(paper_id, error)

            dashboard.update_stage("CrossRef", current=i, succeeded=succeeded, failed=failed)

            # Add error event
            if random.random() > 0.8:  # Show some errors
                dashboard.add_event(f"✗ {paper_id}: {error}")

        # Checkpoint every 500
        if i % 500 == 0:
            logger.info(f"Checkpoint saved at {i} papers", to_master=True)
            dashboard.add_event(f"💾 Checkpoint saved ({i} papers)")

        # Simulate processing time
        time.sleep(0.001)  # Speed up for demo

    # Complete stage
    dashboard.update_stage("CrossRef", status="Complete")
    logger.info(f"CrossRef complete: {succeeded} succeeded, {failed} failed", to_master=True)

    # Start next stage
    dashboard.update_stage("S2", status="Running", start_time=time.time())

    # Simulate S2 processing (faster for demo)
    for i in range(1, 501):  # Just show partial progress
        dashboard.update_stage("S2", current=i, succeeded=i - 5, failed=5, current_file=f"paper_{i:04d}.json")
        time.sleep(0.001)

    # Let dashboard stay visible
    time.sleep(2)
    dashboard.finish()


def simulate_minimal_mode():
    """Simulate minimal progress bar mode."""
    print("\nMINIMAL MODE DEMO")
    print("=" * 70)

    # Process each stage with minimal output
    stages = ["CrossRef", "S2", "OpenAlex", "Unpaywall", "PubMed", "arXiv"]

    for stage in stages:
        progress = MinimalProgressBar(stage, 2000)

        succeeded = 0
        failed = 0

        for i in range(1, 2001):
            # Simulate processing
            if random.random() > 0.05:
                succeeded += 1
            else:
                failed += 1

            # Update every 50 papers
            if i % 50 == 0:
                progress.update(i, succeeded, failed)

            time.sleep(0.0001)  # Very fast for demo

        progress.finish()

    print("\nPipeline complete!")


def demonstrate_log_files():
    """Show what gets written to log files."""
    print("\n" + "=" * 70)
    print("LOG FILE CONTENTS DEMO")
    print("=" * 70)

    # Create logger
    logger = PipelineLogger("demo_stage", log_dir=Path("demo_logs"))

    # Show different log levels
    logger.debug("This goes to detailed log only")
    logger.info("This goes to stage log", to_master=False)
    logger.info("This goes to both logs", to_master=True)
    logger.warning("Warnings go to both by default")
    logger.error("Errors go to both by default")

    # Show success/failure logging
    logger.success("paper_001", "Enriched with CrossRef, S2, OpenAlex data")
    logger.failure("paper_002", "DOI not found in any database")

    # Display log file paths
    print("\nLog files created:")
    print(f"  Stage log: demo_logs/{logger.stage_name}_{logger.timestamp}.log")
    print(f"  Master log: demo_logs/pipeline_{logger.timestamp}.log")

    # Show sample content
    print("\nSample stage log content:")
    print("-" * 50)
    stage_log = Path(f"demo_logs/{logger.stage_name}_{logger.timestamp}.log")
    if stage_log.exists():
        with open(stage_log) as f:
            for line in f.readlines()[:5]:
                print(f"  {line.strip()}")

    print("\nSample master log content:")
    print("-" * 50)
    master_log = Path(f"demo_logs/pipeline_{logger.timestamp}.log")
    if master_log.exists():
        with open(master_log) as f:
            for line in f.readlines()[:5]:
                print(f"  {line.strip()}")


def main():
    """Run demonstrations."""
    print("V5 PIPELINE LOGGING AND DISPLAY DEMO")
    print("=" * 70)
    print("\nThis demo shows three display modes:")
    print("1. Full 40-line dashboard (updates in place)")
    print("2. Minimal progress bars (one line per stage)")
    print("3. Log file contents (detailed debugging)")
    print()

    # Ask user which demo to run
    print("Which demo would you like to see?")
    print("1. Dashboard mode (40-line display)")
    print("2. Minimal mode (compact progress bars)")
    print("3. Log files demo")
    print("4. All demos")

    choice = input("\nEnter choice (1-4): ").strip()

    if choice == "1":
        simulate_crossref_enrichment()
    elif choice == "2":
        simulate_minimal_mode()
    elif choice == "3":
        demonstrate_log_files()
    elif choice == "4":
        simulate_crossref_enrichment()
        simulate_minimal_mode()
        demonstrate_log_files()
    else:
        print("Invalid choice")

    # Cleanup demo logs
    import shutil

    if Path("demo_logs").exists():
        shutil.rmtree("demo_logs")
        print("\nDemo logs cleaned up")


if __name__ == "__main__":
    main()
