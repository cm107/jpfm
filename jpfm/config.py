"""
Configuration loader for JPFM application.

This module loads and validates the central config.yaml file and exposes
configuration values as module-level constants for use across the application.
"""

import logging
from pathlib import Path
from typing import Any, Dict

import yaml

# Path to config.yaml
CONFIG_FILE = Path(__file__).parent.parent / "config" / "config.yaml"


def _load_config() -> Dict[str, Any]:
    """
    Load and parse config.yaml.

    Returns:
        Dict: Parsed configuration dictionary.

    Raises:
        FileNotFoundError: If config.yaml does not exist.
        yaml.YAMLError: If config.yaml is malformed.
    """
    if not CONFIG_FILE.exists():
        raise FileNotFoundError(f"Configuration file not found: {CONFIG_FILE}")

    with open(CONFIG_FILE, "r") as f:
        config = yaml.safe_load(f)

    if config is None:
        config = {}

    return config


# Load configuration at module import time
_CONFIG = _load_config()

# Dictionary source URLs and timeouts
JISHO_URL = _CONFIG.get("jisho", {}).get("base_url", "https://jisho.org/search/")
JISHO_TIMEOUT = _CONFIG.get("jisho", {}).get("timeout_seconds", 10)
JISHO_MAX_RETRIES = _CONFIG.get("jisho", {}).get("max_retries", 3)
JISHO_RETRY_DELAY = _CONFIG.get("jisho", {}).get("retry_delay_seconds", 3)

KOTOBANK_URL = _CONFIG.get("kotobank", {}).get("base_url", "https://kotobank.jp/word/")
KOTOBANK_TIMEOUT = _CONFIG.get("kotobank", {}).get("timeout_seconds", 10)
KOTOBANK_MAX_RETRIES = _CONFIG.get("kotobank", {}).get("max_retries", 3)
KOTOBANK_RETRY_DELAY = _CONFIG.get("kotobank", {}).get("retry_delay_seconds", 3)

KOOHII_URL = _CONFIG.get("koohii", {}).get("base_url", "https://kanji.koohii.com/")
KOOHII_TIMEOUT = _CONFIG.get("koohii", {}).get("timeout_seconds", 10)
KOOHII_MAX_RETRIES = _CONFIG.get("koohii", {}).get("max_retries", 3)
KOOHII_RETRY_DELAY = _CONFIG.get("koohii", {}).get("retry_delay_seconds", 3)

# Cache settings
CACHE_ENABLED = _CONFIG.get("cache", {}).get("enabled", True)
CACHE_DIRECTORY = _CONFIG.get("cache", {}).get("directory", "storage/cache")
CACHE_METADATA_FORMAT = _CONFIG.get("cache", {}).get("metadata_format", "json")
CACHE_RETENTION_DAYS = _CONFIG.get("cache", {}).get("retention_days", 30)

# Logging settings
LOG_LEVEL = _CONFIG.get("logging", {}).get("level", "INFO")
LOG_CONSOLE_ENABLED = _CONFIG.get("logging", {}).get("console_enabled", True)
LOG_FILE_ENABLED = _CONFIG.get("logging", {}).get("file_enabled", True)
LOG_DIRECTORY = _CONFIG.get("logging", {}).get("log_directory", "storage/logs")

# GUI settings
GUI_WINDOW_WIDTH = _CONFIG.get("gui", {}).get("window_width", 1000)
GUI_WINDOW_HEIGHT = _CONFIG.get("gui", {}).get("window_height", 700)
GUI_DEFAULT_FONT_SIZE = _CONFIG.get("gui", {}).get("default_font_size", 11)

# Parser behavior
PARSER_FIXTURE_MODE = _CONFIG.get("parser", {}).get("fixture_mode", False)
PARSER_FIXTURES_DIRECTORY = (
    _CONFIG.get("parser", {}).get("fixtures_directory", "tests/fixtures")
)

# Expose config dict for advanced use cases
CONFIG = _CONFIG

# Log configuration loaded
_log = logging.getLogger(__name__)
_log.debug(f"Configuration loaded from {CONFIG_FILE}")
