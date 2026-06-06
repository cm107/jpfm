# Working Progress: JPFM

This document tracks the milestones and task completion for the Japanese Dictionary Parser and Flashcard Creator. Our goal is to transition the legacy `jp_dict` logic into a decoupled, test-driven PySide6 application.

## **Milestone 01: Foundation** (Completed)
*Goal: Establish the repository structure, technical rules, and automated environment.*

- [x] Initial repository setup following the `classifier_app` layout.
- [x] Create `.github/` rules, including **Copilot instructions** and **Issue/PR templates**.
- [x] Configure `setup.py` with `dev` extras for **PySide6** and **pytest-qt**.
- [x] Set up **GitHub Actions** for headless GUI testing using `tests.yml`.
- [x] Implement a comprehensive **logging system** to track pipeline state.
- [x] Define central `config.yaml` for application settings.

---

## **Milestone 02: Core Parser** (Jisho Parser: Complete)
*Goal: Re-implement legacy extraction logic with 100% test coverage using local HTML fixtures.*

- [x] **Jisho Parser**: Refactored legacy logic into standalone service class (`jpfm/parsers/jisho_parser.py`).
  - ✓ Modular architecture with zero GUI dependencies.
  - ✓ Strict type hints and Google-style docstrings.
  - ✓ Comprehensive logging for state tracking and error diagnosis.
  - ✓ Extracts Reading, Kanji, and Definitions (simplified MVP, deferred complex features).
  - ✓ 28 unit tests, all passing; 100% fixture-based (no live requests during CI).
  - ✓ Test coverage: initialization, parsing, error handling, logging, integration, edge cases.
- [x] **Kotobank Parser**: Re-implement with strict error handling and logging.
  - ✓ Standalone service at `jpfm/parsers/kotobank_parser.py` with fixture-based tests.
- [x] **Koohii Parser**: Modernize extraction logic and ensure compatibility with modern HTML structures.
  - ✓ Simplified MVP service at `jpfm/parsers/koohii_parser.py` with fixture-based tests.
- [x] **Contract Testing**: Establish versioning strategy for legacy vs current fixtures.
- [x] **Validation**: Ensure all parsers pass headless unit tests without making live network requests.

---

## **Milestone 03: Efficient Pipeline**
*Goal: Implement the caching layer to prevent redundant web requests.*

- [x] **Storage Layer** (Phase 1): Implemented cache persistence and versioning.
  - ✓ `jpfm/storage/storage_service.py` with `StorageService` class.
  - ✓ Methods: `save(source, word, parsed_data)`, `load(source, word)`, `exists(source, word)`, `list_cached_words(source)`, `clear_cache(source=None)`.
  - ✓ JSON persistence to `storage/cache/{source}/{word}.json` with metadata (_version, _source, _cached_at).
  - ✓ 24 comprehensive unit tests in `tests/storage/test_storage_service.py`, all passing.
  - ✓ Version validation: stale entries are treated as cache misses.
- [x] **Cache-Aware Logic** (Phase 2): Implemented Dictionary Manager orchestrator.
  - ✓ `jpfm/services/dictionary_manager.py` with `DictionaryManager` class.
  - ✓ Parser factories (JishoParserFactory, KotobankParserFactory, KoohiiParserFactory) for fetch/parse coordination.
  - ✓ Methods: `get_entry(source, word)`, `batch_get_entries(source, words)`, `clear_cache(source=None)`, `list_cached_words(source)`, `get_cache_stats()`.
  - ✓ Cache-first pattern: checks storage before web requests.
  - ✓ 30 comprehensive integration tests in `tests/services/test_dictionary_manager.py`, all passing.
  - ✓ Proper logging of cache hits/misses and fetch errors.
- [x] **Metadata Versioning** (Phase 3): Establish schema compatibility and migration.

---

## **Milestone 04: GUI Development**
*Goal: Build the user interface using a hybrid MVP/MVC pattern with automated component tests.*

- [x] **Main Application Window**: Create the primary PySide6 interface.
- [x] **Component Tests**: Write unit tests for individual widgets (e.g., verifying "Search" button signals) using **`qtbot`**.
- [x] **Results View**: Implement a custom `QAbstractItemModel` for dictionary data, validated by **`qtmodeltester`**.
- [x] **Passive View Enforcement**: Ensure no business logic is hardcoded inside widget classes.

---
## **Milestone 04.01: Browser History Word List** (Pending)
*Goal: Implement browser history import and manual word list construction, with GUI-configurable extraction rules.*

- [x] Draft browser history import design and extraction-rule contract in `docs/browser_history_import.md`.
- [x] Add configuration defaults for supported history filenames and extraction patterns.
- [x] Define a `HistoryImportService` as the service entry point for recursive snapshot scanning and candidate extraction.
- [x] Support manual word addition and merge imported candidates with user-entered terms.
- [x] Normalize and deduplicate the generated word list before it enters the parsing pipeline.
- [x] Create unit tests for import logic, normalization, rule matching, and manual list behavior.
- [x] Add UI controls for history import and manual word entry.
- [x] Wire the workflow into the GUI presenter with passive view controls for import and manual input.
- [x] Add presenter unit tests for history import workflow.

---
## **Milestone 04.02: Word List Management & Import Visibility** (Pending)
*Goal: Add list editing, pruning, learned-word exclusion, metadata, parsing orchestration, and sort capabilities before Anki export.*

- [ ] Add a progress bar or progress feedback for browser history import.
- [ ] Add the ability to remove words from the word list.
- [ ] Add configurable pruning rules for prohibited characters and strings.
- [ ] Add support for excluding already-learned words.
- [ ] Add word metadata tracking: source, timestamps, hit count, and added time.
- [ ] Add a `Start Parsing` workflow with progress and failure handling.
- [ ] Add collision resolution and fallback prioritization rules for parsing.
- [ ] Add word list sorting by metadata and parse-derived criteria.

---
## **Milestone 05: Anki Integration**
*Goal: Port AnkiConnect functionality into a decoupled GUI service.*

- [ ] **Anki Service**: Port and refactor Anki logic from the original `jp_dict`.
- [ ] **Signal Integration**: Connect the GUI to the Anki service via strongly typed signals.
- [ ] **Export Validation**: Create mock tests for the Anki export workflow.

---

## **Milestone 06: Finalization**
*Goal: End-to-end validation and project cleanup.*

- [ ] **Integration Testing**: Simulate the full workflow (Input → Parse → Cache → Export) in a headless environment.
- [ ] **Documentation**: Finalize the `docs/` directory with parsing contracts and GUI architecture details.
- [ ] **Code Cleanup**: Remove any remaining dependencies on the `ref/` directory and perform final linting.
