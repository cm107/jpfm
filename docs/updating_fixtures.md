# Fixture Maintenance and Update Policy

To maintain the **"Stability over Speed"** priority of this project, we must follow a disciplined approach to updating and retaining test fixtures. Because the application relies on a **cache-aware processing pipeline**, our fixtures must validate both current and legacy data formats to prevent regressions.

## 1. When to Update Fixtures
Fixtures are not static; they must be updated or supplemented in the following scenarios:

*   **Contract Test Failures**: When a unit test fails with a "format changed" error or a specific logger message (e.g., `"Element ID 'reading-section' not found"`), it is a primary signal that the live webpage structure has diverged from our saved fixture.
*   **Site Redesigns**: If the target dictionary website undergoes a visual or structural overhaul, a new set of fixtures must be captured immediately to ensure the extraction logic is updated for the new "contract".
*   **Feature Expansion**: If a new field is being added to our extraction requirements (e.g., adding "Pitch Accent" data), existing fixtures should be updated or new ones added to verify the parser can handle this new data point across different word types.

## 2. Maintaining Old vs. New Fixtures
When a webpage format changes, do not simply overwrite the old fixture. Instead, follow these organization rules:

*   **Versioning by Directory**: Organize fixtures into `current/` and `legacy/` subdirectories within `tests/fixtures/`.
    *   `tests/fixtures/jisho/current/verb_taberu.html`
    *   `tests/fixtures/jisho/legacy_2023/verb_taberu.html`
*   **Descriptive Naming**: Ensure names include the source, word type, and, if necessary, a version or date marker to distinguish between format iterations.

## 3. The Retention Debate: Keep or Delete?
The decision to keep obsolete fixtures depends on the state of the **`storage/`** directory and the requirements of the processing pipeline.

### **When to Keep Old Fixtures (Backward Compatibility)**
You should keep old fixtures to ensure **backward compatibility** as long as data parsed with that format still exists in user caches.
*   **Cache Integrity**: Since the app uses the `storage/` directory to maintain the local state of previously parsed words, the parser must be able to "understand" old metadata to prevent unnecessary recalculations or crashes when loading cached files.
*   **Regression Testing**: Keeping old fixtures allows you to run "Legacy Support" tests. This ensures that an update to the parser to support a *new* site format does not accidentally break the logic required to read *old* cached entries.

### **When to Delete Old Fixtures (Eliminating Clutter)**
You should only delete fixtures to **reduce clutter** when a format is truly orphaned:
*   **Mandatory Migrations**: If the project implements a script to migrate all old cached data in `storage/` to a new unified format, the old fixtures associated with the pre-migration format become unnecessary.
*   **Official Deprecation**: Once the application no longer supports loading data from a specific legacy version of the target site, the associated fixtures and tests can be removed to streamline the `tests/` directory.

## 4. Maintenance Workflow
1.  **Detect**: A test failure highlights that the live site has changed.
2.  **Archive**: Move the now-outdated fixture from `current/` to a `legacy_[date]/` folder.
3.  **Capture**: Save a new HTML sample of the redesigned site into the `current/` folder.
4.  **Implement**: Update the parsing logic to handle the new format while maintaining the `try-except` blocks for the archived format.
5.  **Validate**: Run the full suite. A successful run proves the app can handle the new site *and* still process old cached data from `storage/`.