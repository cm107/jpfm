# Browser History Logic Comparison

This document compares the legacy `ref/jp_dict` browser history parsing implementation with the planned architecture for Milestone 04.01.

## Legacy Implementation Summary

The legacy codebase uses a series of history utilities and history object wrappers to scan browser history directories, combine history snapshots, and collect Jisho search URLs.

### Key behaviors

- Recursively search directories for Chrome-style history exports named:
  - `BrowserHistory.json`
  - `History.json`
- Combine history files into a single ordered list by using `time_usec` as a de-dup key.
- Treat history entries as dictionaries containing `title`, `url`, `client_id`, `time_usec`, and optional page transition metadata.
- Provide high-level search helpers such as `search_by_url_base('https://jisho.org/search/')` and grouping by identical URLs.
- Extract Jisho search URLs using a hard-coded prefix matcher in `JishoSearchUrlUtil.is_valid()`.
- Build grouped entries in `HistoryUrlSectionGroup` by a derived key based on the first byte of the raw search term.
- Store matching history candidates as `HistoryUrl(url, [utctime])` pairs and sort entries by earliest timestamp.

### Implementation locations

- `ref/jp_dict/jp_dict/parsing/history_url.py`
- `ref/jp_dict/jp_dict/v3/history_util.py`
- `ref/jp_dict/jp_dict/v2/cli/core/history.py`
- `ref/jp_dict/jp_dict/parsing/browser_history.py`
- `ref/jp_dict/jp_dict/old/tools/history_parsing/history_test.py`

## What the legacy code does well

- Detects browser history snapshots recursively.
- Normalizes duplicate history entries by timestamp when combining multiple files.
- Offers a basic abstraction for URL grouping and lazy history entry grouping.
- Separates history path collection from history entry combination.

## Observed limitations

### 1. Hard-coded, single-provider extraction

- Extraction logic is tightly coupled to `https://jisho.org/search/`.
- The code is not built to support multiple search sites or future URL rule changes.

### 2. Weak candidate metadata

- Candidate objects only preserve the raw URL and timestamps.
- There is no explicit extraction rule or provider metadata attached to each candidate.
- No structured `word` field or normalized token is saved.

### 3. Inefficient de-dup and grouping logic

- Duplicate grouping uses list membership checks and nested loops.
- `HistoryUrlSectionGroup` dynamically creates groups keyed by raw URL bytes, which is opaque and brittle.
- Full JSON history files are loaded into memory, then reversed and iterated with pop operations.

### 4. Manual and external fetching fallback

- The old workflow includes a fallback that loads each matching Jisho URL and scrapes the HTML title to determine the search word.
- This is inefficient and unnecessary if the extraction rule can determine the word directly from the URL.

### 5. Limited JSON path support and normalization

- Only Chrome history exports are considered, with no support for alternate browser or export formats.
- URLs are accepted only by prefix; encoded query or path normalization is not robust.

## Improvement Plan for Milestone 04.01

The new design should prioritize efficiency, metadata clarity, and scalability.

### 1. Config-driven extraction rules

- Define a ruleset in `config/config.yaml` with named extraction rules.
- Support patterns such as:
  - `https://jisho.org/search/{query}`
  - other future provider templates
- Each rule should include:
  - `provider_name`
  - `matcher` (prefix or regex)
  - `extractor` (path segment or query param)
  - `normalizer`

### 2. Explicit candidate metadata model

Use a structured candidate type such as:

- `source_path`: file path to the history snapshot
- `browse_timestamp`: `time_usec`
- `browser_name`: derived from source or config
- `url`: original URL
- `rule_id`: extraction rule used
- `word`: extracted raw token
- `normalized_word`: normalized candidate word
- `title`: optional title metadata if available

This supports better auditing, UI filtering, and future export.

### 3. Streamlined scanning and extraction

- Recursively enumerate relevant files using a reusable helper.
- Use a generator-based pipeline to avoid loading entire history dumps at once.
- Filter entries early by supported URL patterns before decoding or parsing.
- Only decode URLs when a rule has matched.

### 4. Robust normalization and deduplication

- Normalize extracted words using a common function.
- Deduplicate candidates by normalized token and rule source.
- Preserve manual additions separately and merge them into the final list without overwriting them.

### 5. Better metadata organization

- Keep the browser history import service focused on candidate construction.
- Store history metadata and extraction metadata in separate fields.
- Allow the presenter/UI to display both imported history entries and manual overrides.

### 6. Increased scalability

- Support additional providers without changing core service logic.
- Use explicit extraction rule definitions instead of opaque grouping heuristics.
- Avoid expensive `time_usec` list membership checks by indexing or keying candidates.
- Enable incremental import by remembering processed history paths or file checksums in the future.

## Planned architecture changes

### Service boundaries

- `HistoryImportService` will:
  - discover candidate history files
  - parse entries through configured rules
  - normalize and dedupe extracted words
  - return a curated word list plus metadata

- `DictionaryManager` will remain responsible for parsing and cache orchestration.
- The GUI will consume a clean list of imported and manual words as the input source for parsing.

### Why this is better

- More efficient: avoids external fetching and reduces full-file memory churn.
- More scalable: new providers and rules can be added by config.
- More maintainable: extraction logic is explicit, testable, and decoupled from history data models.
- More transparent: candidates carry provenance metadata, enabling better UI and debugging.

## Example future state

Instead of `process(url, utctime)` and opaque grouping, the system can produce:

- `{'url': 'https://jisho.org/search/食べる', 'rule_id': 'jisho_search', 'word': '食べる', 'normalized_word': '食べる', 'source_path': '/.../BrowserHistory.json', 'time_usec': 1234567890}`

This makes the browser history pipeline both simpler and more adaptable than the legacy implementation.
