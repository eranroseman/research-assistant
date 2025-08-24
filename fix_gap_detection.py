#!/usr/bin/env python3
"""Quick fix for gap detection data handling issues."""

import re


def fix_gap_detection_file():
    """Fix the gap detection file to handle data type issues."""
    file_path = "src/gap_detection.py"

    with open(file_path) as f:
        content = f.read()

    # Fix author handling in citation network analysis
    content = re.sub(
        r'"authors": \[a\.get\("name", ""\) for a in ref\.get\("authors", \[\]\)\],',
        '"authors": [a.get("name", "") if isinstance(a, dict) else str(a) for a in ref.get("authors", [])],',
        content,
    )

    # Fix paper handling in citation network analysis
    content = re.sub(
        r'citation_candidates\[ref_key\]\["citing_papers"\]\.append\(\{\s*"id": paper\["id"\],\s*"title": paper\["title"\]\s*\}\)',
        """citation_candidates[ref_key]["citing_papers"].append({
                    "id": paper.get("id", "unknown") if isinstance(paper, dict) else str(paper),
                    "title": paper.get("title", "Unknown Title") if isinstance(paper, dict) else "Unknown Title"
                })""",
        content,
        flags=re.MULTILINE | re.DOTALL,
    )

    # Fix author handling in author network analysis
    content = re.sub(
        r'"authors": \[a\.get\("name", ""\) for a in paper\.get\("authors", \[\]\)\],',
        '"authors": [a.get("name", "") if isinstance(a, dict) else str(a) for a in paper.get("authors", [])],',
        content,
    )

    with open(file_path, "w") as f:
        f.write(content)

    print("✅ Fixed gap detection data handling issues")


if __name__ == "__main__":
    fix_gap_detection_file()
