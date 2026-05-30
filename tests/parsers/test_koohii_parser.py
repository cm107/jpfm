"""
Unit tests for Koohii parser service.

Tests use local fixtures in `tests/fixtures/koohii/current/` and avoid live network requests.
"""

import pytest
from pathlib import Path

from jpfm.parsers.koohii_parser import KoohiiParser


class TestKoohiiParserInitialization:
    def test_init_valid(self):
        html = "<html><body>ok</body></html>"
        p = KoohiiParser(html)
        assert p.soup is not None

    def test_init_invalid(self):
        with pytest.raises(ValueError):
            KoohiiParser("")


class TestKoohiiParserWithFixtures:
    @pytest.fixture
    def fixtures(self):
        dirp = Path(__file__).parent.parent / "fixtures" / "koohii" / "current"
        if not dirp.exists():
            pytest.skip("Koohii fixtures directory not found")
        files = list(dirp.glob("*.html"))
        if not files:
            pytest.skip("No Koohii fixture files found")
        return files

    def test_parse_structure(self, fixtures):
        for f in fixtures:
            html = f.read_text(encoding='utf-8')
            parser = KoohiiParser(html, url=str(f))
            res = parser.parse()
            if res is not None:
                assert 'kanji' in res
                assert 'mnemonic' in res
                assert isinstance(res['kanji'], str)
                assert isinstance(res['mnemonic'], str)

    def test_specific_fixture_values(self, fixtures):
        # Test specific known fixtures
        mapping = {f.stem: f for f in fixtures}
        if '愛' in mapping:
            html = mapping['愛'].read_text(encoding='utf-8')
            p = KoohiiParser(html)
            r = p.parse()
            assert r is not None
            assert r['kanji'] == '愛'
            assert 'heart' in r['mnemonic'] or 'love' in r['mnemonic']

        if '行' in mapping:
            html = mapping['行'].read_text(encoding='utf-8')
            p = KoohiiParser(html)
            r = p.parse()
            assert r is not None
            assert r['kanji'] == '行'

        if '音' in mapping:
            html = mapping['音'].read_text(encoding='utf-8')
            p = KoohiiParser(html)
            r = p.parse()
            assert r is not None
            assert r['kanji'] == '音'
            assert 'sound' in r['mnemonic']


class TestKoohiiParserResilience:
    def test_empty_page(self):
        html = "<html><body></body></html>"
        p = KoohiiParser(html)
        assert p.extract_kanji() == ""
        assert p.extract_mnemonic() == ""

    def test_malformed(self):
        html = "<html><body><div class='oops'></div>"
        p = KoohiiParser(html)
        r = p.parse()
        assert r is None or isinstance(r, dict)
