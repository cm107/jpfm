# Legacy: Search Result Match Resolution (jp_dict)

Summary
-------
This note summarizes how the legacy `jp_dict` project located and resolved matching search results (primarily for Jisho-derived results). It is a compact reference to the original code paths and heuristics to be ported or adapted.

Key implementation files
- `ref/jp_dict/jp_dict/old/tools/word_search/jisho_word_search_core.py` — scraping + result extraction and plumbing into `WordResultHandler`.
- `ref/jp_dict/jp_dict/old/lib/jisho/word_results.py` — `WordResult` and `WordResultHandler` with `find_matches()` logic.
- `ref/jp_dict/jp_dict/old/lib/history_parsing/word_match_filter.py` — post-match filtering and sorting rules (the canonical "default_filter").

How matching works (legacy)
- Parsing: the search-scraper extracts HTML blocks into `WordResult` objects containing three main parts: `jap_vocab` (writing, reading, other forms), `concept_labels` (is_common_word, jlpt_level, wanikani_level), and `vocab_entry` (definitions + other forms).
- Primary match detection (WordResultHandler.find_matches):
  - If either `jap_vocab.writing` or `jap_vocab.reading` equals the `search_word`, it is considered a match.
  - Otherwise, `vocab_entry.other_forms` (if present) are inspected: any `kanji_writing` or `kana_writing` that equals `search_word` is considered a match.

Post-match filtering and resolution (default_filter)
- `default_filter` composes a sequence of filters/sorts to reduce candidate sets:
  1. Keep only search cases where the number of matches == 1 (`filter_by_match_count` target=1).
  2. Sort by WaniKani level (ascending), placing non-WaniKani items second.
  3. Sort by JLPT level (descending), placing non-JLPT items second.
  4. Prefer `common` words first (`sort_by_common_words` → `common_first`).
  5. Optionally remove words already present in user-provided learned lists.

Design intent & takeaways
- The legacy system attempts to boil multiple candidates down to a single, high-confidence result by combining orthographic equality checks with heuristics based on metadata (WaniKani, JLPT, common).
- The ordering in `default_filter` encodes domain preferences: prefer low WaniKani (easier kanji), then higher JLPT (more likely general-use words), then common-word tags.
- The `WordResult` shape provides all information necessary to score candidates deterministically.

Risks and caveats
- Legacy code assumes exact equality of `writing` and `reading` fields with the `search_word`. That works for many cases but fails for partial/okurigana and normalization edge-cases.
- The filter reduces to single-match cases early; later heuristics only reorder already filtered items. For our resolver we should preserve candidate lists and score them (instead of discarding early) so we can explain fallbacks.

References
- `ref/jp_dict/jp_dict/old/tools/word_search/jisho_word_search_core.py`
- `ref/jp_dict/jp_dict/old/lib/jisho/word_results.py`
- `ref/jp_dict/jp_dict/old/lib/history_parsing/word_match_filter.py`
