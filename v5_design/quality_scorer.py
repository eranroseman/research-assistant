"""Quality Scoring System for Research Papers.

This module implements a comprehensive quality scoring system that evaluates papers
based on multiple factors including study design, sample size, statistical rigor,
and publication venue.
"""

from typing import Any
import re
from datetime import datetime, UTC


class QualityScorer:
    """Calculate quality scores for research papers based on extracted metadata."""

    def __init__(self):
        """Initialize the quality scorer with scoring weights."""
        # Scoring weights (total = 100)
        self.weights = {
            "study_type": 20,  # RCT, cohort, etc.
            "sample_size": 15,  # Larger samples = higher quality
            "statistical_rigor": 15,  # p-values, confidence intervals
            "venue_quality": 15,  # Journal impact
            "recency": 10,  # More recent = better
            "citations": 10,  # Citation count
            "completeness": 10,  # How complete the extraction is
            "reproducibility": 5,  # Code/data availability
        }

        # Study type rankings (higher = better)
        self.study_type_scores = {
            "systematic review": 10,
            "meta-analysis": 10,
            "randomized controlled trial": 9,
            "rct": 9,
            "cohort study": 7,
            "cohort": 7,
            "case-control": 6,
            "cross-sectional": 5,
            "case series": 3,
            "case report": 2,
            "opinion": 1,
            "editorial": 1,
        }

        # Top-tier venues
        self.top_venues = {
            "nature",
            "science",
            "cell",
            "lancet",
            "nejm",
            "new england journal of medicine",
            "jama",
            "bmj",
            "pnas",
            "nature medicine",
            "nature biotechnology",
            "nature genetics",
            "nature neuroscience",
            "nature methods",
        }

    def calculate_score(self, paper: dict[str, Any]) -> dict[str, Any]:
        """Calculate comprehensive quality score for a paper.

        Args:
            paper: Dictionary containing paper metadata and extracted entities

        Returns:
            Dictionary with total score and component breakdowns
        """
        scores = {}

        # 1. Study Type Score (20 points)
        scores["study_type"] = self._score_study_type(paper)

        # 2. Sample Size Score (15 points)
        scores["sample_size"] = self._score_sample_size(paper)

        # 3. Statistical Rigor Score (15 points)
        scores["statistical_rigor"] = self._score_statistics(paper)

        # 4. Venue Quality Score (15 points)
        scores["venue_quality"] = self._score_venue(paper)

        # 5. Recency Score (10 points)
        scores["recency"] = self._score_recency(paper)

        # 6. Citation Score (10 points)
        scores["citations"] = self._score_citations(paper)

        # 7. Completeness Score (10 points)
        scores["completeness"] = self._score_completeness(paper)

        # 8. Reproducibility Score (5 points)
        scores["reproducibility"] = self._score_reproducibility(paper)

        # Calculate total
        total_score = sum(scores.values())

        # Generate grade
        grade = self._calculate_grade(total_score)

        return {
            "total_score": round(total_score, 1),
            "grade": grade,
            "components": scores,
            "strengths": self._identify_strengths(scores),
            "weaknesses": self._identify_weaknesses(scores),
        }

    def _score_study_type(self, paper: dict[str, Any]) -> float:
        """Score based on study design."""
        study_types = paper.get("entities", {}).get("study_types", [])

        if not study_types:
            # Try to detect from text
            text = paper.get("abstract", "") + " " + paper.get("title", "")
            text_lower = text.lower()

            for study_type, score in self.study_type_scores.items():
                if study_type in text_lower:
                    return (score / 10) * self.weights["study_type"]

        # Use the highest quality study type found
        max_score = 0
        for study_type in study_types:
            study_lower = study_type.lower()
            for known_type, score in self.study_type_scores.items():
                if known_type in study_lower:
                    max_score = max(max_score, score)

        return (max_score / 10) * self.weights["study_type"]

    def _score_sample_size(self, paper: dict[str, Any]) -> float:
        """Score based on sample size."""
        sample_sizes = paper.get("entities", {}).get("sample_sizes", [])

        if not sample_sizes:
            return 0

        # Extract numeric values
        max_sample = 0
        for sample in sample_sizes:
            # Extract number from strings like "n=500" or "500 patients"
            numbers = re.findall(r"\d+", str(sample))
            if numbers:
                max_sample = max(max_sample, int(numbers[0]))

        # Scoring scale
        if max_sample >= 10000:
            score = 1.0
        elif max_sample >= 1000:
            score = 0.8
        elif max_sample >= 500:
            score = 0.6
        elif max_sample >= 100:
            score = 0.4
        elif max_sample >= 50:
            score = 0.2
        else:
            score = 0.1

        return score * self.weights["sample_size"]

    def _score_statistics(self, paper: dict[str, Any]) -> float:
        """Score based on statistical rigor."""
        entities = paper.get("entities", {})
        score = 0
        max_score = 0

        # Check for p-values
        p_values = entities.get("p_values", [])
        if p_values:
            score += 5
        max_score += 5

        # Check for confidence intervals
        confidence_intervals = entities.get("confidence_intervals", [])
        if confidence_intervals:
            score += 5
        max_score += 5

        # Check for effect sizes
        effect_sizes = entities.get("effect_sizes", [])
        if effect_sizes:
            score += 3
        max_score += 3

        # Check for statistical tests mentioned
        stats_text = paper.get("methods", "") + paper.get("results", "")
        stats_keywords = [
            "anova",
            "t-test",
            "chi-square",
            "regression",
            "mann-whitney",
            "wilcoxon",
            "kruskal-wallis",
        ]
        if any(keyword in stats_text.lower() for keyword in stats_keywords):
            score += 2
        max_score += 2

        return (score / max_score) * self.weights["statistical_rigor"] if max_score > 0 else 0

    def _score_venue(self, paper: dict[str, Any]) -> float:
        """Score based on publication venue."""
        venue = paper.get("venue", "") or paper.get("journal", "")

        if not venue:
            return 0

        venue_lower = venue.lower()

        # Check if top-tier venue
        for top_venue in self.top_venues:
            if top_venue in venue_lower:
                return self.weights["venue_quality"]

        # Check for impact factor or known good journals
        if any(term in venue_lower for term in ["ieee", "acm", "springer", "elsevier", "wiley"]):
            return 0.6 * self.weights["venue_quality"]

        # Default score for peer-reviewed journals
        if venue and venue != "unknown":
            return 0.3 * self.weights["venue_quality"]

        return 0

    def _score_recency(self, paper: dict[str, Any]) -> float:
        """Score based on publication recency."""
        year = paper.get("year")

        if not year:
            return 0

        try:
            year = int(year)
            current_year = datetime.now(UTC).year
            age = current_year - year

            if age <= 2:
                score = 1.0
            elif age <= 5:
                score = 0.8
            elif age <= 10:
                score = 0.5
            elif age <= 15:
                score = 0.3
            else:
                score = 0.1

            return score * self.weights["recency"]
        except (ValueError, TypeError):
            return 0

    def _score_citations(self, paper: dict[str, Any]) -> float:
        """Score based on citation count."""
        citations = paper.get("citation_count", 0)

        # Adjust for paper age
        year = paper.get("year")
        if year:
            try:
                age = datetime.now(UTC).year - int(year) + 1
                citations_per_year = citations / age
            except (ValueError, TypeError, ZeroDivisionError):
                citations_per_year = citations
        else:
            citations_per_year = citations

        # Scoring scale (citations per year)
        if citations_per_year >= 50:
            score = 1.0
        elif citations_per_year >= 20:
            score = 0.8
        elif citations_per_year >= 10:
            score = 0.6
        elif citations_per_year >= 5:
            score = 0.4
        elif citations_per_year >= 1:
            score = 0.2
        else:
            score = 0.1

        return score * self.weights["citations"]

    def _score_completeness(self, paper: dict[str, Any]) -> float:
        """Score based on extraction completeness."""
        score = 0
        max_score = 0

        # Check for essential sections
        essential_fields = ["title", "abstract", "introduction", "methods", "results", "discussion"]

        for field in essential_fields:
            max_score += 1
            if paper.get(field):
                score += 1

        # Check for entities
        entities = paper.get("entities", {})
        if entities:
            entity_count = sum(len(v) for v in entities.values() if isinstance(v, list))
            if entity_count > 20:
                score += 2
            elif entity_count > 10:
                score += 1
        max_score += 2

        # Check for references
        if paper.get("references"):
            score += 1
        max_score += 1

        # Check for DOI
        if paper.get("doi"):
            score += 1
        max_score += 1

        return (score / max_score) * self.weights["completeness"] if max_score > 0 else 0

    def _score_reproducibility(self, paper: dict[str, Any]) -> float:
        """Score based on reproducibility indicators."""
        entities = paper.get("entities", {})
        score = 0

        # Check for code availability
        if entities.get("code_availability"):
            score += 2.5

        # Check for data availability
        if entities.get("data_availability"):
            score += 2.5

        # Check for software/tools mentioned
        if entities.get("software"):
            score += 1

        # Check for GitHub/repository links
        text = paper.get("abstract", "") + paper.get("methods", "")
        if any(term in text.lower() for term in ["github", "repository", "code available"]):
            score = min(score + 1, self.weights["reproducibility"])

        return min(score, self.weights["reproducibility"])

    def _calculate_grade(self, score: float) -> str:
        """Convert numeric score to letter grade."""
        if score >= 85:
            return "A+"
        if score >= 80:
            return "A"
        if score >= 75:
            return "A-"
        if score >= 70:
            return "B+"
        if score >= 65:
            return "B"
        if score >= 60:
            return "B-"
        if score >= 55:
            return "C+"
        if score >= 50:
            return "C"
        if score >= 45:
            return "C-"
        if score >= 40:
            return "D"
        return "F"

    def _identify_strengths(self, scores: dict[str, float]) -> list[str]:
        """Identify paper strengths based on scores."""
        strengths = []

        for component, score in scores.items():
            max_possible = self.weights.get(component, 0)
            if max_possible > 0 and score >= 0.8 * max_possible:
                if component == "study_type":
                    strengths.append("High-quality study design")
                elif component == "sample_size":
                    strengths.append("Large sample size")
                elif component == "statistical_rigor":
                    strengths.append("Strong statistical analysis")
                elif component == "venue_quality":
                    strengths.append("Published in top-tier venue")
                elif component == "recency":
                    strengths.append("Recent publication")
                elif component == "citations":
                    strengths.append("Highly cited")
                elif component == "completeness":
                    strengths.append("Complete extraction")
                elif component == "reproducibility":
                    strengths.append("Good reproducibility")

        return strengths

    def _identify_weaknesses(self, scores: dict[str, float]) -> list[str]:
        """Identify paper weaknesses based on scores."""
        weaknesses = []

        for component, score in scores.items():
            max_possible = self.weights.get(component, 0)
            if max_possible > 0 and score < 0.3 * max_possible:
                if component == "study_type":
                    weaknesses.append("Weak study design")
                elif component == "sample_size":
                    weaknesses.append("Small sample size")
                elif component == "statistical_rigor":
                    weaknesses.append("Limited statistical analysis")
                elif component == "venue_quality":
                    weaknesses.append("Unknown or low-tier venue")
                elif component == "recency":
                    weaknesses.append("Older publication")
                elif component == "citations":
                    weaknesses.append("Few citations")
                elif component == "completeness":
                    weaknesses.append("Incomplete extraction")
                elif component == "reproducibility":
                    weaknesses.append("Limited reproducibility")

        return weaknesses


# Example usage
if __name__ == "__main__":
    scorer = QualityScorer()

    # Example paper data
    example_paper = {
        "title": "A Randomized Controlled Trial of Digital Health Intervention",
        "abstract": "We conducted a randomized controlled trial with 500 participants...",
        "year": 2023,
        "venue": "Nature Medicine",
        "citation_count": 25,
        "methods": "Statistical analysis using ANOVA and regression...",
        "results": "Significant improvement (p<0.001) with 95% CI...",
        "entities": {
            "study_types": ["randomized controlled trial"],
            "sample_sizes": ["n=500"],
            "p_values": ["p<0.001", "p=0.03"],
            "confidence_intervals": ["95% CI: 1.2-3.4"],
            "software": ["R", "Python"],
            "code_availability": ["GitHub repository available"],
        },
    }

    result = scorer.calculate_score(example_paper)
    print(f"Quality Score: {result['total_score']}/100 ({result['grade']})")
    print(f"Strengths: {', '.join(result['strengths'])}")
    print(f"Weaknesses: {', '.join(result['weaknesses']) if result['weaknesses'] else 'None identified'}")
