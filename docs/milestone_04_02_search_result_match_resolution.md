# Milestone 04.02 — Search Result Match Resolution

TL;DR
-----
Implement a deterministic resolver that consolidates parser search results into one canonical match per query, using scored heuristics informed by legacy `jp_dict` rules (WaniKani, JLPT, common tags) while preferring cached metadata and providing a logged resolution trace for debugging and UI display.

Why
---
- Current behavior can choose the first API result blindly, causing incorrect parses and cache pollution.
- The legacy `jp_dict` resolves matches using a series of filters and sorts; we should adapt those priorities into a score-based resolver that is testable and explainable.

Legacy mapping (key takeaways)
---------------------------------
- Exact-match rules: legacy `WordResultHandler.find_matches` treats `jap_vocab.writing` or `jap_vocab.reading` equality with `search_word` as matches; `vocab_entry.other_forms` are also checked.
- Legacy `default_filter` pipeline prefers (in order): single-match results → WaniKani ascending → JLPT descending → common words first → exclude learned words.

Goals
-----
- Preserve exact-match behavior for high-confidence cases.
- Score multiple candidates deterministically using: orthographic match, `confidence_hint`, cached metadata bonus, `is_common_word`, `jlpt_level`, `wanikani_level`, and source priority.
- Expose a `trace` for why a candidate was chosen.
- Add unit and integration tests using existing fixtures.

Strict acceptance policy
-----------------------
- Resolver MUST only *accept* candidates that are exact orthographic matches to the `search_word`. An accepted candidate is one where any of the following is true:
  - `candidate.writing == search_word`
  - `candidate.reading == search_word`
  - any `candidate.other_forms` writing or reading equals `search_word`
- If no exact-match candidate exists (and no exact cached entry exists for `search_word`), the resolver returns `None` and the manager should treat the query as "no acceptable match" (do not forgive non-exact matches). Scoring may still be computed and recorded for diagnostics, ranking, or UI explanation, but it must not be used to accept a non-exact candidate.

High-level design
------------------
- New model: `DictionaryMatch` (fields: `source`, `source_id`, `writing`, `reading`, `other_forms`, `concept_labels`, `vocab_entry_snippet`, `confidence_hint`, `cached`, `score`, `trace`).
- New service: `DictionaryMatchResolver.resolve(search_word, candidates) -> DictionaryMatch`.
  - Normalization pass: canonicalize candidate `writing`/`reading` (strip spaces, full-width/half-width normalization if needed).
  - Base score: use `confidence_hint` if provided else 0.5.
  - Orthographic boosts: exact `writing` match +0.35, exact `reading` match +0.25, other form match +0.15.
  - Metadata boosts/penalties: `cached` +`CACHE_BONUS`, `is_common_word` +0.10, `jlpt` lower numeric (N5=5?) — normalized to score contribution, `wanikani` lower level => small boost (legacy preferred ascending).
  - Source priority tie-break (configurable list) used after scoring.
  - Record every rule application in `trace` for transparency.
  - IMPORTANT: perform an exact-match filter step before accepting a candidate; if no exact-match candidates exist, the resolver returns `None` even if a candidate has a high aggregate score.

Implementation steps
--------------------
1. Add `DictionaryMatch` dataclass in `jpfm/models/`.
2. Implement `DictionaryMatchResolver` in `jpfm/services/` with a pure `resolve()` method and small helper functions for scoring and normalization.
3. Update `jpfm/parsers/*_parser.py` adapters to emit a list of normalized candidate dicts (or `DictionaryMatch` prototypes) instead of a single best guess.
4. Update `jpfm/services/dictionary_manager.py` to:
   - Collect candidates from configured sources.
   - Call `DictionaryMatchResolver.resolve()`.
   - Persist the chosen result to cache via `StorageService.save()` (only replace if incoming score > stored_score + epsilon).
5. Add unit tests for `DictionaryMatchResolver` (edge cases: no candidates, exact-reading vs okurigana, conflicting metadata) using fixtures in `tests/fixtures/*`.
6. Add integration tests in `tests/services/test_dictionary_manager.py` that verify end-to-end behavior: cache preferred; resolver chooses expected candidate.
7. Update `entry_table_model` / presenter to display resolution `score` and provide a 'view trace' action (UI change later, minimal model support now).

Files to modify
---------------
- `jpfm/models/word_list_item.py` (extend or add `DictionaryMatch` in `jpfm/models/`)
- `jpfm/services/dictionary_manager.py` (integration with resolver)
- `jpfm/services/dictionary_match_resolver.py` (new file)
- `jpfm/parsers/jisho_parser.py`, `jpfm/parsers/koohii_parser.py`, `jpfm/parsers/kotobank_parser.py` (emit normalized candidates)
- `jpfm/storage/storage_service.py` (persist score/metadata; read existing schema safely)
- `jpfm/ui/entry_table_model.py`, `jpfm/ui/presenter.py` (display score/trace)
- Tests: `tests/services/test_dictionary_manager.py`, `tests/services/test_match_resolver.py`, `tests/parsers/*` fixtures

Verification
------------
- Unit: `tests/services/test_match_resolver.py` — scoring rules produce deterministic ordering.
- Integration: `tests/services/test_dictionary_manager.py` — resolve then persist; cached candidate preferred on subsequent queries.
- Regression: run full `pytest -q` and ensure existing tests pass.

Decisions & defaults
--------------------
- `CACHE_BONUS = 0.25` (configurable via `jpfm/config.py`).
- `BASE_CONFIDENCE = 0.5` when source hint missing.
- Orthographic boosts tuned to reflect legacy priority (writing > reading > other_form).
- Normalization: preserve kana/kanji characters; only trim whitespace and normalize common punctuation. More aggressive normalization deferred until needed.

Acceptance criteria
-------------------
- Resolver implemented with unit tests covering core rules.
- `DictionaryManager` integrates resolver and uses the resolver-chosen candidate for caching.
- New tests and existing tests all pass.
- Logs include a human-readable trace for each resolution.

Next steps
----------
1. Review this plan.
2. If approved, I'll implement `DictionaryMatch` + `DictionaryMatchResolver` and add unit tests.
