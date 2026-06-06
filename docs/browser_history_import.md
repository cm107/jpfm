# Browser History Import and Configurable Extraction Rules

This document defines the browser history import workflow for Milestone 04.01. The goal is to build a word list from browser history snapshots and support manual additions, while keeping extraction logic configurable and testable.

## Purpose

The browser history import feature is intended to create a source-of-truth word list for parsing jobs. It is not a parser itself; instead, it provides candidate search words derived from user browsing activity and manual entries.

## Supported Source Layout

The import workflow should support common Chrome history snapshot layouts, including:

- `Chrome/BrowserHistory.json`
- `Chrome/History.json`

It should recursively scan nested snapshot folders and collect history files from dated exports or snapshot directories.

## Configurable URL Extraction Rules

The feature must support configurable URL extraction rules so the UI can adapt to different search sites or future changes.

### Default Rule

The default extraction rule should match URLs in the form:

- `https://jisho.org/search/{word}`

### Rule Requirements

- Allow users to add or edit rules from the GUI.
- Use extraction patterns that are simple to understand and test.
- Normalize extracted words after rule application.
- Support a list of rules, not just a single hard-coded pattern.

## Word List Behavior

The imported word list must:

- deduplicate entries across imported history and manual input
- normalize whitespace and common punctuation
- preserve manually added words even if browser history does not include them
- exclude empty or malformed values

## Import Workflow

1. The user selects a browser history snapshot root folder.
2. The app scans the folder recursively for supported history JSON files.
3. Each JSON history entry is checked against configured extraction rules.
4. Candidate words are extracted, normalized, and deduplicated.
5. Manual words are merged into the final list.
6. The resulting list is presented in the UI for verification before parsing.

## Expected Integration Points

- `jpfm/services/history_import_service.py` should encapsulate the scanning, extraction, and normalization logic.
- `jpfm/config.py` and `config/config.yaml` should define default extraction rules and supported snapshot filenames.
- `jpfm/ui/main_window.py` should expose controls for importing history and manually adding words.
- `jpfm/ui/presenter.py` should coordinate import actions and update the view.

## Testing Strategy

Use fixture-based tests to verify:

- recursive scanning of nested snapshot directories
- detection of supported history JSON filenames
- correct extraction of words from Jisho search URLs
- normalization and deduplication behavior
- manual word preservation
- malformed or unsupported URLs do not produce valid entries

The service should be fully testable without launching the GUI.
