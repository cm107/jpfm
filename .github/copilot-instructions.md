# GitHub Copilot Instructions: Japanese Dictionary & Flashcard App

## 1. Core Project Philosophy
*   **Goal**: Rebuild `jp_dict` as a robust PySide6 GUI application with an efficient, cache-aware processing pipeline.
*   **Priority**: **Stability over speed**. The parsing logic must be modular and heavily validated against local HTML fixtures to prevent breaks due to external webpage changes.
*   **Efficiency**: Never recalculate metadata if a cached version exists in the `storage/` directory.

## 2. Directory & Architectural Rules
*   **Root Layout**: Strictly adhere to this structure: `app/` (logic), `config/` (settings), `storage/` (cache), `tests/` (validation), `docs/` (documentation), and `scripts/` (utilities).
*   **Configuration**: All constants, URLs, and GUI parameters must reside in `config.yaml`. **No hard-coded strings or magic numbers** in the source code.
*   **Separation of Concerns**: Use a **Model-View-Presenter (MVP)** or **Model-View-Controller (MVC)** hybrid pattern.
    *   Business logic (parsing, Anki creation) must reside in standalone service classes, **never** inside a PySide6 Widget class.
    *   The View must be passive, communicating with logic layers via **strongly typed signals**.

## 3. PySide6 & GUI Testing Standards
*   **Framework**: Use **PySide6** for all UI components.
*   **Automated Testing**: Every new GUI component must include a corresponding test in `tests/` using **`pytest-qt`**.
*   **Headless Validation**: Ensure all UI logic can be tested programmatically without a physical display. 
*   **Interaction Rules**:
    *   **Prefer native API methods** (e.g., `QLineEdit.setText()`) over raw event simulation (e.g., `qtbot.mouseClick`) for faster, more reliable tests.
    *   Always register widgets with `qtbot.addWidget(widget)` to ensure proper teardown and prevent window leaks.
    *   Use `qtbot.waitSignal` to handle asynchronous tasks like parsing results or network mock responses.

## 4. Robust Parsing & Data Rules
*   **Fixture-Based Testing**: For the parser, suggest tests that load local HTML files from `tests/fixtures/` rather than making live network requests.
*   **Error Handling**: Every parsing function must include comprehensive `try-except` blocks that log specific failures (e.g., `"Element ID 'reading-section' not found"`) to help pinpoint webpage format changes.
*   **Logging**: Implement a logging system across all modules to track the processing pipeline's state, following the `classifier_app` convention.

## 5. Python Coding Conventions
*   **Typing**: Require **strict type hinting** for all function signatures.
*   **Documentation**: Use **Google-style or NumPy-style docstrings** for every class and method.
*   **Logic Reuse**: When porting logic from the original `jp_dict`, refactor it into standalone services that the GUI interacts with via signals.

## 6. Implementation Snippet Guidelines
*   *“When creating a new processing task, always check `storage/cache/` for existing metadata before initiating a WebRequest. If data is found, load it and log 'Using cached metadata for [word]'.”*
*   *“When writing GUI tests, use `qtmodeltester` to validate any custom `QAbstractItemModel` implementations to catch indexing or row-count errors automatically.”*

## 7. Reference Directory (Read-Only)
*   **Path**: `ref/jp_dict/`
*   **Rule**: The `ref/` directory is strictly for **reference and legacy logic analysis**. 
*   **No Modifications**: Never suggest modifications, deletions, or new files within the `ref/` directory.
*   **Modernization Policy**: When reimplementing features from `ref/jp_dict`, do not copy code directly. All legacy logic must be refactored into modular, standalone services within the `jpfm/` directory that communicate with the GUI via signals.
*   **Architecture Shift**: Legacy CLI-based logic must be adapted to fit the **MVP/MVC hybrid pattern** and the **cache-aware processing pipeline** defined for this project.

## 8. Virtual Environment & Dependency Management
*   **Virtual Environment**: Always activate the project's virtual environment, located at `venv/`, before running any scripts or tests to ensure dependencies are correctly isolated. Never suggest creating a new virtual environment anywhere else.
*   **Dependency Installation**: Use `pip install -e .[dev]` to install the project in editable mode with development dependencies, including PySide6 and pytest-qt. Avoid suggesting direct `pip install` commands for individual packages outside of this context.
*   **Adding New Dependencies**: If a new dependency is required, it must be added to the `install_requires` list in `setup.py` and included in the `dev` extras if it's only needed for development or testing. Always ensure that any new dependencies are compatible with Python 3.7 or higher, as specified in the project requirements. We do not maintain dependency lists in separate `requirements.txt` files; all dependencies must be managed through `setup.py` to maintain a single source of truth.
