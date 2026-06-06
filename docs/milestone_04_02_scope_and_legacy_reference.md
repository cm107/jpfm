# Milestone 04.02: Word List Management and Browser History Enhancements

## Purpose

This document captures the remaining work needed before moving to Milestone 05, and it records how the legacy `jp_dict` repository implemented similar behavior.

Milestone 04.02 extends the existing browser history word list feature by adding user-visible progress, list management, pruning, learned-word exclusion, metadata tracking, parsing orchestration, collision handling, and sort behavior.

## 04.02 Feature Scope

The following features are in scope for Milestone 04.02:

- History import progress feedback for the user
- Manual removal of word list entries
- Configurable pruning of invalid or undesired words
- Exclusion of already-learned words
- Detailed metadata tracking for each word list item
- A `Start Parsing` workflow and progress reporting
- Search result collision handling and fallback rules
- Sortable word list by metadata and parsed fields

## Legacy `jp_dict` Implementation Notes

The legacy repository already contains several implementation patterns that inform this work.

### 1. Browser history discovery and combining

Key files:
- `ref/jp_dict/jp_dict/v2/cli/core/history.py`
- `ref/jp_dict/jp_dict/parsing/history_url.py`

Legacy behavior:
- Recursively locate history export files using `BrowserHistory.json` and `History.json`
- Combine history snapshots with de-duplication keyed by `time_usec`
- Sort combined entries by timestamp before processing
- Use `tqdm` for CLI progress reporting while combining

### 2. URL extraction and hit counting

Key files:
- `ref/jp_dict/jp_dict/parsing/history_url.py`

Legacy behavior:
- Match history URLs with hard-coded Jisho prefix logic
- Group matching URLs into `HistoryUrlSectionGroup`
- Track repeated URLs and their timestamps in `HistoryUrl`
- Compute hits by bundling multiple timestamps for the same search URL

### 3. Progress bar / user feedback patterns

Key files:
- `ref/jp_dict/jp_dict/v2/cli/core/history.py`
- `ref/jp_dict/test/old/parse_jisho_history.py`
- `ref/jp_dict/test/old/test_parse_nippon_daihyakka_zensho.py`

Legacy behavior:
- Use `tqdm` in long-running loops for history combination and parse workflows
- Save progress state to files such as `progress.pth`
- Support optional progress display via `show_pbar` and `leave` flags

### 4. Learned-word filtering and pruning

Key files:
- `ref/jp_dict/jp_dict/old/test/tagged_cache_filter_test.py`

Legacy behavior:
- Implement multiple filters for word metadata, including wildcard tags, English character tags, typo/tag filters, and garbage characters
- Filter by `learned_list` using `TaggedCacheFilter.filter_by_learned`
- Filter by hit count, timestamps, JLPT level, WaniKani level, and common-word status

### 5. Sorting and metadata-aware ordering

Key files:
- `ref/jp_dict/test/sort_testing/basic_test.py`

Legacy behavior:
- Sort candidate results by fields such as `search_word_hit_count`, `first_search_localtime`, and `last_search_localtime`
- Support `recommended_sort()` and then filter out export lists
- Use parse metadata to influence order before export

## What the legacy design gets right

- History import is treated as a separate preprocessing step
- Hit counts and timestamps are preserved for candidate prioritization
- CLI progress reporting is present for long operations
- Learned-word filtering is a first-class concept
- Sorting is based on both search metadata and parse metadata

## Legacy limitations to improve

### Hard-coded extraction rules
- Legacy code is tightly coupled to Jisho search URLs; it is not configurable or provider-agnostic.

### Weak candidate metadata
- Candidates often only carry raw URL and timestamps, not normalized words, origin metadata, or extraction rule provenance.

### Inefficient grouping and deduplication
- `HistoryUrlSectionGroup` uses opaque grouping keys and iterative list searches.

### CLI-first progress reporting
- Progress is implemented with `tqdm`, not a GUI-friendly task model.

### Limited list-editing support
- There is no native support for removing words from an interactive list or editing word metadata in the view.

## Recommended improvements for 04.02

### Use structured import metadata
A word list item should include:
- `word`
- `normalized_word`
- `source` (`browser_history` or `manual`)
- `origin_url` or provider metadata
- `history_timestamps`
- `hit_count`
- `added_at`
- `first_timestamp` / `last_timestamp`
- `rule_id` or extraction rule reference

### Replace hard-coded URL matching with config-driven rules
- Define extraction patterns in `config/config.yaml`
- Support providers and URL templates via named rules
- Make rules editable in the GUI later

### Build a service-backed word list model
- Use a dedicated model/service for word list state
- Maintain manual and imported lists separately until merge
- Deduplicate normalized words at merge time

### Add GUI progress events and keep the view passive
- Emit progress signals from `HistoryImportService`
- Update the view with a progress bar or status message
- Keep parsing and history scanning in presenter/service code

### Use explicit prune filters instead of implicit heuristics
- Accept a list of prohibited characters and prohibited substrings
- Apply filters as a validation pass before parsing
- Keep filter definitions in config and/or user settings

### Support learned-word exclusion as a service
- Load a learned-word list through a new service or file interface
- Filter imported/manual words against that set
- Keep exclusion logic separate from the history extraction pipeline

### Make sort behavior metadata-driven
- Allow in-memory sort by hit count, timestamps, common-word status, JLPT, WaniKani, or parse result completeness
- Use a model that supports sort keys and stable order

## Reference summary

- `ref/jp_dict/jp_dict/v2/cli/core/history.py` — recursive file discovery, history combine, CLI progress
- `ref/jp_dict/jp_dict/parsing/history_url.py` — URL matching, grouping, hit counting
- `ref/jp_dict/jp_dict/old/test/tagged_cache_filter_test.py` — learned filtering and metadata filters
- `ref/jp_dict/test/sort_testing/basic_test.py` — parse result sorting and export filtering
- `ref/jp_dict/test/old/parse_jisho_history.py` — incremental parse progress and deduplication

This legacy reference is intended as a source of architectural inspiration, not a straight port. The new implementation should preserve the high-level outcomes while improving configurability, metadata clarity, and GUI-oriented separation of concerns.
