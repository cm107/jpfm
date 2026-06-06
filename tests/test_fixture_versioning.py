from pathlib import Path


test_root = Path(__file__).parent / "fixtures"


def test_fixture_sources_have_current_directory():
    """Each fixture source must expose a current/ directory."""
    assert test_root.exists(), "tests/fixtures directory is missing"

    sources = [p for p in test_root.iterdir() if p.is_dir()]
    assert sources, "No fixture source directories were found in tests/fixtures"

    for source_dir in sources:
        current_dir = source_dir / "current"
        assert current_dir.exists() and current_dir.is_dir(), (
            f"Fixture source '{source_dir.name}' must contain a current/ directory"
        )


def test_fixture_versioning_directories_are_consistent():
    """Fixture directories should use standard versioning naming conventions."""
    sources = [p for p in test_root.iterdir() if p.is_dir()]
    for source_dir in sources:
        legacy_dir = source_dir / "legacy"
        backup_dir = source_dir / "backup"
        if legacy_dir.exists() or backup_dir.exists():
            assert legacy_dir.exists(), (
                f"Fixture source '{source_dir.name}' should use legacy/ instead of backup/"
            )
