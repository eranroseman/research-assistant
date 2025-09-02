#!/usr/bin/env python3
"""Entity Extraction from Grobid XML.

Extract 50+ entity types from Grobid TEI XML output.
Based on maximum extraction parameters defined in grobid_config.py.
"""

from src import config


import re
from defusedxml import ElementTree
from typing import Any


def extract_all_grobid_entities(xml_content: str) -> dict[str, Any]:
    """Extract 50+ entity types from Grobid XML.

    Args:
        xml_content: TEI XML string from Grobid

    Returns:
        dict: Comprehensive entity extraction with all types
    """
    ns = {"tei": "http://www.tei-c.org/ns/1.0"}

    try:
        root = ElementTree.fromstring(xml_content)
    except ElementTree.ParseError:
        return {"error": "Failed to parse XML"}

    entities = {}

    # Core Metadata
    entities["metadata"] = extract_metadata(root, ns)

    # Research Entities
    entities["methodology"] = extract_methodology(root, ns)
    entities["statistics"] = extract_statistics(root, ns)
    entities["software_data"] = extract_software_and_data(root, ns)
    entities["clinical"] = extract_clinical_entities(root, ns)

    # Document Structure
    entities["structure"] = extract_document_structure(root, ns)

    # Quality Indicators
    entities["quality_indicators"] = extract_quality_indicators(root, ns)

    return entities


def extract_metadata(root: ElementTree.Element, ns: dict) -> dict:
    """Extract core metadata from paper."""
    metadata = {}

    # Title
    title_elem = root.find(".//tei:titleStmt/tei:title", ns)
    if title_elem is not None and title_elem.text:
        metadata["title"] = title_elem.text.strip()

    # Authors with details
    authors = []
    for author in root.findall(".//tei:fileDesc//tei:author", ns):
        author_info = {}

        # Name
        name_parts = []
        for name in author.findall(".//tei:persName/*", ns):
            if name.text:
                name_parts.append(name.text.strip())
        if name_parts:
            author_info["name"] = " ".join(name_parts)

        # Email
        email = author.find(".//tei:email", ns)
        if email is not None and email.text:
            author_info["email"] = email.text.strip()

        # ORCID (if consolidateHeader='2' was used)
        idno = author.find('.//tei:idno[@type="ORCID"]', ns)
        if idno is not None and idno.text:
            author_info["orcid"] = idno.text.strip()

        # Affiliation
        affiliation = author.find(".//tei:affiliation", ns)
        if affiliation is not None:
            org_name = affiliation.find(".//tei:orgName", ns)
            if org_name is not None and org_name.text:
                author_info["affiliation"] = org_name.text.strip()

        if author_info:
            authors.append(author_info)

    metadata["authors"] = authors

    # DOI
    doi_elem = root.find('.//tei:idno[@type="DOI"]', ns)
    if doi_elem is not None and doi_elem.text:
        metadata["doi"] = doi_elem.text.strip()

    # Publication date
    date_elem = root.find(".//tei:publicationStmt/tei:date", ns)
    if date_elem is not None:
        metadata["publication_date"] = date_elem.get("when", "")

    # Journal
    journal_elem = root.find('.//tei:monogr/tei:title[@level="j"]', ns)
    if journal_elem is not None and journal_elem.text:
        metadata["journal"] = journal_elem.text.strip()

    # Keywords
    keywords = []
    for keyword in root.findall(".//tei:keywords/tei:term", ns):
        if keyword.text:
            keywords.append(keyword.text.strip())
    metadata["keywords"] = keywords

    return metadata


def extract_methodology(root: ElementTree.Element, ns: dict) -> dict:
    """Extract methodology-related entities."""
    methodology = {}

    # Sample sizes
    methodology["sample_sizes"] = extract_sample_sizes(root, ns)

    # Study type detection
    methodology["study_type"] = detect_study_type(root, ns)

    # Clinical trial IDs
    methodology["trial_ids"] = extract_trial_ids(root, ns)

    # Time periods
    methodology["time_periods"] = extract_time_periods(root, ns)

    return methodology


