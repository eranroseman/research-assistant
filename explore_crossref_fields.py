#!/usr/bin/env python3
"""Explore all available fields from CrossRef API to see what we can verify."""

from habanero import Crossref
import pprint


def explore_crossref_fields(doi: str = "10.1371/journal.pone.0261785"):
    """Fetch and display all available CrossRef fields for a paper."""
    cr = Crossref()

    print(f"Fetching CrossRef data for DOI: {doi}")
    print("=" * 80)

    try:
        # Get the full response
        response = cr.works(ids=doi)

        if response and "message" in response:
            data = response["message"]

            # Pretty print the entire response
            print("\nFULL CROSSREF RESPONSE:")
            print("-" * 40)
            pp = pprint.PrettyPrinter(indent=2, width=100)
            pp.pprint(data)

            # Extract and categorize fields
            print("\n" + "=" * 80)
            print("CATEGORIZED FIELDS AVAILABLE:")
            print("=" * 80)

            # Basic metadata
            print("\n1. BASIC METADATA:")
            print("-" * 40)
            fields = ["DOI", "URL", "type", "title", "subtitle", "short-title"]
            for field in fields:
                if field in data:
                    value = data[field]
                    if isinstance(value, list) and len(value) > 0:
                        value = value[0] if len(str(value[0])) < 100 else f"{str(value[0])[:100]}..."
                    print(f"  {field}: {value}")

            # Dates
            print("\n2. DATES:")
            print("-" * 40)
            date_fields = [
                "created",
                "deposited",
                "indexed",
                "issued",
                "published-print",
                "published-online",
                "accepted",
                "approved",
            ]
            for field in date_fields:
                if field in data:
                    value = data[field]
                    if isinstance(value, dict):
                        if "date-time" in value:
                            print(f"  {field}: {value['date-time']}")
                        elif "date-parts" in value:
                            print(f"  {field}: {value['date-parts']}")
                    else:
                        print(f"  {field}: {value}")

            # Publication details
            print("\n3. PUBLICATION DETAILS:")
            print("-" * 40)
            pub_fields = [
                "container-title",
                "container-title-short",
                "publisher",
                "publisher-location",
                "volume",
                "issue",
                "page",
                "article-number",
                "published-print",
                "published-online",
            ]
            for field in pub_fields:
                if field in data:
                    value = data[field]
                    if isinstance(value, list) and len(value) > 0:
                        value = value[0]
                    if value:
                        print(f"  {field}: {value}")

            # Authors and contributors
            print("\n4. AUTHORS & CONTRIBUTORS:")
            print("-" * 40)
            if "author" in data:
                print(f"  authors: {len(data['author'])} authors")
                if data["author"]:
                    first = data["author"][0]
                    print(f"    First author: {first.get('given', '')} {first.get('family', '')}")
                    if "ORCID" in first:
                        print(f"    ORCID: {first['ORCID']}")
                    if first.get("affiliation"):
                        print(f"    Affiliation: {first['affiliation'][0].get('name', 'N/A')}")

            if "editor" in data:
                print(f"  editors: {len(data['editor'])} editors")

            # Identifiers
            print("\n5. IDENTIFIERS:")
            print("-" * 40)
            id_fields = ["DOI", "ISSN", "ISBN", "archive", "license"]
            for field in id_fields:
                if field in data:
                    value = data[field]
                    if isinstance(value, list) and len(value) > 0:
                        if isinstance(value[0], dict):
                            value = value[0].get("URL", value[0])
                        else:
                            value = ", ".join(value)
                    print(f"  {field}: {value}")

            # Metrics and scores
            print("\n6. METRICS:")
            print("-" * 40)
            metric_fields = ["is-referenced-by-count", "references-count", "score"]
            for field in metric_fields:
                if field in data:
                    print(f"  {field}: {data[field]}")

            # Abstract
            print("\n7. CONTENT:")
            print("-" * 40)
            if "abstract" in data:
                abstract = data["abstract"]
                # Remove XML tags if present
                import re

                clean_abstract = re.sub("<[^<]+?>", "", abstract)
                print(f"  abstract: {clean_abstract[:200]}...")

            # Subject/Keywords
            print("\n8. CLASSIFICATION:")
            print("-" * 40)
            if "subject" in data:
                subjects = data["subject"]
                print(f"  subjects: {', '.join(subjects)}")

            if "keyword" in data:
                keywords = data["keyword"]
                if isinstance(keywords, list):
                    print(f"  keywords: {', '.join(keywords[:10])}")

            # Clinical trials
            print("\n9. CLINICAL TRIALS:")
            print("-" * 40)
            if "clinical-trial-number" in data:
                trials = data["clinical-trial-number"]
                for trial in trials[:5]:  # Show first 5
                    print(f"  {trial.get('clinical-trial-number', 'N/A')} ({trial.get('registry', 'N/A')})")

            # Funding
            print("\n10. FUNDING:")
            print("-" * 40)
            if "funder" in data:
                funders = data["funder"]
                print(f"  Number of funders: {len(funders)}")
                for funder in funders[:3]:  # Show first 3
                    name = funder.get("name", "Unknown")
                    doi = funder.get("DOI", "No DOI")
                    print(f"    - {name} ({doi})")
                    if "award" in funder:
                        awards = funder["award"]
                        if isinstance(awards, list) and awards:
                            print(f"      Awards: {', '.join(awards[:3])}")

            # References
            print("\n11. REFERENCES:")
            print("-" * 40)
            if "reference" in data:
                refs = data["reference"]
                print(f"  Total references: {len(refs)}")
                if refs:
                    print(
                        f"  First reference: {refs[0].get('unstructured', refs[0].get('DOI', 'N/A'))[:100]}..."
                    )

            # Update history
            print("\n12. UPDATE HISTORY:")
            print("-" * 40)
            if "update-to" in data:
                updates = data["update-to"]
                for update in updates:
                    print(f"  Updated to: {update.get('DOI', 'N/A')} ({update.get('type', 'N/A')})")

            # Quality indicators
            print("\n13. QUALITY INDICATORS:")
            print("-" * 40)
            quality_fields = ["peer-review", "content-domain", "assertion"]
            for field in quality_fields:
                if field in data:
                    print(f"  {field}: Present")

            # Relations
            print("\n14. RELATIONS:")
            print("-" * 40)
            if "relation" in data:
                relations = data["relation"]
                for rel_type, rel_data in relations.items():
                    if isinstance(rel_data, list) and rel_data:
                        print(f"  {rel_type}: {len(rel_data)} items")

            # License
            print("\n15. LICENSE:")
            print("-" * 40)
            if "license" in data:
                licenses = data["license"]
                for lic in licenses:
                    url = lic.get("URL", "N/A")
                    start = lic.get("start", {}).get("date-time", "N/A")
                    print(f"  License: {url}")
                    print(f"  Start: {start}")

            return data

    except Exception as e:
        print(f"Error: {e}")
        return None


