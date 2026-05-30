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
- [ ] **Kotobank Parser**: Re-implement with strict error handling and logging.
- [ ] **Koohii Parser**: Modernize extraction logic and ensure compatibility with modern HTML structures.
 - [x] **Kotobank Parser**: Re-implement with strict error handling and logging.
  - ✓ Standalone service at `jpfm/parsers/kotobank_parser.py` with fixture-based tests.
 - [x] **Koohii Parser**: Modernize extraction logic and ensure compatibility with modern HTML structures.
  - ✓ Simplified MVP service at `jpfm/parsers/koohii_parser.py` with fixture-based tests.
- [ ] **Contract Testing**: Establish versioning strategy for legacy vs current fixtures.
- [ ] **Validation**: Ensure all parsers pass headless unit tests without making live network requests.

---

## **Milestone 03: Efficient Pipeline**
*Goal: Implement the caching layer to prevent redundant web requests.*

- [ ] **Storage Layer**: Implement logic to save and load metadata from the `storage/` directory.
- [ ] **Cache-Aware Logic**: Ensure the "Dictionary Manager" checks local storage before initiating web requests.
- [ ] **Metadata Versioning**: Establish a system to handle legacy vs. current data formats in the cache.

---

## **Milestone 04: GUI Development**
*Goal: Build the user interface using a hybrid MVP/MVC pattern with automated component tests.*

- [ ] **Main Application Window**: Create the primary PySide6 interface.
- [ ] **Component Tests**: Write unit tests for individual widgets (e.g., verifying "Search" button signals) using **`qtbot`**.
- [ ] **Results View**: Implement a custom `QAbstractItemModel` for dictionary data, validated by **`qtmodeltester`**.
- [ ] **Passive View Enforcement**: Ensure no business logic is hardcoded inside widget classes.

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