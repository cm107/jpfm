# Milestone 04.02 Implementation Plan

## Goal

Deliver a robust word list workflow that covers history import progress, list editing, pruning, learned-word exclusion, metadata tracking, parsing orchestration, collision handling, and sorting.

## High-level architecture

The implementation should preserve the existing MVP/MVC hybrid:

- `HistoryImportService` handles history scanning, extraction, normalization, deduplication, and candidate metadata construction.
- `DictionaryManager` remains responsible for parsing, cache coordination, and content lookup.
- `MainWindow` stays passive and exposes controls only.
- `DictionaryPresenter` coordinates commands and updates the view.
- A new word list model or service can manage list state, metadata, and actions such as remove, prune, and sort.

## Tasks

### 1. History import progress

- Add progress signals to `HistoryImportService`:
  - `on_scan_progress(file_index, file_count)`
  - `on_extract_progress(entry_index, entry_count)`
  - `on_complete(final_count)`
- Create a progress UI element in `MainWindow`:
  - A determinate progress bar for file scanning and extraction phases
  - A simple status label for phase messages
- Update `DictionaryPresenter` to bridge service progress events to view updates.

### 2. Word removal and list editing

- Add a `QListWidget` context action or delete button for list entries.
- Keep removal in the presenter/service layer: the view emits `word_removed` and the presenter updates the word list model.
- Ensure deletion does not remove the underlying imported history evidence until the user confirms their new final list.

### 3. Pruning rules

- Add config entries for:
  - prohibited characters
  - prohibited substrings
  - allowed minimum / maximum word length
- Implement a prune pass in `HistoryImportService` or a new `WordListFilterService`.
- Keep pruning rules explicit, testable, and configurable.

### 4. Learned-word exclusion

- Create a new learned-word provider or loader service.
- Support loading a learned list from a file or config path.
- Filter generated candidates against the learned list during final word list assembly.
- Ensure the learned filter is optional and user-configurable.

### 5. Rich word metadata

- Extend word list items with metadata fields:
  - `source`
  - `origin_url`
  - `added_at`
  - `history_timestamps`
  - `hit_count`
  - `first_timestamp`
  - `last_timestamp`
  - `rule_id`
- Use a table model or custom list model to display metadata in the UI later.
- Store metadata in the list state so future parse decisions can reference it.

### 6. Parsing workflow and progress

- Add a `Start Parsing` button to `MainWindow`.
- Add presenter signals for parse start, progress, completion, and failure.
- Use a parse worker or task abstraction to avoid blocking the UI.
- Provide clear messages for words with no result or failed parse attempts.

### 7. Collision handling

- Create a collision resolution component in `DictionaryManager` or a dedicated selection service.
- Support exact-match and non-exact-match prioritization rules:
  - prefer common words
  - prefer lower JLPT / lower WaniKani levels
  - prefer first API result if no criteria match
- Expose fallback logging for cases where the rule is not decisive.

### 8. Sorting and ordering

- Add sort keys to the word list state:
  - `hit_count`
  - `first_timestamp`
  - `last_timestamp`
  - `is_common_word`
  - `jlpt_level`
  - `wanikani_level`
- Add view controls to choose sort order.
- Keep sort behavior stable and declarative in the presenter's model.

## Component responsibilities

### `HistoryImportService`

- Recursively scan supported history snapshot files
- Apply configured extraction rules
- Normalize and deduplicate candidates
- Emit progress and completion events
- Merge manual words and learned exclusion results
- Return a `WordListResult` containing words plus metadata

### `DictionaryPresenter`

- Handle UI commands for import, manual add, remove, prune, and parse
- Translate service progress events into view updates
- Maintain current word list state across import and manual edits
- Keep the view passive and free of processing logic

### `MainWindow`

- Expose controls and status displays
- Provide manual add, import history, remove word, parse start, and sort controls
- Offer a progress bar and status message area
- Emit strongly typed signals only

### New `WordListModel` or state manager

- Maintain list entries with metadata
- Support add, remove, prune, exclude learned, and sort operations
- Provide stable final word lists to the parser
- Allow tests to exercise list behavior without the UI

## Testing strategy

- Add fixture-based unit tests for import progress, rule matching, pruning, and learned exclusion.
- Add presenter tests for word remove, sort order, and parse start coordination.
- Add GUI tests for progress UI state, delete actions, and parse button behavior.
- Use local fixtures and no live browser history network requests.

## Exit criteria

Milestone 04.02 is complete when:

- The user can import history with visible progress
- Manual word list items can be deleted and audited
- Pruning and learned exclusion are applied before parsing
- Each word item retains source/timestamps/hit-count metadata
- A parse workflow exists with progress and a clear pass/fail outcome
- The word list can be sorted by metadata-driven criteria
- There is a clean separation between view, presenter, and service logic
