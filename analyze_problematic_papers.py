#!/usr/bin/env python3
"""Comprehensive analysis of problematic papers for removal from knowledge base.

This script analyzes the existing extraction data to identify:
1. Papers with complete GROBID failures (17 papers identified earlier)
2. Non-research documents (supplementary materials, checklists, grey literature)
3. Papers with minimal content or metadata
4. Any other quality issues that should exclude papers from the KB

Usage:
    python analyze_problematic_papers.py [--directory PATH]
"""

import json
import argparse
from pathlib import Path
from datetime import datetime, UTC
from typing import Any
from collections import defaultdict


class ProblematicPaperAnalyzer:
    """Analyze extraction data to identify papers for removal."""

    def __init__(self, data_dir: str = "kb_final_cleaned_20250831_170352"):
        """Initialize analyzer with data directory."""
        self.data_dir = Path(data_dir)
        if not self.data_dir.exists():
            raise ValueError(f"Data directory not found: {data_dir}")

        self.problems = {
            "grobid_failures": [],
            "non_articles": [],
            "minimal_content": [],
            "metadata_issues": [],
            "quality_issues": [],
            "corrupted_data": [],
        }

        self.stats = {"total_papers": 0, "problematic_papers": 0, "by_category": defaultdict(int)}

    def analyze_paper(self, json_file: Path) -> tuple[str, dict[str, Any]]:
        """Analyze a single paper for quality issues.

        Returns:
            Tuple of (category, detailed_info)
            category: 'ok' if good, else problem category
        """
        try:
            with open(json_file) as f:
                data = json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            return "corrupted_data", {
                "paper_id": json_file.stem,
                "error": f"JSON decode error: {e!s}",
                "file_size": json_file.stat().st_size,
            }

        paper_id = json_file.stem

        # Basic metadata extraction
        title = data.get("title", "").strip()
        doi = data.get("doi", "").strip()
        abstract = data.get("abstract", "").strip()
        authors = data.get("authors", [])
        year = data.get("year", "")
        journal = data.get("journal", "").strip()
        sections = data.get("sections", [])
        references = data.get("references", [])

        # Calculate text metrics
        total_text = sum(len(s.get("text", "")) for s in sections if isinstance(s, dict) and s.get("text"))

        abstract_length = len(abstract)
        num_sections = len([s for s in sections if isinstance(s, dict) and s.get("text")])
        num_references = len(references) if isinstance(references, list) else 0

        paper_info = {
            "paper_id": paper_id,
            "title": title[:100] if title else "[NO TITLE]",
            "title_length": len(title),
            "doi": doi,
            "abstract_length": abstract_length,
            "authors_count": len(authors) if isinstance(authors, list) else 0,
            "year": str(year),
            "journal": journal[:50] if journal else "[NO JOURNAL]",
            "num_sections": num_sections,
            "total_text_chars": total_text,
            "num_references": num_references,
            "file_size": json_file.stat().st_size,
            "has_sections": bool(sections),
            "section_types": [s.get("type", "unknown") for s in sections[:5] if isinstance(s, dict)],
        }

        # Check for GROBID failures - papers that couldn't be extracted at all
        if (
            not sections
            or (num_sections == 0 and total_text < 100)
            or (total_text < 500 and abstract_length < 100 and not title)
        ):
            return "grobid_failures", paper_info

        # Check for non-research articles
        if title:
            title_lower = title.lower()
            non_article_indicators = [
                "editorial",
                "comment on",
                "response to",
                "erratum",
                "corrigendum",
                "retraction",
                "correction to",
                "book review",
                "conference report",
                "meeting report",
                "news",
                "announcement",
                "letter to editor",
                "author reply",
                "author response",
            ]

            if any(indicator in title_lower for indicator in non_article_indicators):
                return "non_articles", paper_info

        # Check DOI for supplementary materials or datasets
        if doi:
            doi_lower = doi.lower()
            if any(
                pattern in doi_lower
                for pattern in [
                    "dcsupplemental",
                    "supplemental",
                    "supplement",
                    "figshare",
                    "zenodo",
                    "dryad",
                    "dataverse",
                    "osf.io",
                ]
            ):
                return "non_articles", paper_info

        # Check for minimal content papers
        if total_text < 1000 and abstract_length < 200:
            return "minimal_content", paper_info

        # Check for critical metadata issues
        if not title and not doi:
            return "metadata_issues", paper_info

        # Check for potential quality issues
        quality_issues = []

        # Very short papers (likely abstracts only)
        if total_text < 2000 and num_sections < 3:
            quality_issues.append("very_short")

        # No abstract and no substantial text
        if abstract_length < 50 and total_text < 3000:
            quality_issues.append("no_abstract_minimal_text")

        # No references (unusual for research papers)
        if num_references == 0:
            quality_issues.append("no_references")

        # Missing year (problematic for citations)
        if not year or year == "":
            quality_issues.append("no_year")

        # Suspicious title patterns
        if title and len(title) < 10:
            quality_issues.append("very_short_title")

        if quality_issues:
            paper_info["quality_issues"] = quality_issues
            return "quality_issues", paper_info

        # Paper seems OK
        return "ok", paper_info

    def analyze_all_papers(self):
        """Analyze all papers in the data directory."""
        json_files = [
            f
            for f in self.data_dir.glob("*.json")
            if not any(keyword in f.name.lower() for keyword in ["report", "summary", "log", "excluded"])
        ]

        self.stats["total_papers"] = len(json_files)

        print(f"Analyzing {len(json_files)} papers for quality issues...")
        print("=" * 70)

        for json_file in json_files:
            category, paper_info = self.analyze_paper(json_file)

            if category != "ok":
                self.problems[category].append(paper_info)
                self.stats["problematic_papers"] += 1
                self.stats["by_category"][category] += 1

                print(f"  ISSUE ({category}): {paper_info['paper_id']}")
                if paper_info.get("title") and paper_info["title"] != "[NO TITLE]":
                    print(f"    Title: {paper_info['title']}")
                if paper_info.get("doi"):
                    print(f"    DOI: {paper_info['doi']}")
                print(
                    f"    Text: {paper_info['total_text_chars']} chars, "
                    f"Sections: {paper_info['num_sections']}"
                )

    def generate_comprehensive_report(self):
        """Generate comprehensive analysis report."""
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")

        # Generate JSON report
        json_report = {
            "timestamp": timestamp,
            "analysis_directory": str(self.data_dir),
            "statistics": dict(self.stats),
            "problems_by_category": {
                category: papers for category, papers in self.problems.items() if papers
            },
            "removal_recommendations": self._generate_removal_recommendations(),
        }

        json_report_path = Path(f"problematic_papers_analysis_{timestamp}.json")
        with open(json_report_path, "w") as f:
            json.dump(json_report, f, indent=2)

        # Generate markdown report
        md_report_path = Path(f"problematic_papers_analysis_{timestamp}.md")
        self._generate_markdown_report(md_report_path, json_report)

        # Generate removal list
        removal_list_path = Path(f"papers_to_remove_{timestamp}.txt")
        self._generate_removal_list(removal_list_path)

        return json_report_path, md_report_path, removal_list_path

    def _generate_removal_recommendations(self) -> dict[str, Any]:
        """Generate specific removal recommendations."""
        recommendations = {}

        # GROBID failures - remove all
        if self.problems["grobid_failures"]:
            recommendations["grobid_failures"] = {
                "action": "REMOVE",
                "reason": "Complete extraction failure - no usable content",
                "count": len(self.problems["grobid_failures"]),
                "paper_ids": [p["paper_id"] for p in self.problems["grobid_failures"]],
            }

        # Non-articles - remove all
        if self.problems["non_articles"]:
            recommendations["non_articles"] = {
                "action": "REMOVE",
                "reason": "Not research papers - editorials, datasets, supplements",
                "count": len(self.problems["non_articles"]),
                "paper_ids": [p["paper_id"] for p in self.problems["non_articles"]],
            }

        # Minimal content - remove
        if self.problems["minimal_content"]:
            recommendations["minimal_content"] = {
                "action": "REMOVE",
                "reason": "Insufficient content - likely abstract-only or failed extraction",
                "count": len(self.problems["minimal_content"]),
                "paper_ids": [p["paper_id"] for p in self.problems["minimal_content"]],
            }

        # Metadata issues - remove if critical
        if self.problems["metadata_issues"]:
            critical_metadata = [
                p for p in self.problems["metadata_issues"] if not p.get("title") and not p.get("doi")
            ]
            if critical_metadata:
                recommendations["critical_metadata_issues"] = {
                    "action": "REMOVE",
                    "reason": "No title and no DOI - unidentifiable papers",
                    "count": len(critical_metadata),
                    "paper_ids": [p["paper_id"] for p in critical_metadata],
                }

        # Corrupted data - remove
        if self.problems["corrupted_data"]:
            recommendations["corrupted_data"] = {
                "action": "REMOVE",
                "reason": "File corruption or JSON decode errors",
                "count": len(self.problems["corrupted_data"]),
                "paper_ids": [p["paper_id"] for p in self.problems["corrupted_data"]],
            }

        # Quality issues - review case by case (don't auto-remove)
        if self.problems["quality_issues"]:
            severe_quality = [
                p
                for p in self.problems["quality_issues"]
                if (
                    "very_short" in p.get("quality_issues", [])
                    and "no_references" in p.get("quality_issues", [])
                )
            ]
            if severe_quality:
                recommendations["severe_quality_issues"] = {
                    "action": "REVIEW",
                    "reason": "Very short papers with no references - likely abstracts or posters",
                    "count": len(severe_quality),
                    "paper_ids": [p["paper_id"] for p in severe_quality],
                }

        return recommendations

    def _generate_markdown_report(self, report_path: Path, json_data: dict[str, Any]):
        """Generate human-readable markdown report."""
        with open(report_path, "w") as f:
            f.write("# Problematic Papers Analysis Report\n\n")
            f.write(f"Generated: {json_data['timestamp']}\n")
            f.write(f"Data Directory: {json_data['analysis_directory']}\n\n")

            # Summary statistics
            stats = json_data["statistics"]
            f.write("## Summary Statistics\n\n")
            f.write(f"- **Total Papers Analyzed**: {stats['total_papers']}\n")
            f.write(
                f"- **Problematic Papers Found**: {stats['problematic_papers']} "
                f"({stats['problematic_papers'] / stats['total_papers'] * 100:.1f}%)\n"
            )
            f.write(f"- **Clean Papers**: {stats['total_papers'] - stats['problematic_papers']}\n\n")

            # Breakdown by category
            f.write("## Issues by Category\n\n")
            for category, count in stats["by_category"].items():
                f.write(f"- **{category.replace('_', ' ').title()}**: {count} papers\n")
            f.write("\n")

            # Detailed findings
            f.write("## Detailed Findings\n\n")

            for category, papers in json_data["problems_by_category"].items():
                if not papers:
                    continue

                f.write(f"### {category.replace('_', ' ').title()}: {len(papers)} papers\n\n")

                if category == "grobid_failures":
                    f.write("Papers where GROBID extraction completely failed.\n\n")
                    f.write("| Paper ID | Text | Sections | Abstract | Issue |\n")
                    f.write("|----------|------|----------|----------|-------|\n")
                    for paper in papers[:15]:  # Limit for readability
                        issue = "No content" if paper["total_text_chars"] < 100 else "Minimal extraction"
                        f.write(
                            f"| {paper['paper_id']} | {paper['total_text_chars']} | "
                            f"{paper['num_sections']} | {paper['abstract_length']} | {issue} |\n"
                        )

                elif category == "non_articles":
                    f.write("Content identified as non-research articles.\n\n")
                    f.write("| Paper ID | Title | DOI | Type |\n")
                    f.write("|----------|-------|-----|------|\n")
                    for paper in papers[:15]:
                        title = paper["title"][:40] + "..." if len(paper["title"]) > 40 else paper["title"]
                        paper_type = "Editorial" if "editorial" in paper["title"].lower() else "Other"
                        f.write(
                            f"| {paper['paper_id']} | {title} | {paper['doi'][:30]}... | {paper_type} |\n"
                        )

                elif category == "minimal_content":
                    f.write("Papers with insufficient content (likely abstract-only).\n\n")
                    f.write("| Paper ID | Text | Abstract | Sections | References |\n")
                    f.write("|----------|------|----------|----------|------------|\n")
                    for paper in papers[:15]:
                        f.write(
                            f"| {paper['paper_id']} | {paper['total_text_chars']} | "
                            f"{paper['abstract_length']} | {paper['num_sections']} | "
                            f"{paper['num_references']} |\n"
                        )

                elif category == "quality_issues":
                    f.write("Papers with quality concerns but may be recoverable.\n\n")
                    f.write("| Paper ID | Issues | Text | Refs | Year |\n")
                    f.write("|----------|--------|------|------|------|\n")
                    for paper in papers[:15]:
                        issues = ", ".join(paper.get("quality_issues", []))
                        f.write(
                            f"| {paper['paper_id']} | {issues} | {paper['total_text_chars']} | "
                            f"{paper['num_references']} | {paper['year']} |\n"
                        )

                f.write("\n")

            # Removal recommendations
            f.write("## Removal Recommendations\n\n")
            recommendations = json_data["removal_recommendations"]

            total_to_remove = sum(
                rec["count"] for rec in recommendations.values() if rec["action"] == "REMOVE"
            )

            f.write(f"**Total papers recommended for removal: {total_to_remove}**\n\n")

            for category, rec in recommendations.items():
                action_emoji = "🗑️" if rec["action"] == "REMOVE" else "⚠️"
                f.write(f"### {action_emoji} {category.replace('_', ' ').title()}\n")
                f.write(f"- **Action**: {rec['action']}\n")
                f.write(f"- **Count**: {rec['count']} papers\n")
                f.write(f"- **Reason**: {rec['reason']}\n")
                if rec["action"] == "REMOVE":
                    f.write(f"- **Paper IDs**: {', '.join(rec['paper_ids'][:10])}")
                    if len(rec["paper_ids"]) > 10:
                        f.write(f" and {len(rec['paper_ids']) - 10} more")
                f.write("\n\n")

            f.write("## Next Steps\n\n")
            f.write("1. Review the removal recommendations above\n")
            f.write("2. Use the generated removal list to clean the knowledge base\n")
            f.write("3. Re-build the KB with the cleaned dataset\n")
            f.write("4. Monitor extraction quality in future updates\n\n")

            f.write("## Files Generated\n\n")
            f.write(f"- **This report**: {report_path.name}\n")
            f.write(f"- **JSON data**: {report_path.name.replace('.md', '.json')}\n")
            f.write(
                f"- **Removal list**: {report_path.name.replace('analysis', 'to_remove').replace('.md', '.txt')}\n"
            )

    def _generate_removal_list(self, removal_path: Path):
        """Generate simple list of paper IDs to remove."""
        with open(removal_path, "w") as f:
            f.write("# Papers to Remove from Knowledge Base\n")
            f.write(f"# Generated: {datetime.now(UTC).isoformat()}\n")
            f.write("# Format: One paper ID per line\n\n")

            recommendations = self._generate_removal_recommendations()

            all_removals = []
            for category, rec in recommendations.items():
                if rec["action"] == "REMOVE":
                    f.write(f"\n# {category.replace('_', ' ').title()} ({rec['count']} papers)\n")
                    f.write(f"# {rec['reason']}\n")
                    for paper_id in rec["paper_ids"]:
                        f.write(f"{paper_id}\n")
                        all_removals.append(paper_id)

            f.write(f"\n# Total papers to remove: {len(all_removals)}\n")

    def print_summary(self):
        """Print analysis summary to console."""
        print("\n" + "=" * 70)
        print("PROBLEMATIC PAPERS ANALYSIS COMPLETE")
        print("=" * 70)

        print("\n📊 SUMMARY:")
        print(f"  Total papers analyzed: {self.stats['total_papers']}")
        print(
            f"  Problematic papers: {self.stats['problematic_papers']} "
            f"({self.stats['problematic_papers'] / self.stats['total_papers'] * 100:.1f}%)"
        )

        print("\n📋 ISSUES BREAKDOWN:")
        for category, count in self.stats["by_category"].items():
            print(f"  {category.replace('_', ' ').title()}: {count} papers")

        # Count total removals
        recommendations = self._generate_removal_recommendations()
        total_to_remove = sum(rec["count"] for rec in recommendations.values() if rec["action"] == "REMOVE")

        print(f"\n🗑️ RECOMMENDED FOR REMOVAL: {total_to_remove} papers")
        for category, rec in recommendations.items():
            if rec["action"] == "REMOVE":
                print(f"  {category.replace('_', ' ').title()}: {rec['count']} papers")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Analyze extraction data for problematic papers")
    parser.add_argument(
        "--directory",
        default="kb_final_cleaned_20250831_170352",
        help="Directory containing extracted JSON files",
    )

    args = parser.parse_args()

    print("=" * 70)
    print("PROBLEMATIC PAPERS ANALYZER")
    print("=" * 70)
    print(f"Analyzing: {args.directory}")
    print("Looking for:")
    print("  - Complete GROBID extraction failures")
    print("  - Non-research documents (editorials, datasets, supplements)")
    print("  - Papers with minimal content or critical metadata issues")
    print("  - Quality issues that affect KB usefulness")
    print("=" * 70 + "\n")

    try:
        analyzer = ProblematicPaperAnalyzer(args.directory)
        analyzer.analyze_all_papers()

        json_report, md_report, removal_list = analyzer.generate_comprehensive_report()

        analyzer.print_summary()

        print("\n💾 FILES GENERATED:")
        print(f"  Detailed report: {md_report}")
        print(f"  JSON data: {json_report}")
        print(f"  Removal list: {removal_list}")

        print("\n✅ ANALYSIS COMPLETE!")
        print("   Review the markdown report for detailed findings")
        print("   Use the removal list to clean your knowledge base")

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