def compare_with_our_extraction():
    """Compare what we extract vs what's available."""
    print("\n" + "=" * 80)
    print("COMPARISON WITH OUR CURRENT EXTRACTION:")
    print("=" * 80)

    currently_extracted = ["DOI", "title", "year", "authors", "journal"]

    additional_valuable = [
        "abstract",
        "volume",
        "issue",
        "page",
        "publisher",
        "ISSN",
        "ISBN",
        "is-referenced-by-count (citation count)",
        "references-count",
        "subject (research areas)",
        "keyword",
        "funder",
        "clinical-trial-number",
        "published-online",
        "published-print",
        "license",
        "ORCID (for authors)",
        "affiliation details",
        "editor",
        "subtitle",
        "container-title-short (journal abbreviation)",
    ]

    print("\nCurrently extracted:")
    for field in currently_extracted:
        print(f"  ✓ {field}")

    print("\nAdditional fields we could verify/extract:")
    for field in additional_valuable:
        print(f"  + {field}")


if __name__ == "__main__":
    # Test with a paper that has rich metadata
    test_dois = [
        "10.1371/journal.pone.0261785",  # PLOS ONE paper (rich metadata)
        "10.1038/s41591-023-02502-5",  # Nature Medicine (high impact)
        "10.1016/j.jclinepi.2021.03.001",  # Clinical epidemiology paper
    ]

    print("Testing with a PLOS ONE paper (typically has rich metadata)...")
    data = explore_crossref_fields(test_dois[0])

    # Show comparison
    compare_with_our_extraction()

    print("\n" + "=" * 80)
    print("Testing with another DOI to see variation...")
    print("=" * 80)
    explore_crossref_fields(test_dois[1])