def extract_sample_sizes(root: ElementTree.Element, ns: dict) -> list[int]:
    """Extract all sample sizes from paper."""
    sizes = []

    patterns = [
        r"n\s*=\s*(\d+)",
        r"N\s*=\s*(\d+)",
        r"(\d+)\s+participants?",
        r"(\d+)\s+patients?",
        r"(\d+)\s+subjects?",
        r"sample size of (\d+)",
        r"enrolled (\d+)",
        r"recruited (\d+)",
    ]

    # Get all text content
    text = " ".join(root.itertext())

    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            try:
                size = int(match)
                if (
                    config.MIN_SAMPLE_SIZE_THRESHOLD <= size <= config.MAX_SAMPLE_SIZE_THRESHOLD
                ):  # Reasonable range
                    sizes.append(size)
            except ValueError:
                continue

    # Return unique sizes, sorted descending
    return sorted(set(sizes), reverse=True)


def detect_study_type(root: ElementTree.Element, ns: dict) -> str | None:
    """Detect the type of study."""
    text_lower = " ".join(root.itertext()).lower()

    study_types = {
        "rct": [
            "randomized controlled trial",
            "randomised controlled trial",
            "rct",
            "randomized trial",
            "randomised trial",
        ],
        "cohort": ["cohort study", "prospective cohort", "retrospective cohort"],
        "case_control": ["case-control", "case control"],
        "cross_sectional": ["cross-sectional", "cross sectional"],
        "systematic_review": ["systematic review", "meta-analysis", "meta analysis"],
        "case_report": ["case report", "case study"],
        "observational": ["observational study"],
        "experimental": ["experimental study", "experiment"],
        "qualitative": ["qualitative study", "qualitative research"],
    }

    for study_type, patterns in study_types.items():
        for pattern in patterns:
            if pattern in text_lower:
                return study_type

    return None


def extract_statistics(root: ElementTree.Element, ns: dict) -> dict:
    """Extract statistical values from paper."""
    statistics = {}

    text = " ".join(root.itertext())

    # P-values
    p_values = []
    p_patterns = [r"p\s*[<=]\s*(0\.\d+)", r"P\s*[<=]\s*(0\.\d+)", r"p-value[s]?\s*[<=]\s*(0\.\d+)"]

    for pattern in p_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            try:
                p_val = float(match)
                if 0 <= p_val <= 1:
                    p_values.append(p_val)
            except ValueError:
                continue

    statistics["p_values"] = sorted(set(p_values))

    # Confidence intervals
    ci_patterns = [r"(95%)\s*CI", r"(99%)\s*CI", r"(90%)\s*confidence interval"]

    ci_levels = []
    for pattern in ci_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        ci_levels.extend(matches)

    statistics["confidence_intervals"] = list(set(ci_levels))

    # Effect sizes (odds ratios, hazard ratios, etc.)
    effect_sizes = {}

    # Odds ratios
    or_pattern = r"OR\s*[=:]\s*(\d+\.?\d*)"
    or_matches = re.findall(or_pattern, text, re.IGNORECASE)
    if or_matches:
        effect_sizes["odds_ratios"] = [float(x) for x in or_matches]

    # Hazard ratios
    hr_pattern = r"HR\s*[=:]\s*(\d+\.?\d*)"
    hr_matches = re.findall(hr_pattern, text, re.IGNORECASE)
    if hr_matches:
        effect_sizes["hazard_ratios"] = [float(x) for x in hr_matches]

    statistics["effect_sizes"] = effect_sizes

    return statistics


