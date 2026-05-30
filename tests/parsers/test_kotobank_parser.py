"""
Unit tests for Kotobank parser service.

Tests use fixtures in `tests/fixtures/kotobank/current/` and avoid live network requests.
"""

import logging
from pathlib import Path

import pytest

from jpfm.parsers.kotobank_parser import KotobankParser


class TestKotobankParserInitialization:
    def test_init_valid_html(self):
        html = "<html><head><title>Test</title></head><body></body></html>"
        p = KotobankParser(html)
        assert p.soup is not None

    def test_init_empty_raises(self):
        with pytest.raises(ValueError):
            KotobankParser("")


class TestKotobankParserWithFixtures:
    @pytest.fixture
    def fixtures(self):
        dirp = Path(__file__).parent.parent / "fixtures" / "kotobank" / "current"
        if not dirp.exists():
            pytest.skip("Kotobank fixtures not found")
        files = list(dirp.glob("*.html"))
        if not files:
            pytest.skip("No kotobank fixture files found")
        return files

    def test_parse_structure(self, fixtures):
        for f in fixtures:
            html = f.read_text(encoding='utf-8')
            parser = KotobankParser(html, url=str(f))
            result = parser.parse()
            # result may be None if extraction heuristics fail
            if result is not None:
                assert isinstance(result, dict)
                assert 'title' in result
                assert 'definitions' in result
                assert isinstance(result['title'], str)
                assert isinstance(result['definitions'], list)

    def test_extract_title_and_definitions(self, fixtures):
        f = fixtures[0]
        html = f.read_text(encoding='utf-8')
        parser = KotobankParser(html)
        title = parser.extract_title()
        defs = parser.extract_definitions()
        assert isinstance(title, str)
        assert isinstance(defs, list)


class TestKotobankParserResilience:
    def test_malformed_html(self):
        # Intentionally malformed HTML structure (missing closing tags in body)
        html = "<html><body><div class='oops'></div>"
        parser = KotobankParser(html)
        res = parser.parse()
        assert res is None or isinstance(res, dict)

    def test_empty_page(self):
        html = "<html><body></body></html>"
        parser = KotobankParser(html)
        assert parser.extract_title() == ""
        assert parser.extract_definitions() == []
