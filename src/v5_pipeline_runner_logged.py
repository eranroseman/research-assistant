#!/usr/bin/env python3
"""V5 Pipeline Runner with unified 40-line dashboard display.

Coordinates all enrichment stages with a single dashboard that shows
the complete pipeline status in 40 lines that update in place.
"""

import json
import time
import sys
from pathlib import Path
import argparse
import subprocess

from src import config
from src.pipeline_logger import PipelineLogger, PipelineDashboard


class V5PipelineRunner:
    """Unified pipeline runner with dashboard display."""

    def __init__(self, display_mode: str = "dashboard", force: bool = False):
        """Initialize pipeline runner.

        Args:
            display_mode: "dashboard", "minimal", or "quiet"
            force: Force re-enrichment even if data exists
        """
        self.display_mode = display_mode
        self.force = force
        self.logger = PipelineLogger("pipeline")
        self.dashboard = None
        self.stages_config = self._get_stages_config()

    def _get_stages_config(self) -> list[dict]:
        """Get configuration for all pipeline stages."""
        return [
            {
                "name": "CrossRef",
                "script": "src/crossref_enricher_v5_logged.py",
                "input": "extraction_pipeline/02_json_extraction",
                "output": "extraction_pipeline/04_crossref_enrichment",
                "checkpoint_interval": config.FAST_API_CHECKPOINT_INTERVAL,
                "estimated_time": 240,  # 4 minutes for 2000 papers
            },
            {
                "name": "S2",
                "script": "src/semantic_scholar_enricher.py",
                "input": "extraction_pipeline/04_crossref_enrichment",
                "output": "extraction_pipeline/05_s2_enrichment",
                "checkpoint_interval": config.FAST_API_CHECKPOINT_INTERVAL,
                "estimated_time": 75,  # 1.25 minutes
            },
            {
                "name": "OpenAlex",
                "script": "src/openalex_enricher.py",
                "input": "extraction_pipeline/05_s2_enrichment",
                "output": "extraction_pipeline/06_openalex_enrichment",
                "checkpoint_interval": 50,  # OpenAlex has different rate limit
                "estimated_time": 225,  # 3.75 minutes
            },
            {
                "name": "Unpaywall",
                "script": "src/unpaywall_enricher.py",
                "input": "extraction_pipeline/06_openalex_enrichment",
                "output": "extraction_pipeline/07_unpaywall_enrichment",
                "checkpoint_interval": config.MEDIUM_API_CHECKPOINT_INTERVAL,
                "estimated_time": 140,  # 2.3 minutes
            },
            {
                "name": "PubMed",
                "script": "src/pubmed_enricher.py",
                "input": "extraction_pipeline/07_unpaywall_enrichment",
                "output": "extraction_pipeline/08_pubmed_enrichment",
                "checkpoint_interval": config.MEDIUM_API_CHECKPOINT_INTERVAL,
                "estimated_time": 370,  # 6.2 minutes
            },
            {
                "name": "arXiv",
                "script": "src/arxiv_enricher.py",
                "input": "extraction_pipeline/08_pubmed_enrichment",
                "output": "extraction_pipeline/09_arxiv_enrichment",
                "checkpoint_interval": 100,  # arXiv with batch processing
                "estimated_time": 600,  # 10 minutes with new batch mode
            },
            {
                "name": "TEI",
                "script": "src/comprehensive_tei_extractor.py",
                "input": "extraction_pipeline/01_tei_xml",
                "output": "extraction_pipeline/02_json_extraction",
                "checkpoint_interval": 1000,  # Local processing, fast
                "estimated_time": 90,  # 1.5 minutes
            },
            {
                "name": "PostProc",
                "script": "src/grobid_post_processor.py",
                "input": "extraction_pipeline/09_arxiv_enrichment",
                "output": "extraction_pipeline/10_final_output",
                "checkpoint_interval": 1000,  # Local processing
                "estimated_time": 495,  # 8.25 minutes
            },
        ]

    def count_papers(self, directory: Path) -> int:
        """Count JSON papers in a directory."""
        count = 0
        if directory.exists():
            for json_file in directory.rglob("*.json"):
                count += 1
        return count

    def get_stage_stats(self, stage_config: dict) -> dict:
        """Get statistics for a stage."""
        output_dir = Path(stage_config["output"])
        checkpoint_file = output_dir / f".{stage_config['name'].lower()}_checkpoint.json"

        stats = {"current": 0, "succeeded": 0, "failed": 0, "status": "Waiting"}

        # Count output files
        if output_dir.exists():
            stats["current"] = self.count_papers(output_dir)

        # Load checkpoint for detailed stats
        if checkpoint_file.exists():
            try:
                with open(checkpoint_file) as f:
                    checkpoint = json.load(f)
                    if "stats" in checkpoint:
                        stats["succeeded"] = checkpoint["stats"].get("enriched", 0)
                        stats["failed"] = checkpoint["stats"].get("errors", 0)
            except:
                pass

        return stats

    def run_stage(self, stage_config: dict, total_papers: int) -> bool:
        """Run a single pipeline stage.

        Returns:
            True if successful, False otherwise
        """
        stage_name = stage_config["name"]
        self.logger.info(f"Starting {stage_name} stage", to_master=True)

        # Update dashboard
        if self.dashboard:
            self.dashboard.update_stage(stage_name, status="Running", start_time=time.time())
            self.dashboard.add_event(f"▶ Starting {stage_name} enrichment")

        # Build command
        cmd = [
            sys.executable,
            stage_config["script"],
            "--input",
            stage_config["input"],
            "--output",
            stage_config["output"],
        ]

        if self.force:
            cmd.append("--force")

        # Add display mode for stages that support it
        if stage_name == "CrossRef":  # Only CrossRef supports display mode so far
            cmd.extend(["--display", "quiet"])  # Use quiet since we have main dashboard

        try:
            # Run the stage script
            self.logger.info(f"Running: {' '.join(cmd)}", to_master=False)

            # Run with real-time output capture for dashboard updates
            process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1
            )

            # Monitor progress
            last_update = time.time()
            while True:
                # Check if process is still running
                poll = process.poll()
                if poll is not None:
                    break

                # Update stats periodically
                if time.time() - last_update > 2:  # Every 2 seconds
                    stats = self.get_stage_stats(stage_config)
                    if self.dashboard:
                        self.dashboard.update_stage(
                            stage_name,
                            current=stats["current"],
                            succeeded=stats["succeeded"],
                            failed=stats["failed"],
                        )
                    last_update = time.time()

                time.sleep(0.5)

            # Get final return code
            returncode = process.returncode

            if returncode == 0:
                # Success
                final_stats = self.get_stage_stats(stage_config)
                self.logger.info(
                    f"{stage_name} complete: {final_stats['succeeded']} succeeded, "
                    f"{final_stats['failed']} failed",
                    to_master=True,
                )

                if self.dashboard:
                    self.dashboard.update_stage(stage_name, status="Complete")
                    self.dashboard.add_event(f"✓ {stage_name}: {final_stats['succeeded']} enriched")
                return True
            # Failure
            self.logger.error(f"{stage_name} failed with code {returncode}", to_master=True)
            if self.dashboard:
                self.dashboard.update_stage(stage_name, status="Failed")
                self.dashboard.add_event(f"✗ {stage_name} failed")
            return False

        except Exception as e:
            self.logger.error(f"Error running {stage_name}: {e}", to_master=True)
            if self.dashboard:
                self.dashboard.update_stage(stage_name, status="Failed")
                self.dashboard.add_event(f"✗ {stage_name}: {str(e)[:50]}")
            return False

    def run(self, start_stage: str | None = None, end_stage: str | None = None):
        """Run the complete pipeline.

        Args:
            start_stage: Stage name to start from (inclusive)
            end_stage: Stage name to end at (inclusive)
        """
        # Determine total papers from initial input
        initial_input = Path("extraction_pipeline/02_json_extraction")
        total_papers = self.count_papers(initial_input)

        if total_papers == 0:
            self.logger.error("No papers found in input directory!", to_master=True)
            return

        self.logger.info(f"Starting V5 pipeline with {total_papers} papers", to_master=True)

        # Setup display
        if self.display_mode == "dashboard" and sys.stdout.isatty():
            self.dashboard = PipelineDashboard(total_stages=8)
            # Add all stages
            for stage_config in self.stages_config:
                self.dashboard.add_stage(stage_config["name"], total_papers)
                # Load existing stats
                stats = self.get_stage_stats(stage_config)
                self.dashboard.update_stage(
                    stage_config["name"],
                    current=stats["current"],
                    succeeded=stats["succeeded"],
                    failed=stats["failed"],
                    status="Complete" if stats["current"] >= total_papers else "Waiting",
                )

        # Determine stages to run
        stages_to_run = self.stages_config
        if start_stage:
            start_idx = next((i for i, s in enumerate(stages_to_run) if s["name"] == start_stage), 0)
            stages_to_run = stages_to_run[start_idx:]
        if end_stage:
            end_idx = next(
                (i for i, s in enumerate(stages_to_run) if s["name"] == end_stage), len(stages_to_run) - 1
            )
            stages_to_run = stages_to_run[: end_idx + 1]

        # Run stages
        pipeline_start = time.time()
        failed_stage = None

        for stage_config in stages_to_run:
            # Skip TEI and PostProc for API enrichment pipeline
            if stage_config["name"] in ["TEI", "PostProc"] and not self.force:
                self.logger.info(f"Skipping {stage_config['name']} (not part of enrichment)", to_master=False)
                continue

            # Check if stage needs to run
            stats = self.get_stage_stats(stage_config)
            if not self.force and stats["current"] >= total_papers * 0.95:
                self.logger.info(
                    f"Skipping {stage_config['name']}: already processed "
                    f"{stats['current']}/{total_papers} papers",
                    to_master=True,
                )
                if self.dashboard:
                    self.dashboard.add_event(f"⏭ {stage_config['name']}: already complete")
                continue

            # Run the stage
            success = self.run_stage(stage_config, total_papers)
            if not success:
                failed_stage = stage_config["name"]
                break

        # Final summary
        pipeline_time = time.time() - pipeline_start
        hours = int(pipeline_time / 3600)
        minutes = int((pipeline_time % 3600) / 60)
        seconds = int(pipeline_time % 60)

        if failed_stage:
            self.logger.error(
                f"Pipeline stopped at {failed_stage} after {hours}h {minutes}m {seconds}s", to_master=True
            )
        else:
            self.logger.info(f"Pipeline complete in {hours}h {minutes}m {seconds}s", to_master=True)

        # Gather final statistics
        total_processed = 0
        total_succeeded = 0
        total_failed = 0

        for stage_config in self.stages_config:
            stats = self.get_stage_stats(stage_config)
            if stats["current"] > 0:
                total_processed += stats["current"]
                total_succeeded += stats["succeeded"]
                total_failed += stats["failed"]

        # Print summary
        print("\n" + "=" * 70)
        print("PIPELINE SUMMARY")
        print("=" * 70)
        print(f"Total time: {hours}h {minutes}m {seconds}s")
        print(f"Papers processed: {total_papers}")
        print(f"Total enrichments: {total_processed}")
        print(
            f"Success rate: {(total_succeeded / total_processed * 100):.1f}%"
            if total_processed > 0
            else "N/A"
        )
        print("=" * 70)

        # Stage breakdown
        print("\nStage Results:")
        for stage_config in self.stages_config:
            stats = self.get_stage_stats(stage_config)
            if stats["current"] > 0:
                print(
                    f"  {stage_config['name']:12s}: {stats['succeeded']:4d} succeeded, "
                    f"{stats['failed']:4d} failed"
                )

        if self.dashboard:
            self.dashboard.finish()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="V5 Pipeline Runner with unified dashboard")
    parser.add_argument(
        "--display",
        choices=["dashboard", "minimal", "quiet"],
        default="dashboard",
        help="Display mode: dashboard (40-line), minimal (progress bars), or quiet",
    )
    parser.add_argument(
        "--force", action="store_true", help="Force re-enrichment even if data already exists"
    )
    parser.add_argument("--start", help="Stage to start from (e.g., 'CrossRef', 'S2')")
    parser.add_argument("--end", help="Stage to end at (e.g., 'OpenAlex', 'arXiv')")

    args = parser.parse_args()

    # Run pipeline
    runner = V5PipelineRunner(display_mode=args.display, force=args.force)
    runner.run(start_stage=args.start, end_stage=args.end)


if __name__ == "__main__":
    main()