def extract_software_and_data(root: ElementTree.Element, ns: dict) -> dict:
    """Extract software tools and datasets mentioned."""
    result = {}

    text = " ".join(root.itertext())

    # Software detection
    software_patterns = {
        "SPSS": r"SPSS\s*(?:v|version)?\s*([\d\.]+)?",
        "R": r"\bR\s+(?:version\s*)?([\d\.]+)",
        "Python": r"Python\s*([\d\.]+)?",
        "MATLAB": r"MATLAB\s*(?:R\d{4}[ab]?)?",
        "SAS": r"SAS\s*(?:v|version)?\s*([\d\.]+)?",
        "Stata": r"Stata\s*(?:v|version)?\s*([\d\.]+)?",
        "GraphPad Prism": r"GraphPad\s+Prism\s*([\d\.]+)?",
        "Excel": r"(?:Microsoft\s+)?Excel",
        "JASP": r"JASP\s*([\d\.]+)?",
        "Mplus": r"Mplus\s*([\d\.]+)?",
    }

    software_found = []
    for name, pattern in software_patterns.items():
        if re.search(pattern, text, re.IGNORECASE):
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches and matches[0]:
                software_found.append(f"{name} {matches[0]}")
            else:
                software_found.append(name)

    result["software"] = software_found

    # Dataset detection
    dataset_patterns = [
        "MIMIC-III",
        "MIMIC-IV",
        "eICU",
        "UK Biobank",
        "NHANES",
        "PhysioNet",
        "TCGA",
        "GEO",
        "dbGaP",
        "ClinicalTrials.gov",
        "OpenNeuro",
        "ImageNet",
        "COCO",
        "MNIST",
    ]

    datasets_found = []
    for dataset in dataset_patterns:
        if dataset.lower() in text.lower():
            datasets_found.append(dataset)

    result["datasets"] = datasets_found

    # Data availability
    data_availability = {"has_statement": False, "is_available": False, "repository": None}

    if "data availability" in text.lower() or "data sharing" in text.lower():
        data_availability["has_statement"] = True

        if "available" in text.lower() and "request" not in text.lower():
            data_availability["is_available"] = True

        # Check for repository mentions
        repos = ["github", "zenodo", "figshare", "dryad", "osf"]
        for repo in repos:
            if repo in text.lower():
                data_availability["repository"] = repo
                break

    result["data_availability"] = data_availability

    # Code availability
    code_patterns = [
        r"github\.com/[\w\-]+/[\w\-]+",
        r"gitlab\.com/[\w\-]+/[\w\-]+",
        r"bitbucket\.org/[\w\-]+/[\w\-]+",
        r"doi\.org/10\.\d+/zenodo\.\d+",
    ]

    code_urls = []
    for pattern in code_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        code_urls.extend(matches)

    result["code_urls"] = list(set(code_urls))

    return result


def extract_clinical_entities(root: ElementTree.Element, ns: dict) -> dict:
    """Extract clinical and medical entities."""
    clinical = {}

    text = " ".join(root.itertext())

    # Clinical trial IDs
    clinical["trial_ids"] = extract_trial_ids(root, ns)

    # Disease mentions (simplified - real implementation would use NER)
    common_diseases = [
        "diabetes",
        "cancer",
        "covid-19",
        "coronavirus",
        "hypertension",
        "depression",
        "anxiety",
        "alzheimer",
        "parkinson",
        "stroke",
        "heart disease",
        "cardiovascular disease",
        "obesity",
    ]

    diseases_found = []
    for disease in common_diseases:
        if disease.lower() in text.lower():
            diseases_found.append(disease)

    clinical["diseases"] = diseases_found

    # Drug mentions (simplified)
    clinical["drugs"] = extract_drug_mentions(text)

    return clinical


def extract_trial_ids(root: ElementTree.Element, ns: dict) -> list[str]:
    """Extract clinical trial identifiers."""
    text = " ".join(root.itertext())

    trial_ids = []

    # NCT numbers
    nct_pattern = r"NCT\d{8}"
    nct_matches = re.findall(nct_pattern, text)
    trial_ids.extend(nct_matches)

    # ISRCTN numbers
    isrctn_pattern = r"ISRCTN\d{8}"
    isrctn_matches = re.findall(isrctn_pattern, text)
    trial_ids.extend(isrctn_matches)

    # EudraCT numbers
    eudract_pattern = r"\d{4}-\d{6}-\d{2}"
    eudract_matches = re.findall(eudract_pattern, text)
    trial_ids.extend(eudract_matches)

    return list(set(trial_ids))


