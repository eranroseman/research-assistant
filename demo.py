#!/usr/bin/env python3
"""
Demo script to set up and test the Research Assistant
"""

import json
import subprocess
import sys
from pathlib import Path


def run_command(command_text, capture_output=True):
    """Run a shell command and return output."""
    print(f"Running: {command_text}")
    if capture_output:
        result = subprocess.run(
            command_text, shell=True, capture_output=True, text=True
        )
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(f"Error: {result.stderr}", file=sys.stderr)
        return result.stdout
    else:
        subprocess.run(command_text, shell=True)
        return None


def setup_demo():
    """Set up the demo knowledge base and test functionality."""
    print("=" * 60)
    print("Research Assistant Demo Setup")
    print("=" * 60)

    # Check if knowledge base already exists
    knowledge_base_path = Path("kb_data")
    if (
        knowledge_base_path.exists()
        and (knowledge_base_path / "metadata.json").exists()
    ):
        print("\nKnowledge base already exists. Using existing database.")
        print("To rebuild, delete kb_data/ directory and run again.")
    else:
        print("\nBuilding demo knowledge base with sample papers...")
        run_command("python build_kb.py --demo", capture_output=False)

    print("\n" + "=" * 60)
    print("Testing CLI Functionality")
    print("=" * 60)

    # Test 1: Show KB info
    print("\n1. Knowledge Base Information:")
    print("-" * 40)
    run_command("python cli.py info")

    # Test 2: Search for papers
    print("\n2. Searching for 'digital health':")
    print("-" * 40)
    run_command("python cli.py search 'digital health' -k 3 -v")

    # Test 3: Search for different topic
    print("\n3. Searching for 'artificial intelligence':")
    print("-" * 40)
    run_command("python cli.py search 'artificial intelligence diagnosis' -k 3")

    # Test 4: Get specific paper
    print("\n4. Retrieving paper 0001:")
    print("-" * 40)
    output = run_command("python cli.py get 0001")
    if output:
        lines = output.split("\n")[:20]
        print("\n".join(lines))
        print("... [truncated for demo]")

    # Test 5: Generate citations
    print("\n5. Generating IEEE citations for 'telemedicine':")
    print("-" * 40)
    run_command("python cli.py cite 'telemedicine' -k 3")

    # Test 6: JSON output
    print("\n6. JSON output for API integration:")
    print("-" * 40)
    json_output_text = run_command(
        "python cli.py search 'wearable devices' -k 2 --json"
    )
    if json_output_text:
        try:
            data = json.loads(json_output_text)
            print(json.dumps(data, indent=2))
        except json.JSONDecodeError:
            print(json_output_text)

    print("\n" + "=" * 60)
    print("Demo Complete!")
    print("=" * 60)
    print("\nYou can now:")
    print("1. Use the CLI directly: python cli.py search 'your query'")
    print("2. Use in Claude Code: /research your research topic")
    print("3. Build from local Zotero: python build_kb.py (with Zotero running)")
    print("\nFor more information, see README.md")


def test_research_workflow():
    """Demonstrate a complete research workflow."""
    print("\n" + "=" * 60)
    print("Research Workflow Example")
    print("=" * 60)

    topic = "barriers to digital health adoption"
    print(f"\nResearch Topic: '{topic}'")
    print("\nStep 1: Initial broad search")
    print("-" * 40)

    # Search for papers
    search_results_json = run_command(f"python cli.py search '{topic}' -k 10 --json")

    if search_results_json:
        papers = json.loads(search_results_json)
        print(f"Found {len(papers)} relevant papers")

        print("\nStep 2: Analyzing top papers")
        print("-" * 40)

        # Get top 3 papers
        for i, paper in enumerate(papers[:3], 1):
            print(f"\n{i}. {paper['title']}")
            print(f"   Authors: {', '.join(paper['authors'][:2])}...")
            print(f"   Relevance: {paper['similarity_score']:.3f}")

            # Retrieve paper content
            paper_content = run_command(f"python cli.py get {paper['id']}")
            if paper_content:
                # Extract abstract
                lines = paper_content.split("\n")
                for j, line in enumerate(lines):
                    if "Abstract" in line and j + 1 < len(lines):
                        abstract = lines[j + 1][:200] + "..."
                        print(f"   Abstract: {abstract}")
                        break

        print("\nStep 3: Generate citations")
        print("-" * 40)
        run_command(f"python cli.py cite '{topic}' -k 5")

        print("\nStep 4: Research Report Template")
        print("-" * 40)
        print("""
# Research Report: Barriers to Digital Health Adoption

## Executive Summary
Based on analysis of 5 papers, key barriers include technological
literacy (67%), privacy concerns (54%), and lack of perceived benefit (43%).

## Key Findings
1. Elderly populations face significant technological barriers [2]
2. Privacy and security concerns affect over half of users [2], [4]
3. User engagement declines significantly over time [5]

## Evidence Quality
- High confidence: Technology literacy as primary barrier
- Medium confidence: Privacy concerns vary by demographic
- Low confidence: Long-term engagement strategies

## References
[Generated citations would appear here]
        """)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--workflow":
        setup_demo()
        test_research_workflow()
    else:
        setup_demo()
