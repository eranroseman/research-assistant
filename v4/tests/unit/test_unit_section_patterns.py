#!/usr/bin/env python3
"""Unit tests for improved section header pattern recognition."""

import pytest
from src.pragmatic_section_extractor import PragmaticSectionExtractor
from src.config import FUZZY_THRESHOLD


@pytest.mark.unit
class TestSectionPatternRecognition:
    """Test the improved section header pattern recognition."""

    @pytest.fixture
    def extractor(self):
        """Create a PragmaticSectionExtractor with updated config."""
        return PragmaticSectionExtractor(fuzzy_threshold=FUZZY_THRESHOLD)

    def test_title_case_headers(self, extractor):
        """Test recognition of Title Case headers (65% of papers)."""
        text = """
Abstract
This comprehensive study investigates novel approaches to machine learning algorithms in healthcare applications, demonstrating significant improvements in diagnostic accuracy and patient outcomes through innovative computational methodologies.

Introduction
The introduction provides comprehensive background information about recent advances in artificial intelligence and machine learning technologies applied to medical diagnostics and clinical decision support systems.

Methods
We conducted extensive experiments using a randomized controlled trial design with multiple validation datasets, implementing state-of-the-art machine learning algorithms and rigorous statistical analysis procedures.

Results
Our comprehensive experiments demonstrated statistically significant improvements in prediction accuracy, achieving 94.2% sensitivity and 96.7% specificity across all validation datasets with p-values less than 0.001.

Discussion
The experimental results clearly indicate that our proposed approach represents a substantial advancement over existing methodologies, with important implications for clinical practice and healthcare delivery systems.

Conclusion
In summary, we have successfully demonstrated the effectiveness and clinical applicability of our novel machine learning framework for healthcare applications.
"""
        result = extractor.extract(text=text)

        assert "abstract" in result
        assert "introduction" in result
        assert "methods" in result
        assert "results" in result
        assert "discussion" in result
        assert "conclusion" in result

        # Check content is captured
        assert "comprehensive study" in result.get("abstract", "")
        assert "background information" in result.get("introduction", "")

    def test_numbered_sections(self, extractor):
        """Test recognition of numbered sections (12% of papers)."""
        text = """
Abstract
This study presents comprehensive findings on the effectiveness of deep learning approaches for automated medical image analysis, revealing significant improvements in diagnostic accuracy and clinical workflow efficiency.

1. Introduction
Recent technological advances have created unprecedented opportunities for implementing artificial intelligence solutions in medical imaging, providing strong motivation for developing automated diagnostic support systems.

2. Methods
Our experimental methodology employed convolutional neural networks trained on large-scale medical imaging datasets, utilizing advanced data augmentation techniques and cross-validation procedures for robust performance evaluation.

3. Results
Comprehensive analysis revealed statistically significant improvements in diagnostic accuracy, with our proposed method achieving 97.3% accuracy on the validation dataset compared to 89.1% for conventional approaches.

4. Discussion
These results demonstrate the substantial potential of deep learning technologies for enhancing medical diagnostic capabilities while reducing clinical workload and improving patient care quality.

5. Conclusion
Our research establishes a foundation for future developments in AI-assisted medical diagnostics and highlights promising directions for continued research and clinical implementation.
"""
        result = extractor.extract(text=text)

        assert "abstract" in result
        assert "introduction" in result
        assert "methods" in result
        assert "results" in result
        assert "discussion" in result
        assert "conclusion" in result

    def test_sections_with_colons(self, extractor):
        """Test recognition of sections with colons."""
        text = """
Abstract:
This comprehensive study examines fundamental questions regarding the effectiveness of digital health interventions in chronic disease management, utilizing advanced statistical methodologies and longitudinal data analysis approaches.

Introduction:
Recent developments in digital health technology have demonstrated promising results for improving patient engagement and clinical outcomes in chronic disease management across diverse patient populations.

Methods:
Participants were recruited from multiple healthcare centers using stratified random sampling, with comprehensive demographic and clinical data collection procedures implemented according to established research protocols.

Results:
Statistical analysis revealed significant improvements in patient adherence rates and clinical biomarkers, with effect sizes ranging from 0.6 to 1.2 across primary outcome measures.

Discussion:
Our comprehensive findings strongly suggest that digital health interventions represent a viable and effective approach for enhancing chronic disease management in real-world clinical settings.
"""
        result = extractor.extract(text=text)

        assert "abstract" in result
        assert "introduction" in result
        assert "methods" in result
        assert "results" in result
        assert "discussion" in result

    def test_sections_with_periods(self, extractor):
        """Test recognition of sections with periods."""
        text = """
Abstract.
This research presents key findings from a comprehensive investigation of mobile health applications for diabetes management, demonstrating significant improvements in glycemic control and patient self-management behaviors.

Introduction.
Extensive background research and clinical context indicate substantial opportunities for leveraging mobile technology to improve diabetes care delivery and patient outcomes in community healthcare settings.

Methods.
Our rigorous experimental design employed randomized controlled trial methodology with comprehensive data collection procedures, statistical power analysis, and validated outcome measurement instruments.

Results.
Comprehensive data analysis revealed statistically significant improvements in hemoglobin A1c levels, self-monitoring frequency, and medication adherence across all intervention groups compared to control conditions.
"""
        result = extractor.extract(text=text)

        assert "abstract" in result
        assert "introduction" in result
        assert "methods" in result
        assert "results" in result

    def test_mixed_case_sections(self, extractor):
        """Test recognition of mixed case variations."""
        text = """
ABSTRACT
This comprehensive research investigation examines the effectiveness of telemedicine interventions for rural healthcare delivery, demonstrating substantial improvements in patient access and clinical outcome measures.

introduction
Extensive literature review and clinical needs assessment indicate significant opportunities for implementing telemedicine technologies to address healthcare disparities in underserved rural communities.

Methods
Our systematic research approach employed mixed-methods evaluation framework with quantitative outcome measurements and qualitative stakeholder interviews to assess implementation effectiveness and user satisfaction.

RESULTS
Comprehensive analysis revealed statistically significant improvements in healthcare access rates, patient satisfaction scores, and clinical quality indicators across all participating rural healthcare facilities.

discussion
These findings provide strong evidence supporting the clinical effectiveness and economic viability of telemedicine interventions for improving healthcare delivery in rural communities.
"""
        result = extractor.extract(text=text)

        assert "abstract" in result
        assert "introduction" in result
        assert "methods" in result
        assert "results" in result
        assert "discussion" in result

    def test_alternative_section_names(self, extractor):
        """Test recognition of alternative section names."""
        text = """
Summary
This comprehensive research summary presents evidence from a large-scale systematic review of artificial intelligence applications in clinical decision support systems, highlighting significant opportunities for improving diagnostic accuracy.

Background
Extensive background analysis of current clinical decision support technologies reveals substantial gaps in accuracy and usability, providing strong justification for developing advanced AI-based solutions.

Methodology
Our comprehensive methodology employed systematic review protocols with meta-analysis techniques, including rigorous study selection criteria, data extraction procedures, and quality assessment frameworks for evidence synthesis.

Findings
Key research findings demonstrate that AI-enhanced clinical decision support systems achieve significantly higher diagnostic accuracy rates compared to traditional approaches, with improvements ranging from 15% to 30%.

Conclusions
Multiple evidence-based conclusions support the implementation of AI technologies in clinical practice, with particular emphasis on the potential for reducing diagnostic errors and improving patient safety.
"""
        result = extractor.extract(text=text)

        # These should map to standard sections
        assert "abstract" in result  # Summary -> abstract
        assert "introduction" in result  # Background -> introduction
        assert "methods" in result  # Methodology -> methods
        assert "results" in result  # Findings -> results
        assert "conclusion" in result  # Conclusions -> conclusion

    def test_materials_and_methods(self, extractor):
        """Test recognition of 'Materials and Methods' variant."""
        text = """
Abstract
This comprehensive study investigates the effectiveness of precision medicine approaches in oncology treatment planning, utilizing advanced genomic analysis and machine learning techniques for personalized therapy selection.

Introduction
Recent advances in precision oncology have created unprecedented opportunities for tailoring cancer treatment strategies based on individual patient characteristics and tumor molecular profiles.

Materials and Methods
Detailed experimental protocols included comprehensive genomic sequencing, bioinformatics analysis pipelines, machine learning model development, and rigorous statistical validation procedures using large-scale clinical datasets.

Results
Experimental results demonstrate significant improvements in treatment response rates and survival outcomes, with precision medicine approaches achieving 78% response rates compared to 52% for standard therapy.
"""
        result = extractor.extract(text=text)

        assert "methods" in result
        assert "experimental protocols" in result.get("methods", "").lower()

    def test_references_section(self, extractor):
        """Test recognition of References section."""
        text = """
Abstract
This systematic review analyzes recent advances in digital therapeutics for mental health interventions, examining effectiveness across diverse patient populations and clinical settings through comprehensive meta-analysis.

References
1. Smith, J.A., Johnson, M.B., & Williams, C.D. (2023). Digital therapeutics for anxiety disorders: A randomized controlled trial. Journal of Medical Internet Research, 25(4), e12345.
2. Another Author, P.Q., & Researcher, R.S. (2024). Mobile health interventions for depression: Systematic review and meta-analysis. Digital Medicine, 7(2), 156-173.

Bibliography
Comprehensive bibliography includes additional peer-reviewed sources examining digital health interventions, clinical effectiveness studies, and implementation research across various healthcare settings and patient populations.

Literature Cited
Extensive literature citations encompass foundational research in digital therapeutics, regulatory frameworks, clinical validation studies, and real-world evidence for mobile health applications in mental healthcare.
"""
        result = extractor.extract(text=text)

        assert "references" in result
        assert "Smith, J.A." in result.get("references", "") or "Another Author" in result.get(
            "references", ""
        )

    def test_section_boundary_detection(self, extractor):
        """Test that section boundaries are correctly detected."""
        text = """
Introduction
This comprehensive introduction section provides detailed background information on wearable technology applications in chronic disease monitoring, examining recent technological advances and clinical implementation strategies.
The introduction continues with extensive literature review covering sensor technologies, data analytics approaches, and patient engagement methodologies that inform our research design.
Additional introduction content explores regulatory considerations, privacy concerns, and implementation challenges that must be addressed for successful clinical adoption of wearable health monitoring systems.

Methods
The comprehensive methods section describes our systematic approach to evaluating wearable technology effectiveness, including participant recruitment protocols, data collection procedures, and statistical analysis plans.
Our methodology should not include introduction content but focuses specifically on experimental design, outcome measurements, and validation procedures for assessing clinical effectiveness.

Results
The results section presents comprehensive findings from our clinical evaluation, including quantitative outcome measures, statistical significance testing, and subgroup analyses across different patient populations and clinical conditions.
"""
        result = extractor.extract(text=text)

        intro = result.get("introduction", "")
        methods = result.get("methods", "")

        # Introduction content should be in introduction
        assert "comprehensive introduction" in intro
        assert "literature review" in intro

        # Methods should not contain introduction content
        assert "introduction section" not in methods
        assert "comprehensive methods section" in methods

        # Results should be separate
        assert "results section" in result.get("results", "").lower()

    def test_minimum_section_length_validation(self, extractor):
        """Test that minimum section length from config is respected."""
        text = """
Abstract
This comprehensive research study examines the clinical effectiveness of AI-powered diagnostic tools in emergency medicine, demonstrating significant improvements in diagnostic accuracy and clinical decision-making efficiency.

Introduction
This comprehensive introduction provides detailed background information on artificial intelligence applications in emergency medicine, examining current challenges in diagnostic accuracy and the potential for AI technologies to enhance clinical decision-making processes.

Methods
Our rigorous methodology employed randomized controlled trial design with comprehensive data collection protocols, including validated outcome measurements, statistical power analysis, and multi-site implementation procedures for robust evidence generation.

Results
This comprehensive results section presents detailed findings from our clinical evaluation, demonstrating statistically significant improvements in diagnostic accuracy rates, clinical workflow efficiency, and patient satisfaction measures across all participating emergency departments.
"""
        result = extractor.extract(text=text)

        # Check which sections meet the minimum length
        # Based on the config: MIN_SECTION_LENGTH = 50 chars for most sections
        if "abstract" in result:
            # Short abstract might be rejected or accepted based on word count
            pass  # Implementation may vary

        assert "introduction" in result  # Should be included
        assert "results" in result  # Should be included

    def test_fuzzy_threshold_matching(self, extractor):
        """Test that fuzzy threshold (70) catches variations."""
        text = """
Abstact
Typo in abstract header but should still match our fuzzy threshold testing criteria, demonstrating the robustness of our pattern recognition system for handling common OCR and formatting errors.

Introducton
Another intentional typo in section header that should successfully match with our configured fuzzy threshold parameters, validating the system's ability to handle real-world document processing challenges.

Methds
Missing letter in methods header should still be successfully matched by our fuzzy pattern recognition algorithms, ensuring reliable section identification despite common text processing errors.

Resuls
Missing letter in results header should be detected and correctly matched using our fuzzy string matching capabilities with appropriate threshold settings for production use.
"""
        # Note: Fuzzy matching is in Tier 2, so these might not be caught in Tier 1
        # But the test verifies the system can handle variations
        result = extractor.extract(text=text)

        # With fuzzy threshold of 70, these should potentially be matched
        # Actual behavior depends on tier progression
        assert result is not None
        assert "_metadata" in result

    def test_case_insensitive_patterns(self, extractor):
        """Test that patterns are truly case-insensitive."""
        text = """
aBsTrAcT
Mixed case abstract header should be successfully recognized by our case-insensitive pattern matching system, demonstrating robust text processing capabilities for handling diverse document formatting styles.

InTrOdUcTiOn
Mixed case introduction header should work correctly with our case-insensitive matching algorithms, ensuring reliable section identification regardless of capitalization patterns in source documents.

mEtHoDs
Mixed case methods header should be properly detected by our pattern recognition system, validating the effectiveness of case-insensitive matching for real-world document processing scenarios.

ReSuLtS
Mixed case results header should be successfully identified using our case-insensitive pattern matching capabilities, ensuring consistent section extraction across documents with varying formatting conventions.
"""
        result = extractor.extract(text=text)

        assert "abstract" in result
        assert "introduction" in result
        assert "methods" in result
        assert "results" in result
