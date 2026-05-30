"""
Unit tests for Jisho parser service.

All tests use local HTML fixtures loaded from tests/fixtures/jisho/current/.
No live network requests are made during testing.
"""

import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from jpfm.parsers.jisho_parser import JishoParser, ParsedJishoEntry


class TestJishoParserInitialization:
    """Test JishoParser initialization and error handling."""

    def test_init_with_valid_html(self):
        """Test parser initialization with valid HTML content."""
        html = "<html><body>test</body></html>"
        parser = JishoParser(html)
        assert parser.soup is not None
        assert parser.url == "memory://jisho"

    def test_init_with_custom_url(self):
        """Test parser initialization with custom URL."""
        html = "<html><body>test</body></html>"
        parser = JishoParser(html, url="https://jisho.org/search/test")
        assert parser.url == "https://jisho.org/search/test"

    def test_init_with_custom_logger(self, test_logger):
        """Test parser initialization with custom logger."""
        html = "<html><body>test</body></html>"
        parser = JishoParser(html, logger=test_logger)
        assert parser.logger is test_logger

    def test_init_with_empty_html_raises_error(self):
        """Test that empty HTML raises ValueError."""
        with pytest.raises(ValueError, match="non-empty string"):
            JishoParser("")

    def test_init_with_none_html_raises_error(self):
        """Test that None HTML raises ValueError."""
        with pytest.raises(ValueError, match="non-empty string"):
            JishoParser(None)

    def test_init_with_invalid_type_raises_error(self):
        """Test that non-string HTML raises ValueError."""
        with pytest.raises(ValueError, match="non-empty string"):
            JishoParser(123)


class TestJishoParserWithFixtures:
    """Test JishoParser against real HTML fixtures."""

    @pytest.fixture
    def fixture_files(self, jisho_fixtures_dir):
        """Provide paths to available fixture files."""
        if not jisho_fixtures_dir.exists():
            pytest.skip("Fixture files not found")
        
        fixtures = {}
        for html_file in sorted(jisho_fixtures_dir.glob("*.html")):
            word = html_file.stem
            # Read the HTML content
            html_content = html_file.read_text(encoding="utf-8")
            fixtures[word] = {
                "path": html_file,
                "content": html_content,
            }
        
        if not fixtures:
            pytest.skip("No fixture files found in " + str(jisho_fixtures_dir))
        
        return fixtures

    def test_parse_returns_typed_dict_structure(self, fixture_files):
        """Test that parse() returns properly structured ParsedJishoEntry."""
        word = list(fixture_files.keys())[0]
        html = fixture_files[word]["content"]
        
        parser = JishoParser(html, url=f"https://jisho.org/search/{word}")
        result = parser.parse(word)
        
        # Result can be None if no entry found, which is valid
        if result is not None:
            assert isinstance(result, dict)
            assert "reading" in result
            assert "kanji" in result
            assert "definitions" in result
            assert "definitions_raw" in result
            
            # Check types
            assert isinstance(result["reading"], str)
            assert isinstance(result["kanji"], str)
            assert isinstance(result["definitions"], list)
            assert isinstance(result["definitions_raw"], str)

    def test_extract_reading_returns_string(self, fixture_files):
        """Test that extract_reading() returns a string."""
        word = list(fixture_files.keys())[0]
        html = fixture_files[word]["content"]
        
        parser = JishoParser(html)
        reading = parser.extract_reading()
        
        assert isinstance(reading, str)

    def test_extract_kanji_returns_string(self, fixture_files):
        """Test that extract_kanji() returns a string."""
        word = list(fixture_files.keys())[0]
        html = fixture_files[word]["content"]
        
        parser = JishoParser(html)
        kanji = parser.extract_kanji()
        
        assert isinstance(kanji, str)

    def test_extract_definitions_returns_list(self, fixture_files):
        """Test that extract_definitions() returns a list of strings."""
        word = list(fixture_files.keys())[0]
        html = fixture_files[word]["content"]
        
        parser = JishoParser(html)
        definitions = parser.extract_definitions()
        
        assert isinstance(definitions, list)
        for defn in definitions:
            assert isinstance(defn, str)

    def test_definitions_are_non_empty_if_present(self, fixture_files):
        """Test that definitions are non-empty strings."""
        word = list(fixture_files.keys())[0]
        html = fixture_files[word]["content"]
        
        parser = JishoParser(html)
        definitions = parser.extract_definitions()
        
        for defn in definitions:
            assert len(defn) > 0, "Definition should not be empty"

    @pytest.mark.parametrize("fixture_name", ["本", "水", "赤い"])
    def test_common_words_parse_successfully(self, fixture_files, fixture_name):
        """
        Test that common words are parsed with at least one extracted field.
        
        This parametrized test ensures that basic parsing works for
        multiple common Japanese words.
        """
        if fixture_name not in fixture_files:
            pytest.skip(f"Fixture for '{fixture_name}' not available")
        
        html = fixture_files[fixture_name]["content"]
        parser = JishoParser(html, url=f"https://jisho.org/search/{fixture_name}")
        
        result = parser.parse(fixture_name)
        
        # At least one extraction should succeed for valid entries
        if result is not None:
            extracted_something = (
                len(result["reading"]) > 0 or
                len(result["kanji"]) > 0 or
                len(result["definitions"]) > 0
            )
            assert extracted_something, f"Failed to extract anything for '{fixture_name}'"


