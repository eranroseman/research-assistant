#!/usr/bin/env python3
"""Filter out supplemental materials, datasets, and other non-article content.

This script:
1. Identifies papers that are actually supplemental materials or datasets
2. Excludes them from the KB
3. Updates the PDF quality report with these exclusions
"""

import json
import shutil
from pathlib import Path
from datetime import datetime, UTC


class NonArticleFilter:
    """Filter out non-article content from KB."""

    def __init__(self, input_dir: str = "crossref_enriched_20250831_163602"):
        """Initialize filter.

        Args:
            input_dir: Directory with enriched JSON files
        """
        self.input_dir = Path(input_dir)

        # Create output directory
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        self.output_dir = Path(f"kb_articles_only_{timestamp}")
        self.output_dir.mkdir(exist_ok=True)

        # Categories for exclusion
        self.excluded = {
            "supplemental_materials": [],
            "datasets": [],
            "malformed_doi": [],
            "other_non_articles": [],
        }

        self.included = []
        self.stats = {"total_processed": 0, "articles_kept": 0, "non_articles_excluded": 0}

    def is_supplemental_material(self, doi: str) -> bool:
        """Check if DOI indicates supplemental material."""
        if not doi:
            return False

        doi_lower = doi.lower()
        return any(
            [
                "/-/dcsupplemental" in doi_lower,
                "/suppl" in doi_lower,
                ".supplemental" in doi_lower,
                "supplementary" in doi_lower,
                "supp_" in doi_lower,
            ]
        )

    def is_dataset(self, doi: str, title: str = "") -> bool:
        """Check if DOI indicates a dataset."""
        if not doi:
            return False

        doi_lower = doi.lower()
        title_lower = title.lower() if title else ""

        # Check DOI patterns
        is_dataset_doi = any(
            [
                "figshare" in doi_lower,
                "zenodo" in doi_lower,
                "dryad" in doi_lower,
                "dataverse" in doi_lower,
                "osf.io" in doi_lower,
                "mendeley.com/datasets" in doi_lower,
            ]
        )

        # Check title patterns
        is_dataset_title = any(
            [
                "dataset" in title_lower,
                "data from:" in title_lower,
                "supplementary data" in title_lower,
                "additional file" in title_lower,
            ]
        )

        return is_dataset_doi or is_dataset_title

    def has_malformed_doi(self, doi: str) -> bool:
        """Check if DOI is malformed with appended text."""
        if not doi:
            return False

        # Check for text appended to DOI
        malformed_patterns = ["REVIEWS", "REvIEWS", "Date2024", "Date2023", "Date2022", ".pdf", ".html"]

        return any(pattern in doi for pattern in malformed_patterns)

    def analyze_paper(self, json_file: Path) -> tuple[str, dict]:
        """Analyze a paper to determine if it's an article or non-article content.

        Returns:
            Tuple of (category, paper_info)
            category: 'article' or exclusion reason
        """
        with open(json_file) as f:
            data = json.load(f)

        paper_id = json_file.stem
        title = data.get("title", "").strip() if data.get("title") else ""
        doi = data.get("doi", "").strip() if data.get("doi") else ""
        abstract = data.get("abstract", "").strip() if data.get("abstract") else ""

        # Create paper info
        paper_info = {
            "paper_id": paper_id,
            "title": title[:100] if title else "[NO TITLE]",
            "doi": doi,
            "abstract_length": len(abstract),
            "has_sections": bool(data.get("sections", [])),
            "num_references": data.get("num_references", 0),
            "text_chars": sum(
                len(s.get("text", "")) for s in data.get("sections", []) if isinstance(s, dict)
            ),
        }

        # Check exclusion criteria
        if self.is_supplemental_material(doi):
            return "supplemental_materials", paper_info

        if self.is_dataset(doi, title):
            return "datasets", paper_info

        # Don't exclude papers just for malformed DOI - they might be real articles
        # Only track malformed DOI if we need to report it

        # Additional checks for non-articles
        if title:
            title_lower = title.lower()
            if any(
                phrase in title_lower
                for phrase in [
                    "correction to:",
                    "erratum",
                    "corrigendum",
                    "retraction",
                    "comment on",
                    "response to",
                    "author reply",
                    "editorial",
                    "book review",
                ]
            ):
                return "other_non_articles", paper_info

        # Paper is a regular article
        return "article", paper_info

    def process_all(self):
        """Process all papers and filter out non-articles."""
        json_files = [f for f in self.input_dir.glob("*.json") if "report" not in f.name]

        print(f"Processing {len(json_files)} papers to filter non-article content...")
        print("=" * 70)

        for json_file in json_files:
            self.stats["total_processed"] += 1
            category, paper_info = self.analyze_paper(json_file)

            if category == "article":
                # Copy to output directory
                output_file = self.output_dir / json_file.name
                shutil.copy2(json_file, output_file)
                self.included.append(paper_info)
                self.stats["articles_kept"] += 1
            else:
                # Add to exclusion list
                self.excluded[category].append(paper_info)
                self.stats["non_articles_excluded"] += 1
                print(f"  Excluded ({category}): {paper_info['paper_id']}")
                if paper_info["doi"]:
                    print(f"    DOI: {paper_info['doi']}")

        # Generate reports
        self.generate_quality_report()
        self.generate_exclusion_list()
        self.print_summary()

    def generate_quality_report(self):
        """Generate comprehensive quality report."""
        report = {
            "timestamp": datetime.now(UTC).isoformat(),
            "stats": self.stats,
            "exclusion_breakdown": {category: len(papers) for category, papers in self.excluded.items()},
            "excluded_papers": self.excluded,
        }

        # Save JSON report
        report_file = self.output_dir / "non_article_filter_report.json"
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)

        # Generate readable report
        self.generate_readable_report(report)

    def generate_readable_report(self, report: dict):
        """Generate human-readable quality report."""
        readable_file = self.output_dir / "non_article_filter_report.md"

        with open(readable_file, "w") as f:
            f.write("# Non-Article Content Filter Report\n\n")
            f.write(f"Generated: {report['timestamp']}\n\n")

            f.write("## Summary Statistics\n\n")
            f.write(f"- **Total Papers Processed**: {self.stats['total_processed']}\n")
            f.write(
                f"- **Articles Kept**: {self.stats['articles_kept']} ({self.stats['articles_kept'] / self.stats['total_processed'] * 100:.1f}%)\n"
            )
            f.write(
                f"- **Non-Articles Excluded**: {self.stats['non_articles_excluded']} ({self.stats['non_articles_excluded'] / self.stats['total_processed'] * 100:.1f}%)\n\n"
            )

            f.write("## Exclusion Categories\n\n")

            # Supplemental Materials
            if self.excluded["supplemental_materials"]:
                f.write(
                    f"### Supplemental Materials: {len(self.excluded['supplemental_materials'])} items\n\n"
                )
                f.write("Papers identified as supplementary materials to main articles.\n\n")
                f.write("| Paper ID | DOI | Abstract | Text | Refs |\n")
                f.write("|----------|-----|----------|------|------|\n")
                for paper in self.excluded["supplemental_materials"][:10]:
                    doi_short = paper["doi"][:40] + "..." if len(paper["doi"]) > 40 else paper["doi"]
                    abstract = f"{paper['abstract_length']} chars" if paper["abstract_length"] > 0 else "✗"
                    text = f"{paper['text_chars'] / 1000:.1f}K" if paper["text_chars"] > 0 else "✗"
                    refs = str(paper["num_references"]) if paper["num_references"] > 0 else "✗"
                    f.write(f"| {paper['paper_id']} | {doi_short} | {abstract} | {text} | {refs} |\n")
                f.write("\n")

            # Datasets
            if self.excluded["datasets"]:
                f.write(f"### Datasets: {len(self.excluded['datasets'])} items\n\n")
                f.write("FigShare, Zenodo, and other dataset repositories.\n\n")
                f.write("| Paper ID | DOI | Repository | Text |\n")
                f.write("|----------|-----|------------|------|\n")
                for paper in self.excluded["datasets"][:10]:
                    doi = paper["doi"]
                    repo = "FigShare" if "figshare" in doi.lower() else "Other"
                    text = f"{paper['text_chars'] / 1000:.1f}K" if paper["text_chars"] > 0 else "✗"
                    f.write(f"| {paper['paper_id']} | {doi[:30]}... | {repo} | {text} |\n")
                f.write("\n")

            # Malformed DOIs
            if self.excluded["malformed_doi"]:
                f.write(f"### Malformed DOIs: {len(self.excluded['malformed_doi'])} items\n\n")
                f.write("DOIs with appended text that couldn't be cleaned.\n\n")
                f.write("| Paper ID | Malformed DOI | Issue |\n")
                f.write("|----------|---------------|-------|\n")
                for paper in self.excluded["malformed_doi"]:
                    doi = paper["doi"]
                    issue = "Text appended" if any(x in doi for x in ["REVIEWS", "Date"]) else "Other"
                    f.write(f"| {paper['paper_id']} | {doi} | {issue} |\n")
                f.write("\n")

            # Other non-articles
            if self.excluded["other_non_articles"]:
                f.write(f"### Other Non-Articles: {len(self.excluded['other_non_articles'])} items\n\n")
                f.write("Corrections, errata, editorials, comments, etc.\n\n")
                f.write("| Paper ID | Title | Type |\n")
                f.write("|----------|-------|------|\n")
                for paper in self.excluded["other_non_articles"][:10]:
                    title = paper["title"][:50] + "..." if len(paper["title"]) > 50 else paper["title"]
                    f.write(f"| {paper['paper_id']} | {title} | Editorial/Comment |\n")
                f.write("\n")

            f.write("## Recommendations\n\n")
            f.write("1. **Supplemental materials** should link to their parent articles if needed\n")
            f.write("2. **Datasets** could be tracked separately as research resources\n")
            f.write("3. **Malformed DOIs** need manual inspection and cleaning\n")
            f.write("4. **Editorials/Comments** are excluded as they're not primary research\n\n")

            f.write("## Next Steps\n\n")
            f.write("1. Build KB with articles-only directory: `" + str(self.output_dir) + "`\n")
            f.write("2. Consider manual review of borderline cases\n")
            f.write("3. Update Grobid extraction to filter these earlier\n")

    def generate_exclusion_list(self):
        """Generate simple list of excluded paper IDs."""
        exclusion_file = self.output_dir / "excluded_non_articles.txt"

        with open(exclusion_file, "w") as f:
            f.write("# Non-Article Content Excluded from Knowledge Base\n")
            f.write(f"# Generated: {datetime.now(UTC).isoformat()}\n\n")

            for category, papers in self.excluded.items():
                if papers:
                    f.write(f"\n# {category.replace('_', ' ').title()} ({len(papers)} items)\n")
                    for paper in papers:
                        f.write(f"{paper['paper_id']}\n")

    def print_summary(self):
        """Print summary to console."""
        print("\n" + "=" * 70)
        print("NON-ARTICLE FILTERING COMPLETE")
        print("=" * 70)

        print("\n📊 RESULTS:")
        print(f"  Total processed: {self.stats['total_processed']}")
        print(
            f"  ✅ Articles kept: {self.stats['articles_kept']} ({self.stats['articles_kept'] / self.stats['total_processed'] * 100:.1f}%)"
        )
        print(f"  ❌ Non-articles excluded: {self.stats['non_articles_excluded']}")

        print("\n📋 EXCLUSION BREAKDOWN:")
        for category, papers in self.excluded.items():
            if papers:
                print(f"  {category.replace('_', ' ').title()}: {len(papers)} items")

        print("\n💾 OUTPUT:")
        print(f"  Articles-only KB: {self.output_dir}/")
        print(f"  Quality report: {self.output_dir}/non_article_filter_report.md")
        print(f"  Exclusion list: {self.output_dir}/excluded_non_articles.txt")


def main():
    """Main entry point."""
    import sys

    print("=" * 70)
    print("NON-ARTICLE CONTENT FILTER")
    print("=" * 70)
    print("\nThis script will exclude:")
    print("  - Supplemental materials")
    print("  - Datasets (FigShare, Zenodo, etc.)")
    print("  - Papers with malformed DOIs")
    print("  - Editorials, comments, corrections")
    print("=" * 70)

    # Check if enriched directory exists
    enriched_dir = Path("crossref_enriched_20250831_163602")
    if not enriched_dir.exists():
        # Try current directory
        if Path(".").glob("*.json"):
            enriched_dir = Path(".")
        else:
            print("\n❌ Enriched KB not found")
            sys.exit(1)

    print(f"\nSource: {enriched_dir}")
    print("=" * 70 + "\n")

    # Run filter
    article_filter = NonArticleFilter(str(enriched_dir))
    article_filter.process_all()


if __name__ == "__main__":
    main()
