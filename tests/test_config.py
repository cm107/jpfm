from pathlib import Path

import yaml

from jpfm.config import _load_config, write_user_config


def test_load_config_merges_user_defaults_and_storage_overrides(tmp_path: Path) -> None:
    base_config = tmp_path / "config.yaml"
    base_config.write_text(
        "history_import:\n"
        "  supported_filenames:\n"
        "    - BrowserHistory.json\n"
        "  extraction_rules: []\n",
        encoding="utf-8",
    )

    user_defaults = tmp_path / "user_config_defaults.yaml"
    user_defaults.write_text(
        "history_import:\n"
        "  pruning_rules:\n"
        "    - type: prohibited_characters\n"
        "      value: '*'\n"
        "  learned_words:\n"
        "    - 食べる\n",
        encoding="utf-8",
    )

    storage_root = tmp_path / "storage"
    override_dir = storage_root / "config"
    override_dir.mkdir(parents=True)
    override_file = override_dir / "user_config.yaml"
    override_file.write_text(
        "history_import:\n"
        "  learned_words:\n"
        "    - 動く\n",
        encoding="utf-8",
    )

    config = _load_config(
        config_file=base_config,
        user_defaults_file=user_defaults,
        storage_root=storage_root,
    )

    history_import_config = config["history_import"]
    assert history_import_config["supported_filenames"] == ["BrowserHistory.json"]
    assert history_import_config["pruning_rules"][0]["value"] == "*"
    assert history_import_config["learned_words"] == ["動く"]


def test_write_user_config_persists_to_storage_override_file(tmp_path: Path) -> None:
    storage_root = tmp_path / "storage"
    storage_root.mkdir()

    config_data = {
        "history_import": {
            "pruning_rules": [{"type": "prohibited_characters", "value": "*"}],
            "learned_words": ["食べる"],
        }
    }

    override_path = write_user_config(config_data, storage_root=storage_root)

    assert override_path.exists()
    loaded = yaml.safe_load(override_path.read_text(encoding="utf-8"))
    assert loaded["history_import"]["pruning_rules"][0]["value"] == "*"
    assert loaded["history_import"]["learned_words"] == ["食べる"]
