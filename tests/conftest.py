"""
Pytest configuration and shared fixtures for JPFM test suite.

This module provides common fixtures for both unit tests and GUI tests using pytest-qt.
"""

import logging
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def test_logger():
    """
    Create a logger for test execution.

    Yields:
        logging.Logger: Configured test logger.
    """
    from jpfm import get_logger

    logger = get_logger("tests", level=logging.DEBUG)
    yield logger
    logging.shutdown()


@pytest.fixture
def fixtures_dir():
    """
    Return the path to the test fixtures directory.

    Returns:
        Path: Absolute path to tests/fixtures directory.
    """
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def jisho_fixtures_dir(fixtures_dir):
    """
    Return the path to Jisho-specific fixtures.

    Returns:
        Path: Absolute path to tests/fixtures/jisho/current directory.
    """
    jisho_dir = fixtures_dir / "jisho" / "current"
    jisho_dir.mkdir(parents=True, exist_ok=True)
    return jisho_dir


@pytest.fixture
def sample_jisho_html(jisho_fixtures_dir):
    """
    Provide a dictionary of available Jisho HTML fixtures.

    This fixture scans the jisho fixtures directory and returns paths
    to available HTML files, keyed by word name.

    Returns:
        dict: Mapping of word names to HTML file paths.
    """
    fixtures = {}
    if jisho_fixtures_dir.exists():
        for html_file in jisho_fixtures_dir.glob("*.html"):
            word = html_file.stem
            fixtures[word] = html_file
    return fixtures


@pytest.fixture
def mock_bs4_parse(monkeypatch):
    """
    Provide a fixture to mock BeautifulSoup parsing (for advanced use).

    This allows tests to inject mock HTML responses without making network requests.

    Args:
        monkeypatch: pytest monkeypatch fixture for mocking.

    Returns:
        callable: Mock function that can be used with monkeypatch.
    """

    def _mock_parser(html_string):
        """Mock BeautifulSoup to return parsed HTML from a string."""
        from bs4 import BeautifulSoup

        return BeautifulSoup(html_string, "html.parser")

    return _mock_parser