def extract_drug_mentions(text: str) -> list[str]:
    """Extract drug/medication mentions (simplified)."""
    # Common drug suffixes
    drug_patterns = [
        r"\b\w+(?:mab|ib|vir|tide|pril|sartan|statin|zole|cycline)\b",
        r"\b(?:aspirin|insulin|metformin|warfarin|heparin)\b",
    ]

    drugs = []
    for pattern in drug_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        drugs.extend(matches)

    return list(set(drugs))


def extract_time_periods(root: ElementTree.Element, ns: dict) -> dict:
    """Extract study time periods and durations."""
    text = " ".join(root.itertext())

    periods = {}

    # Study duration
    duration_patterns = [
        r"(\d+)\s*(?:year|yr)s?\s+(?:study|trial|follow-up)",
        r"(\d+)\s*months?\s+(?:study|trial|follow-up)",
        r"(\d+)\s*weeks?\s+(?:study|trial|follow-up)",
    ]

    for pattern in duration_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            periods["duration"] = matches[0]
            break

    # Date ranges
    date_pattern = (
        r"(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}"
    )
    date_matches = re.findall(date_pattern, text)
    if len(date_matches) >= config.MIN_DATE_MATCHES:
        periods["date_range"] = f"{date_matches[0]} - {date_matches[-1]}"

    return periods


def extract_document_structure(root: ElementTree.Element, ns: dict) -> dict:
    """Extract document structure information."""
    structure = {}

    # Figures
    figures = root.findall(".//tei:figure", ns)
    structure["figures_count"] = len(figures)

    figure_captions = []
    for fig in figures:
        caption = fig.find(".//tei:figDesc", ns)
        if caption is not None and caption.text:
            figure_captions.append(caption.text.strip())
    structure["figure_captions"] = figure_captions[:10]  # First 10

    # Tables
    tables = root.findall(".//tei:table", ns)
    structure["tables_count"] = len(tables)

    # Equations
    equations = root.findall(".//tei:formula", ns)
    structure["equations_count"] = len(equations)

    # References
    refs = root.findall(".//tei:listBibl/tei:biblStruct", ns)
    structure["references_count"] = len(refs)

    # Sections
    sections = root.findall(".//tei:body/tei:div", ns)
    section_names = []
    for section in sections:
        head = section.find("tei:head", ns)
        if head is not None and head.text:
            section_names.append(head.text.strip())
    structure["sections"] = section_names

    # URLs
    urls = re.findall(r'https?://[^\s<>"{}|\\^`\[\]]+', " ".join(root.itertext()))
    structure["urls"] = list(set(urls))[:20]  # First 20 unique URLs

    return structure


def extract_quality_indicators(root: ElementTree.Element, ns: dict) -> dict:
    """Extract indicators of paper quality and completeness."""
    indicators = {}

    text = " ".join(root.itertext())
    text_lower = text.lower()

    # Funding information (if consolidateFunders='1' was used)
    funding = []
    for funder in root.findall(".//tei:funder", ns):
        funder_name = funder.find(".//tei:orgName", ns)
        if funder_name is not None and funder_name.text:
            funding.append(funder_name.text.strip())
    indicators["funding_sources"] = funding

    # Ethics approval
    indicators["has_ethics_approval"] = any(
        term in text_lower
        for term in [
            "ethics approval",
            "ethical approval",
            "irb approval",
            "institutional review board",
            "ethics committee",
        ]
    )

    # Conflict of interest
    indicators["has_coi_statement"] = any(
        term in text_lower
        for term in ["conflict of interest", "competing interest", "declaration of interest", "disclosure"]
    )

    # Registration (for clinical trials)
    indicators["is_registered"] = bool(extract_trial_ids(root, ns))

    # Reporting guidelines
    guidelines = {
        "CONSORT": "consort" in text_lower,
        "STROBE": "strobe" in text_lower,
        "PRISMA": "prisma" in text_lower,
        "STARD": "stard" in text_lower,
        "ARRIVE": "arrive" in text_lower,
    }
    indicators["reporting_guidelines"] = [g for g, found in guidelines.items() if found]

    # Supplementary materials
    indicators["has_supplementary"] = any(
        term in text_lower
        for term in ["supplementary", "supplemental", "appendix", "additional file", "supporting information"]
    )

    return indicators