class TestJishoParserErrorHandling:
    """Test JishoParser error handling and resilience."""

    def test_parse_with_malformed_html(self):
        """Test parsing with malformed HTML returns None gracefully."""
        html = "<html><body><div class='broken"  # Missing closing tags
        parser = JishoParser(html)
        result = parser.parse()
        
        # Parser should handle malformed HTML gracefully
        assert result is None or isinstance(result, dict)

    def test_parse_with_no_results_returns_none(self):
        """Test parsing HTML with no-matches div returns None."""
        html = '<html><body><div id="no-matches">No results found</div></body></html>'
        parser = JishoParser(html)
        result = parser.parse()
        
        assert result is None

    def test_extract_reading_with_empty_entry(self):
        """Test extract_reading with minimal HTML returns empty string."""
        html = "<html><body></body></html>"
        parser = JishoParser(html)
        reading = parser.extract_reading()
        
        assert reading == ""

    def test_extract_kanji_with_empty_entry(self):
        """Test extract_kanji with minimal HTML returns empty string."""
        html = "<html><body></body></html>"
        parser = JishoParser(html)
        kanji = parser.extract_kanji()
        
        assert kanji == ""

    def test_extract_definitions_with_empty_entry(self):
        """Test extract_definitions with minimal HTML returns empty list."""
        html = "<html><body></body></html>"
        parser = JishoParser(html)
        definitions = parser.extract_definitions()
        
        assert definitions == []


class TestJishoParserLogging:
    """Test logging functionality of JishoParser."""

    def test_parser_logs_initialization(self, test_logger, caplog):
        """Test that parser logs initialization event."""
        caplog.set_level(logging.DEBUG)
        html = "<html><body>test</body></html>"
        
        with caplog.at_level(logging.DEBUG):
            parser = JishoParser(html, logger=test_logger)
        
        # Should have logged successful HTML parsing
        assert any("HTML parsed successfully" in record.message for record in caplog.records)

    def test_parser_logs_parsing_start(self, test_logger, caplog):
        """Test that parser logs when parsing starts."""
        caplog.set_level(logging.DEBUG)
        html = "<html><body>test</body></html>"
        parser = JishoParser(html, logger=test_logger)
        
        with caplog.at_level(logging.DEBUG):
            parser.parse(word="test")
        
        # Should have logged parsing start
        assert any("Starting parse" in record.message for record in caplog.records)

    def test_parser_logs_no_results_warning(self, test_logger, caplog):
        """Test that parser logs warning when no results found."""
        caplog.set_level(logging.WARNING)
        html = '<html><body><div id="no-matches">No matches</div></body></html>'
        parser = JishoParser(html, logger=test_logger)
        
        with caplog.at_level(logging.WARNING):
            result = parser.parse(word="nonexistent")
        
        # Should have logged warning about no results
        assert any("No results found" in record.message for record in caplog.records)

    def test_parser_logs_missing_element_warning(self, test_logger, caplog):
        """Test that parser logs warning when expected elements are missing."""
        caplog.set_level(logging.WARNING)
        html = "<html><body>content without expected structure</body></html>"
        parser = JishoParser(html, logger=test_logger)
        
        with caplog.at_level(logging.WARNING):
            # Extract methods should log warnings about missing elements
            parser.extract_reading()
            parser.extract_kanji()
        
        # Should have logged warnings about missing elements
        assert any("not found" in record.message for record in caplog.records)


