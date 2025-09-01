#!/usr/bin/env python3
"""Unit tests for enhanced extraction improvements."""

import pytest
from src.simple_post_processor import SimplePostProcessor, StructuredAbstractHandler
from src.enhanced_extraction import EnhancedAbstractExtractor, ContentBasedBoundaryDetector
import re


class TestSimplePostProcessor:
    """Tests for simplified post-processing pipeline."""

    def test_contamination_removal(self):
        """Test removal of content that belongs to other sections."""
        processor = SimplePostProcessor()

        # Abstract with keywords contamination - make it longer to pass minimum length
        sections = {
            "abstract": "This comprehensive abstract presents our research findings on machine learning applications in healthcare, demonstrating significant improvements in diagnostic accuracy and treatment outcomes across multiple clinical domains and patient populations. Keywords: machine learning, AI"
        }
        result = processor.process_sections(sections)
        assert "Keywords:" not in result.get("abstract", "")
        assert "comprehensive abstract presents" in result.get("abstract", "")

    def test_artifact_cleaning(self):
        """Test removal of common PDF extraction artifacts."""
        processor = SimplePostProcessor()

        sections = {
            "methods": "We used multiple spaces and this is a longer section to meet the minimum word count requirement for methods sections which needs at least twenty words.\n\n\n\nAnd many newlines."
        }
        result = processor.process_sections(sections)
        assert "We used multiple spaces" in result["methods"]
        assert "\n\n\n" not in result["methods"]

    def test_length_limits(self):
        """Test application of minimum length constraints (NO MAX limits)."""
        processor = SimplePostProcessor()

        # Too short abstract vs very long methods
        sections = {
            "abstract": "Short",
            "methods": "word " * 5000,  # Very long - should NOT be truncated
        }
        result = processor.process_sections(sections)

        assert "abstract" not in result  # Too short, rejected
        assert "methods" in result
        assert len(result["methods"]) > 15000  # NO truncation - preserves all content

    def test_validation(self):
        """Test validation checks."""
        processor = SimplePostProcessor()

        sections = {
            "abstract": "This comprehensive abstract contains sufficient content to pass validation requirements, with more than twenty words describing research objectives, methodology, and findings from our systematic investigation.",
            "introduction": "Too few",  # Less than 15 words
        }
        result = processor.process_sections(sections)

        assert "abstract" in result
        assert "introduction" not in result  # Failed validation

    def test_section_marker_truncation(self):
        """Test truncation at next section markers."""
        processor = SimplePostProcessor()

        sections = {
            "introduction": "Introduction text here. 2. Methods This should be removed.",
            "methods": "Methods content. 3. Results This should also be removed.",
        }
        result = processor.process_sections(sections)

        assert "2. Methods" not in result.get("introduction", "")
        assert "3. Results" not in result.get("methods", "")

    def test_hyphenation_fix(self):
        """Test fixing of hyphenation at line breaks."""
        processor = SimplePostProcessor()

        sections = {
            "abstract": "This research paper contains a hyph- enated word that should be fixed during post-processing, along with twenty additional words to ensure the abstract meets minimum validation requirements for acceptance."
        }
        result = processor.process_sections(sections)

        assert "hyphenated" in result["abstract"]
        assert "hyph- enated" not in result["abstract"]


