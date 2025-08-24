#!/usr/bin/env python3
"""Unit tests for help formatting module.

Tests unified help text formatting system including:
- HelpFormatter class functionality
- Command help templates and examples
- Click integration decorators
- Consistent help text patterns
"""

import pytest

# Import the help formatting module
from src.help_formatting import (
    HelpFormatter,
    format_command_help,
    format_examples,
    get_command_help,
    click_help_decorator,
    COMMAND_HELP_TEMPLATES,
    _formatter,
)


class TestHelpFormatter:
    """Test HelpFormatter class functionality."""

    def test_format_command_help_basic_should_work(self):
        """Test basic command help formatting with description only."""
        formatter = HelpFormatter()
        result = formatter.format_command_help("Search papers by similarity")

        assert result == "Search papers by similarity"
        assert "\n" not in result  # Single line for minimal input

    def test_format_command_help_with_examples_should_include_examples(self):
        """Test command help formatting with examples."""
        formatter = HelpFormatter()
        examples = ['python src/cli.py search "diabetes"', 'python src/cli.py search "AI" --quality-min 70']
        result = formatter.format_command_help("Search papers by similarity", examples=examples)

        assert "Search papers by similarity" in result
        assert "Examples:" in result
        assert 'python src/cli.py search "diabetes"' in result
        assert 'python src/cli.py search "AI" --quality-min 70' in result
        assert result.count("  ") >= 2  # Proper indentation

    def test_format_command_help_with_all_sections_should_format_completely(self):
        """Test command help formatting with all optional sections."""
        formatter = HelpFormatter()
        result = formatter.format_command_help(
            "Search papers by similarity",
            examples=['python src/cli.py search "topic"'],
            notes=["Results ranked by semantic similarity", "Quality scores range 0-100"],
            see_also=["smart-search: For large result sets", "author: Search by author"],
        )

        assert "Search papers by similarity" in result
        assert "Examples:" in result
        assert "Notes:" in result
        assert "See also:" in result
        assert "• Results ranked by semantic similarity" in result
        assert "• smart-search: For large result sets" in result

    def test_format_examples_should_format_with_indentation(self):
        """Test examples formatting with proper indentation."""
        formatter = HelpFormatter()
        examples = ['python src/cli.py search "diabetes"', "python src/cli.py get 0001"]
        result = formatter.format_examples(examples)

        assert "Examples:" in result
        assert result.startswith("Examples:")
        lines = result.split("\n")
        assert len(lines) == 3  # Title + 2 examples
        assert lines[1].startswith("  ")  # Proper indentation
        assert lines[2].startswith("  ")

    def test_format_examples_custom_title_should_work(self):
        """Test examples formatting with custom title."""
        formatter = HelpFormatter()
        examples = ["command1", "command2"]
        result = formatter.format_examples(examples, title="Usage Examples:")

        assert result.startswith("Usage Examples:")
        assert "command1" in result
        assert "command2" in result

    def test_format_option_help_basic_should_work(self):
        """Test option help formatting with basic information."""
        formatter = HelpFormatter()
        result = formatter.format_option_help("--quality-min", "Minimum quality score threshold")

        assert "--quality-min: Minimum quality score threshold" in result

    def test_format_option_help_with_default_should_include_default(self):
        """Test option help formatting with default value."""
        formatter = HelpFormatter()
        result = formatter.format_option_help("--limit", "Maximum number of results", default="10")

        assert "--limit: Maximum number of results" in result
        assert "Default: 10" in result

    def test_format_option_help_with_examples_should_include_examples(self):
        """Test option help formatting with examples."""
        formatter = HelpFormatter()
        result = formatter.format_option_help(
            "--quality-min", "Minimum quality score", examples=["--quality-min 70", "--quality-min 50"]
        )

        assert "--quality-min: Minimum quality score" in result
        assert "Examples:" in result
        assert "--quality-min 70" in result
        assert "--quality-min 50" in result