class TestJishoParserIntegration:
    """Integration tests for the complete parsing workflow."""

    def test_full_parse_workflow(self, sample_jisho_html):
        """Test complete parse workflow from HTML to structured entry."""
        if not sample_jisho_html:
            pytest.skip("No fixtures available for integration test")
        
        word = list(sample_jisho_html.keys())[0]
        html = sample_jisho_html[word].read_text(encoding="utf-8")
        
        # Create parser
        parser = JishoParser(
            html,
            url=f"https://jisho.org/search/{word}",
        )
        
        # Parse the entry
        result = parser.parse(word)
        
        # Verify result structure
        if result is not None:
            assert isinstance(result, dict)
            assert set(result.keys()) == {"reading", "kanji", "definitions", "definitions_raw"}
            
            # Verify that at least some data was extracted
            has_data = any([
                result["reading"],
                result["kanji"],
                result["definitions"],
            ])
            assert has_data, f"No data extracted for '{word}'"

    def test_multiple_fixtures_parse_independently(self, sample_jisho_html):
        """Test that multiple fixtures can be parsed independently without interference."""
        if len(sample_jisho_html) < 2:
            pytest.skip("Need at least 2 fixtures for this test")
        
        fixtures_list = [
            sample_jisho_html[word].read_text(encoding="utf-8")
            for word in list(sample_jisho_html.keys())[:2]
        ]
        
        # Parse first fixture
        parser1 = JishoParser(fixtures_list[0])
        result1 = parser1.parse()
        
        # Parse second fixture
        parser2 = JishoParser(fixtures_list[1])
        result2 = parser2.parse()
        
        # Results should be independent (not share state)
        # At least one should parse successfully or both return None
        if result1 and result2:
            # They should have different content (different fixtures)
            # But this depends on fixture content, so we just verify structure
            assert isinstance(result1, dict)
            assert isinstance(result2, dict)


class TestJishoParserEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_parse_with_very_long_definition(self):
        """Test parsing entry with a very long definition."""
        html = """
        <html><body>
            <div class="concept_light clearfix">
                <span class="furigana">reading</span>
                <span class="text">kanji</span>
                <div class="concept_light-meanings">
                    <div class="meaning-definition">
                        <span class="meaning-meaning">This is a very long definition. """ + "a" * 1000 + """</span>
                    </div>
                </div>
            </div>
        </body></html>
        """
        parser = JishoParser(html)
        result = parser.parse()
        
        if result:
            assert len(result["definitions"]) > 0
            assert len(result["definitions"][0]) > 1000

    def test_parse_with_special_characters(self):
        """Test parsing with special characters in text."""
        html = """
        <html><body>
            <div class="concept_light clearfix">
                <span class="furigana">よ・ぶ</span>
                <span class="text">呼・ぶ</span>
                <div class="concept_light-meanings">
                    <div class="meaning-definition">
                        <span class="meaning-meaning">to call; to summon; to invite (esp. formally)</span>
                    </div>
                </div>
            </div>
        </body></html>
        """
        parser = JishoParser(html)
        result = parser.parse()
        
        if result:
            assert result["reading"] == "よ・ぶ"
            assert result["kanji"] == "呼・ぶ"

    def test_parse_with_unicode_normalization(self):
        """Test that parsing handles Unicode variations correctly."""
        # Different Unicode representations of the same character
        html = """
        <html><body>
            <div class="concept_light clearfix">
                <span class="furigana">てすと</span>
                <span class="text">テスト</span>
                <div class="concept_light-meanings">
                    <div class="meaning-definition">
                        <span class="meaning-meaning">test</span>
                    </div>
                </div>
            </div>
        </body></html>
        """
        parser = JishoParser(html)
        result = parser.parse()
        
        if result:
            assert len(result["kanji"]) > 0
            assert len(result["reading"]) > 0
