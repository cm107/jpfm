# Fixture-Based Testing Guide

This document defines the purpose and rules for implementing fixture-based tests. These tests are the primary defense against breaking changes in target webpage formats and are essential for a robust, headless development workflow.

## 1. Purpose of Fixture Tests

The goal of using fixtures is to achieve **Stability over Speed**.

*   **Webpage Format Protection**: By saving local copies of target webpages, we can run "Contract Testing" to ensure the parser correctly extracts fields like "Reading" and "Definition" even if the live site changes.
*   **Isolation**: Fixtures allow us to test the parsing logic and GUI without making live network requests, which makes tests faster, deterministic, and runnable in offline or CI/CD environments.
*   **Failure Pinpointing**: When a webpage format changes, these tests will immediately highlight the exact field that failed to parse (e.g., "Element ID 'reading-section' not found").
*   **Mocking the Pipeline**: Pre-defined responses from fixtures allow us to test how the GUI handles various scenarios, such as successful parses, network timeouts, or "format changed" errors.

## 2. Rules for Creating Fixture Tests

To maintain the standards of the `classifier_app` architecture, all fixture tests must follow these rules:

### **Storage and Organization**
*   **Pathing**: All HTML samples must be stored in the `tests/fixtures/` directory.
*   **Naming**: Fixtures should be named descriptively based on the source and word type (e.g., `jisho_verb_taberu.html`).

### **Execution Rules**
*   **No Live Requests**: Parser unit tests must strictly load local files from the `fixtures/` folder. They must **never** make live network requests during a test run.
*   **Mocking**: Use `unittest.mock` to feed these pre-defined fixture responses into the `DictionaryManager` or the GUI's Presenter layer.
*   **Error Handling**: Every parsing function must include comprehensive `try-except` blocks that log specific failures to help identify exactly what part of a webpage's HTML structure has changed.

### **Assertion and Logging**
*   **Contract Validation**: Tests must assert the presence and correctness of all expected data fields.
*   **Logging**: Follow the project’s logging convention to track the state of the processing pipeline. If a fixture test fails, the logs in `storage/` or `docs/` should provide a clear traceback of the divergence.

## 3. Integrated Tooling Fixtures

In addition to HTML data fixtures, the project utilizes standard `pytest-qt` fixtures for GUI validation:

*   **`qtbot`**: Used to simulate user interactions (clicking, typing) and to register widgets for proper teardown to prevent memory leaks.
*   **`qtmodeltester`**: Used to automatically validate the structural integrity of custom dictionary models (e.g., checking for off-by-one errors or row count mismatches).
*   **`qtlog`**: Used to intercept internal Qt messages (`qDebug`, `qWarning`) and fail tests if unexpected errors occur during rendering or layout.

## 4. Example Test Structure

A standard fixture test should follow this pattern:
1.  **Load**: Read the HTML string from a file in `tests/fixtures/`.
2.  **Parse**: Pass the string to the modular parsing function.
3.  **Assert**: Verify that the returned object contains the exact expected metadata.
4.  **Log**: Ensure any discrepancies are captured by the logging system.