class TestStructuredAbstractHandler:
    """Tests for structured abstract handling."""

    def test_structured_abstract_detection(self):
        """Test detection of structured abstracts."""
        handler = StructuredAbstractHandler()

        structured = "Background: This study... Methods: We conducted... Results: The findings..."
        unstructured = "This is a regular abstract without any structure markers."

        cleaned_structured = handler.clean_structured_abstract(structured)
        cleaned_unstructured = handler.clean_structured_abstract(unstructured)

        # Structured should have markers removed
        assert "Background:" not in cleaned_structured
        assert "Methods:" not in cleaned_structured
        assert "This study" in cleaned_structured
        assert "We conducted" in cleaned_structured

        # Unstructured should remain unchanged
        assert cleaned_unstructured == unstructured

    def test_marker_removal(self):
        """Test removal of all types of structured markers."""
        handler = StructuredAbstractHandler()

        abstract = """
        Objective: To evaluate the effectiveness.
        Design: Randomized controlled trial.
        Setting: Academic medical center.
        Participants: 100 patients.
        Results: Significant improvement observed.
        Conclusion: The intervention was effective.
        """

        cleaned = handler.clean_structured_abstract(abstract)

        # All markers should be removed
        for marker in ["Objective:", "Design:", "Setting:", "Participants:", "Results:", "Conclusion:"]:
            assert marker not in cleaned

        # Content should be preserved
        assert "evaluate the effectiveness" in cleaned
        assert "Randomized controlled trial" in cleaned
        assert "100 patients" in cleaned

    def test_sentence_flow_fixing(self):
        """Test fixing of sentence flow after marker removal."""
        handler = StructuredAbstractHandler()

        abstract = "Background: first sentence Methods: Second sentence"
        cleaned = handler.clean_structured_abstract(abstract)

        # Should add period between sentences
        assert "first sentence. Second sentence" in cleaned or "first sentence Second sentence" in cleaned

    def test_component_extraction(self):
        """Test extraction of structured components separately."""
        handler = StructuredAbstractHandler()

        abstract = """
        Background: Diabetes is prevalent.
        Methods: Cross-sectional study.
        Results: 50% had poor control.
        Conclusion: Intervention needed.
        """

        components = handler.extract_structured_components(abstract)

        assert components is not None
        assert "background" in components
        assert "Diabetes is prevalent" in components["background"]
        assert "methods" in components
        assert "Cross-sectional study" in components["methods"]


class TestEnhancedAbstractExtractor:
    """Tests for enhanced abstract extraction strategies."""

    def test_metadata_strategy(self):
        """Test using metadata as primary source."""
        extractor = EnhancedAbstractExtractor()

        text = "Some paper text without clear abstract."
        metadata = {
            "abstract": "This is the abstract from metadata with enough words to pass validation. It needs at least twenty words and fifty characters total to be accepted."
        }

        result = extractor.extract_abstract(text, metadata)

        assert result is not None
        assert "abstract from metadata" in result.content
        assert result.method == "metadata"
        assert result.confidence == 1.0

    def test_labeled_abstract_extraction(self):
        """Test extraction with explicit abstract label."""
        extractor = EnhancedAbstractExtractor()

        text = """
        Title of Paper

        Abstract
        This is the abstract content with multiple sentences providing comprehensive information.
        It contains important information about the study methodology and findings.
        The abstract has enough words to meet the minimum validation requirements.
        We ensure it passes all the checks by having more than twenty words.

        Introduction
        The introduction begins here.
        """

        result = extractor.extract_abstract(text, None)

        assert result is not None
        assert "abstract content" in result.content
        assert "The introduction begins" not in result.content
        assert result.method in ["labeled", "positional", "structured"]

    def test_positional_extraction(self):
        """Test extraction based on position."""
        extractor = EnhancedAbstractExtractor()

        text = """
        Paper Title
        Authors

        This substantial paragraph appears before the introduction and contains
        enough text to be considered an abstract. It has multiple sentences and
        provides a summary of the research conducted in this paper. We add more
        content here to ensure it meets the minimum word count requirement of
        twenty words for validation purposes.

        1. Introduction

        The formal introduction starts here.
        """

        result = extractor.extract_abstract(text, None)

        assert result is not None
        assert "substantial paragraph" in result.content
        assert "formal introduction" not in result.content

    def test_structured_abstract_extraction(self):
        """Test extraction of structured abstracts."""
        extractor = EnhancedAbstractExtractor()

        text = """
        Title

        Background: This study examines the effectiveness of digital health interventions.
        Methods: We used a cross-sectional design with a large sample size.
        Results: The analysis showed significant improvements in patient outcomes.
        Conclusion: These findings suggest that digital health is effective for managing chronic conditions.

        Introduction
        """

        result = extractor.extract_abstract(text, None)

        assert result is not None
        assert "Background:" in result.content or "This study examines" in result.content
        assert result.confidence >= 0.7

    def test_fallback_extraction(self):
        """Test fallback to first substantial paragraph."""
        extractor = EnhancedAbstractExtractor()

        text = """
        Short title

        Authors

        This is the first substantial paragraph with enough content to serve as an
        abstract fallback. It contains multiple sentences and provides context about
        the research study. We ensure it has more than twenty words to pass the
        validation requirements for abstract content.

        Another paragraph here.
        """

        result = extractor.extract_abstract(text, None)

        assert result is not None
        assert "first substantial paragraph" in result.content
        assert result.method in ["fallback", "positional"]

    def test_validation_rejects_contaminated(self):
        """Test that validation rejects contaminated abstracts."""
        extractor = EnhancedAbstractExtractor()

        # Manually test validation - needs enough words
        bad_content = "This is abstract content with enough words to pass the minimum word count requirement for validation. Keywords: test, keywords"
        assert not extractor._validate_abstract(bad_content)

        bad_content2 = (
            "This is an abstract with plenty of words to meet requirements. 1. Introduction begins here"
        )
        assert not extractor._validate_abstract(bad_content2)

        good_content = "This is a clean abstract with enough content and no contamination. It has plenty of words to meet the minimum requirement of twenty words total."
        assert extractor._validate_abstract(good_content)