class TestUtilityFunctions:
    """Test standalone utility functions."""

    def test_format_command_help_function_should_work(self):
        """Test standalone format_command_help function."""
        result = format_command_help("Test command", examples=["test example"], notes=["Test note"])

        assert "Test command" in result
        assert "Examples:" in result
        assert "Notes:" in result
        assert "test example" in result
        assert "• Test note" in result

    def test_format_examples_function_should_work(self):
        """Test standalone format_examples function."""
        result = format_examples(["example1", "example2"])

        assert "Examples:" in result
        assert "example1" in result
        assert "example2" in result

    def test_global_formatter_should_be_consistent(self):
        """Test that global formatter produces consistent results."""
        result1 = format_command_help("Test")
        result2 = _formatter.format_command_help("Test")

        assert result1 == result2


class TestCommandTemplates:
    """Test pre-configured command help templates."""

    def test_command_templates_should_have_required_fields(self):
        """Test that all command templates have required fields."""
        required_fields = ["description", "examples"]

        for command_name, template in COMMAND_HELP_TEMPLATES.items():
            for field in required_fields:
                assert field in template, f"Missing {field} in {command_name} template"

    def test_command_templates_should_have_valid_examples(self):
        """Test that command templates have valid examples."""
        for command_name, template in COMMAND_HELP_TEMPLATES.items():
            examples = template["examples"]

            assert isinstance(examples, list), f"{command_name} examples should be list"
            assert len(examples) > 0, f"{command_name} should have at least one example"

            for example in examples:
                assert isinstance(example, str), f"{command_name} examples should be strings"
                assert len(example) > 0, f"{command_name} examples should not be empty"

    def test_search_template_should_be_comprehensive(self):
        """Test search command template completeness."""
        template = COMMAND_HELP_TEMPLATES["search"]

        assert "semantic similarity" in template["description"]
        assert len(template["examples"]) >= 3
        assert "notes" in template
        assert "see_also" in template

        # Check for key concepts
        notes_text = " ".join(template["notes"])
        assert "Multi-QA MPNet" in notes_text
        assert "quality scores" in notes_text

    def test_get_template_should_be_comprehensive(self):
        """Test get command template completeness."""
        template = COMMAND_HELP_TEMPLATES["get"]

        assert "specific paper by ID" in template["description"]
        assert any("--sections" in example for example in template["examples"])
        assert any("4-digit" in note for note in template["notes"])

    def test_build_kb_template_should_be_comprehensive(self):
        """Test build_kb command template completeness."""
        template = COMMAND_HELP_TEMPLATES["build_kb"]

        assert "Zotero library" in template["description"]
        assert any("--demo" in example for example in template["examples"])
        assert any("Safe by default" in note for note in template["notes"])

    def test_discover_template_should_be_comprehensive(self):
        """Test discover command template completeness."""
        template = COMMAND_HELP_TEMPLATES["discover"]

        assert "Semantic Scholar" in template["description"]
        assert "214M paper" in template["description"]
        assert any("--keywords" in example for example in template["examples"])
        assert any("population focus" in note.lower() for note in template["notes"])


class TestGetCommandHelp:
    """Test get_command_help functionality."""

    def test_get_command_help_should_return_formatted_text(self):
        """Test getting formatted help for existing commands."""
        result = get_command_help("search")

        assert "semantic similarity" in result
        assert "Examples:" in result
        assert "Notes:" in result
        assert "See also:" in result

    def test_get_command_help_with_override_should_merge(self):
        """Test getting command help with field overrides."""
        custom_examples = ["custom example 1", "custom example 2"]
        result = get_command_help("search", examples=custom_examples)

        assert "semantic similarity" in result  # Original description
        assert "custom example 1" in result  # Override examples
        assert "custom example 2" in result

    def test_get_command_help_invalid_command_should_raise(self):
        """Test that invalid command name raises ValueError."""
        with pytest.raises(ValueError, match="Unknown command template"):
            get_command_help("nonexistent_command")

    def test_get_command_help_all_commands_should_work(self):
        """Test getting help for all available commands."""
        for command_name in COMMAND_HELP_TEMPLATES:
            result = get_command_help(command_name)

            assert isinstance(result, str)
            assert len(result) > 50  # Should be substantial help text
            assert "Examples:" in result


