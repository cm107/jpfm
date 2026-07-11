"""
Configuration loader for JPFM application.

This module loads and validates the central config.yaml file and exposes
configuration values as module-level constants for use across the application.
"""

import logging
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

# Path to config.yaml
CONFIG_FILE = Path(__file__).parent.parent / "config" / "config.yaml"
USER_CONFIG_DEFAULTS_FILE = Path(__file__).parent / "config" / "user_config_defaults.yaml"
STORAGE_CONFIG_ROOT = Path(__file__).parent.parent / "storage"


def _merge_config(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively merge two configuration dictionaries."""
    merged = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_config(merged[key], value)
        else:
            merged[key] = deepcopy(value)
    return merged


def _load_yaml_file(path: Path) -> Dict[str, Any]:
    """Load a YAML file into a dictionary if it exists."""
    if not path.exists():
        return {}

    with path.open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle) or {}

    if not isinstance(loaded, dict):
        return {}

    return loaded


def _iter_storage_override_files(storage_root: Optional[Path] = None) -> List[Path]:
    """Return candidate YAML override files stored under the storage directory."""
    root = storage_root or STORAGE_CONFIG_ROOT
    candidates = [
        root / "config" / "user_config.yaml",
        root / "config" / "user_config.yml",
        root / "user_config.yaml",
        root / "user_config.yml",
    ]
    return [path for path in candidates if path.exists()]


def _load_config(
    config_file: Optional[Path] = None,
    user_defaults_file: Optional[Path] = None,
    storage_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Load and merge the base config with user-configurable defaults and storage overrides.

    Returns:
        Dict: Parsed configuration dictionary.

    Raises:
        FileNotFoundError: If config.yaml does not exist.
        yaml.YAMLError: If config.yaml is malformed.
    """
    base_config_path = config_file or CONFIG_FILE
    if not base_config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {base_config_path}")

    config = _load_yaml_file(base_config_path)
    defaults = _load_yaml_file(user_defaults_file or USER_CONFIG_DEFAULTS_FILE)
    config = _merge_config(config, defaults)

    for override_path in _iter_storage_override_files(storage_root):
        config = _merge_config(config, _load_yaml_file(override_path))

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

# Browser history import configuration
HISTORY_IMPORT_CONFIG = _CONFIG.get("history_import", {})
HISTORY_IMPORT_SUPPORTED_FILENAMES = HISTORY_IMPORT_CONFIG.get(
    "supported_filenames", ["BrowserHistory.json", "History.json"]
)
HISTORY_IMPORT_EXTRACTION_RULES = HISTORY_IMPORT_CONFIG.get(
    "extraction_rules", []
)

# Expose config dict for advanced use cases
CONFIG = _CONFIG


def write_user_config(config_data: Dict[str, Any], storage_root: Optional[Path] = None) -> Path:
    """Persist user-configurable settings to a YAML override file in the storage tree."""
    root = storage_root or STORAGE_CONFIG_ROOT
    override_path = root / "config" / "user_config.yaml"
    override_path.parent.mkdir(parents=True, exist_ok=True)

    with override_path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(config_data or {}, handle, sort_keys=False)

    return override_path


def update_runtime_config(
    config_data: Dict[str, Any],
    storage_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """Persist user-configurable settings and update the in-memory runtime config."""
    write_user_config(config_data, storage_root=storage_root)

    global _CONFIG, CONFIG
    _CONFIG = _load_config(
        config_file=CONFIG_FILE,
        user_defaults_file=USER_CONFIG_DEFAULTS_FILE,
        storage_root=storage_root,
    )
    CONFIG.clear()
    CONFIG.update(_CONFIG)
    return CONFIG


# Log configuration loaded
_log = logging.getLogger(__name__)
_log.debug(f"Configuration loaded from {CONFIG_FILE}")
