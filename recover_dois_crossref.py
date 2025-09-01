#!/usr/bin/env python3
"""Attempt to recover DOIs for papers missing them using CrossRef search."""

import json
import time
from habanero import Crossref
from difflib import SequenceMatcher


def search_doi_by_title_and_authors(title, authors, year=None):
    """Search CrossRef for a paper by title and authors."""
    cr = Crossref()

    try:
        # Build query
        query = title

        # Add first author if available
        if authors and len(authors) > 0:
            first_author = authors[0]
            if isinstance(first_author, dict):
                name = first_author.get("name", "")
                name_parts = name.split()
                if name_parts:
                    query += f" {name_parts[-1]}"  # Last name

        # Add year if available
        if year and year != "MISSING":
            query += f" {year}"

        print(f"\n  Searching CrossRef with query: {query[:100]}...")

        # Search CrossRef
        works = cr.works(query=query, limit=5)

        if works and "message" in works and "items" in works["message"]:
            items = works["message"]["items"]

            # Find best match
            best_match = None
            best_score = 0

            for item in items:
                # Get item title
                item_titles = item.get("title", [])
                if not item_titles:
                    continue

                item_title = item_titles[0]

                # Calculate similarity
                score = SequenceMatcher(None, title.lower(), item_title.lower()).ratio()

                # Check year match if available
                if year and year != "MISSING":
                    item_year = None
                    date_parts = item.get("published-print", {}).get("date-parts")
                    if not date_parts:
                        date_parts = item.get("published-online", {}).get("date-parts")
                    if not date_parts:
                        date_parts = item.get("issued", {}).get("date-parts")

                    if date_parts and len(date_parts) > 0 and len(date_parts[0]) > 0:
                        item_year = date_parts[0][0]

                    # Boost score if year matches
                    if item_year and str(item_year) == str(year):
                        score += 0.1

                if score > best_score:
                    best_score = score
                    best_match = item

                # Print match info
                print(f"    - {item_title[:80]}")
                print(f"      Score: {score:.2f}, DOI: {item.get('DOI', 'N/A')}")

            # Return DOI if good match found
            if best_match and best_score >= 0.8:
                doi = best_match.get("DOI")
                print(f"  ✓ Found matching DOI: {doi} (score: {best_score:.2f})")
                return doi, best_match
            print(f"  ✗ No good match found (best score: {best_score:.2f})")

    except Exception as e:
        print(f"  Error searching CrossRef: {e}")

    return None, None


def main():
    # Papers without DOI (from previous analysis)
    papers_no_doi = [
        {
            "id": "J822HUC7",
            "title": "An Evolving Multi-Agent Scenario Generation Framework for Simulations in Prevent",
            "year": "2002",
            "authors": 9,
        },
        {
            "id": "IAELJXCC",
            "title": "Harnessing Social Support for Hypertension Control",
            "year": "2024",
            "authors": 2,
        },
        {
            "id": "RVMLBIUC",
            "title": "Using eHealth to improve integrated care for older people with multimorbidity",
            "year": None,
            "authors": 5,
        },
        {
            "id": "K54ATQH8",
            "title": "measures of sleep to have a more holistic understanding of sleep patterns in later life",
            "year": None,
            "authors": 12,
        },
        {
            "id": "R3HQ7UQR",
            "title": "CATEGORY 1 CME CREDIT Perceived Workplace Health and Safety Climates: Association",
            "year": None,
            "authors": 5,
        },
        {
            "id": "CYLIY8BB",
            "title": "Association of remote, longitudinal patient-reported outcomes (PROs) and step co",
            "year": None,
            "authors": 20,
        },
        {
            "id": "7ZBAMXCP",
            "title": "Ethical considerations in electronic data in healthcare",
            "year": None,
            "authors": 6,
        },
        {"id": "UDKMGASP", "title": None, "year": "2021", "authors": 5},
        {
            "id": "RDP5U6U5",
            "title": "app-based interventions on clinical outcomes",
            "year": None,
            "authors": 0,
        },
        {
            "id": "6AMF33HC",
            "title": "Evaluation of the health promotion program 'Beweeg & Scoor' Personal information",
            "year": None,
            "authors": 0,
        },
        {
            "id": "LJFAA6CL",
            "title": "Multimedia Appendix 2: Optimization Digital Innovation Workshop for Hydroxyurea",
            "year": None,
            "authors": 0,
        },
        {
            "id": "6BP8NH7Z",
            "title": "CHEERS Checklist Items to include when reporting economic evaluations of health",
            "year": None,
            "authors": 0,
        },
    ]

    print("=" * 80)
    print("ATTEMPTING TO RECOVER DOIs FROM CROSSREF")
    print("=" * 80)

    recovered = []
    failed = []

    for i, paper in enumerate(papers_no_doi, 1):
        if not paper["title"] or paper["title"] == "MISSING":
            print(f"\n{i}. Paper {paper['id']}: Skipping (no title)")
            failed.append(paper["id"])
            continue

        print(f"\n{i}. Paper {paper['id']}")
        print(f"   Title: {paper['title'][:80]}...")
        print(f"   Year: {paper.get('year', 'Unknown')}")

        # Load the actual paper data to get author information
        json_file = f"comprehensive_extraction_20250831_211114/{paper['id']}.json"
        authors = []

        try:
            with open(json_file) as f:
                data = json.load(f)
                authors = data.get("authors", [])
        except:
            pass

        # Search for DOI
        doi, match_data = search_doi_by_title_and_authors(paper["title"], authors, paper.get("year"))

        if doi:
            recovered.append(
                {
                    "paper_id": paper["id"],
                    "doi": doi,
                    "title": paper["title"],
                    "crossref_title": match_data.get("title", [""])[0] if match_data else "",
                }
            )
        else:
            failed.append(paper["id"])

        # Rate limiting
        time.sleep(0.5)

    print("\n" + "=" * 80)
    print("RECOVERY RESULTS")
    print("=" * 80)
    print(f"Total papers processed: {len(papers_no_doi)}")
    print(f"DOIs recovered: {len(recovered)}")
    print(f"Failed to recover: {len(failed)}")

    if recovered:
        print("\nRECOVERED DOIs:")
        for rec in recovered:
            print(f"  {rec['paper_id']}: {rec['doi']}")
            print(f"    Original: {rec['title'][:60]}...")
            print(f"    CrossRef: {rec['crossref_title'][:60]}...")

    if failed:
        print("\nFAILED TO RECOVER (likely grey literature, abstracts, or supplementary materials):")
        for paper_id in failed:
            print(f"  {paper_id}")

    # Save results
    if recovered:
        with open("recovered_dois.json", "w") as f:
            json.dump(recovered, f, indent=2)
        print("\nRecovered DOIs saved to recovered_dois.json")


if __name__ == "__main__":
    main()