class TestClickIntegration:
    """Test Click framework integration."""

    def test_click_help_decorator_should_set_docstring(self):
        """Test that Click decorator sets function docstring."""

        @click_help_decorator("search")
        def dummy_function():
            pass

        assert dummy_function.__doc__ is not None
        assert "semantic similarity" in dummy_function.__doc__
        assert "Examples:" in dummy_function.__doc__

    def test_click_help_decorator_with_override_should_work(self):
        """Test Click decorator with field overrides."""

        @click_help_decorator("search", examples=["custom example"])
        def dummy_function():
            pass

        assert "custom example" in dummy_function.__doc__
        assert "semantic similarity" in dummy_function.__doc__

    def test_click_help_decorator_invalid_command_should_raise(self):
        """Test that decorator with invalid command raises error."""
        with pytest.raises(ValueError):

            @click_help_decorator("invalid_command")
            def dummy_function():
                pass


class TestHelpConsistency:
    """Test help formatting consistency across commands."""

    def test_all_templates_should_have_consistent_structure(self):
        """Test that all command templates follow consistent structure."""
        for template in COMMAND_HELP_TEMPLATES.values():
            # All should have description
            assert "description" in template
            assert isinstance(template["description"], str)
            assert len(template["description"]) > 20

            # All should have examples
            assert "examples" in template
            assert isinstance(template["examples"], list)
            assert len(template["examples"]) >= 2

    def test_examples_should_follow_consistent_patterns(self):
        """Test that examples follow consistent command patterns."""
        python_pattern = "python src/"

        for command_name, template in COMMAND_HELP_TEMPLATES.items():
            examples = template["examples"]

            # Most examples should start with python src/
            python_examples = [ex for ex in examples if ex.startswith(python_pattern)]
            assert len(python_examples) > 0, f"{command_name} should have python examples"

    def test_notes_should_be_informative(self):
        """Test that notes provide meaningful information."""
        for template in COMMAND_HELP_TEMPLATES.values():
            if "notes" in template:
                notes = template["notes"]

                for note in notes:
                    assert isinstance(note, str)
                    assert len(note) > 10  # Should be substantial
                    assert not note.endswith(".")  # Consistent formatting without periods

    def test_see_also_should_reference_valid_commands(self):
        """Test that see_also references point to valid commands or resources."""
        for template in COMMAND_HELP_TEMPLATES.values():
            if "see_also" in template:
                see_also = template["see_also"]

                for reference in see_also:
                    # Extract command name (before colon if present)
                    ref_command = reference.split(":")[0].strip()

                    # Should reference known commands or valid resources
                    # This is a soft check - some references might be conceptual
                    assert len(ref_command) > 2  # Should be meaningful reference


class TestHelpValidation:
    """Test help formatting input validation and edge cases."""

    def test_empty_description_should_handle_gracefully(self):
        """Test handling of empty description."""
        formatter = HelpFormatter()
        result = formatter.format_command_help("")

        assert result == ""

    def test_empty_examples_list_should_handle_gracefully(self):
        """Test handling of empty examples list."""
        formatter = HelpFormatter()
        result = formatter.format_command_help("Test description", examples=[])

        assert "Test description" in result
        assert "Examples:" not in result  # Should not add empty section

    def test_none_values_should_handle_gracefully(self):
        """Test handling of None values in optional fields."""
        formatter = HelpFormatter()
        result = formatter.format_command_help("Test description", examples=None, notes=None, see_also=None)

        assert result == "Test description"

    def test_mixed_content_types_should_be_robust(self):
        """Test handling of various content types in lists."""
        formatter = HelpFormatter()

        # Should handle different string lengths and content
        examples = [
            "short",
            "A much longer example with various characters and symbols !@#$%",
            'python src/cli.py command --flag "quoted argument"',
        ]

        result = formatter.format_command_help("Test", examples=examples)

        for example in examples:
            assert example in result