class TestContentBasedBoundaryDetector:
    """Tests for content-based section boundary detection."""

    def test_find_next_section_boundary(self):
        """Test finding boundaries based on next section indicators."""
        detector = ContentBasedBoundaryDetector()

        text = """Abstract content here.
        More abstract text.

        Introduction

        The introduction begins here.
        """

        # Find boundary for abstract section
        start_pos = 0
        end_pos = detector.find_section_boundary(text, start_pos, "abstract")

        abstract_content = text[start_pos:end_pos]
        assert "Abstract content" in abstract_content
        assert "Introduction" not in abstract_content
        assert "The introduction begins" not in abstract_content

    def test_max_length_enforcement(self):
        """Test that maximum lengths are enforced."""
        detector = ContentBasedBoundaryDetector()

        # Create very long text
        text = "Abstract. " + ("Long content. " * 1000)

        start_pos = 10  # After "Abstract. "
        end_pos = detector.find_section_boundary(text, start_pos, "abstract")

        section_length = end_pos - start_pos
        assert section_length <= 5000  # Max for abstract

    def test_clean_paragraph_breaks(self):
        """Test finding clean breaks at paragraph boundaries."""
        detector = ContentBasedBoundaryDetector()

        text = """Methods section content here.
        This is a complete paragraph.

        Another paragraph in methods.

        Results

        The results section starts here.
        """

        # Find methods boundary
        start_pos = 0
        end_pos = detector.find_section_boundary(text, start_pos, "methods")

        methods_content = text[start_pos:end_pos]
        # Should end at a paragraph break, not mid-sentence
        assert methods_content.rstrip().endswith(".")
        assert "Results" not in methods_content

    def test_numbered_section_detection(self):
        """Test detection of numbered sections."""
        detector = ContentBasedBoundaryDetector()

        text = """Introduction content here.
        More introduction text.

        2. Methods

        The methods section begins.
        """

        start_pos = 0
        end_pos = detector.find_section_boundary(text, start_pos, "introduction")

        intro_content = text[start_pos:end_pos]
        assert "2. Methods" not in intro_content
        assert "The methods section" not in intro_content

    def test_common_end_markers(self):
        """Test detection of common end markers."""
        detector = ContentBasedBoundaryDetector()

        text = """Discussion content here.
        More discussion text.

        Acknowledgments

        We thank the participants.
        """

        start_pos = 0
        end_pos = detector.find_section_boundary(text, start_pos, "discussion")

        discussion_content = text[start_pos:end_pos]
        assert "Discussion content" in discussion_content
        assert "Acknowledgments" not in discussion_content
        assert "We thank" not in discussion_content

    def test_extract_with_boundaries(self):
        """Test full extraction with boundary detection."""
        detector = ContentBasedBoundaryDetector()

        text = """
        Abstract
        This is the abstract content.

        Introduction
        The introduction starts here.
        """

        # Create a match object for "Abstract"
        match = re.search(r"Abstract", text)
        content, start_pos, end_pos = detector.extract_section_with_boundaries(text, "abstract", match)

        assert "This is the abstract content" in content
        assert "Introduction" not in content
        assert start_pos > match.end()
        assert end_pos > start_pos


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
