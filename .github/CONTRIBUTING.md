# Contributing Guidelines

Thank you for your interest in contributing! This project aims to transition from a CLI-based tool to a robust PySide6 GUI application with an efficient, cache-aware processing pipeline. To ensure stability and eliminate "user-in-the-loop" development, all contributors must adhere to the following standards.

## 1. Development Environment Setup

This project requires **Python 3.7+** and utilizes **PySide6** as the primary Qt binding.

### **Installation**
To provision your development environment, clone the repository and perform an editable install with development extras:
```bash
# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # Or venv\Scripts\activate on Windows

# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Install pre-commit hooks for code style consistency
pre-commit install
```

### **Binding Resolution**
To avoid auto-detection variances, you should force the **PySide6** binding by setting the following environment variable:
*   **Linux/macOS**: `export PYTEST_QT_API=pyside6`
*   **Windows**: `set PYTEST_QT_API=pyside6`

## 2. Architectural Standards

We follow a **hybrid MVP/MVC pattern** to ensure the core logic remains testable in isolation.

*   **Separation of Concerns**: Business logic (web parsing, Anki creation) must reside in standalone service classes and **never** inside a PySide6 Widget class.
*   **Passive Views**: View components (Widgets/Windows) should be "dumb." They should only emit **strongly typed signals** and provide methods for the Presenter to update their state.
*   **Configuration**: All constants, URLs, and GUI parameters must reside in `config.yaml`. No hard-coded strings are permitted in the source code.

## 3. Coding Standards

*   **Typing**: All function signatures must include **strict type hinting**.
*   **Documentation**: Use **Google-style or NumPy-style docstrings** for every class and method.
*   **Logging**: Use the project's comprehensive logging system to track application flow, state transitions, and errors.
*   **Efficiency**: Always check the `storage/` directory for cached metadata before initiating a new web request to prevent unnecessary recalculations.

## 4. Testing Requirements

Every new feature or bug fix must be accompanied by automated tests in the `tests/` directory.

### **GUI Testing with `pytest-qt`**
*   **Registration**: All widgets must be registered with `qtbot.addWidget(widget)` to ensure proper teardown and prevent window leaks.
*   **Native API Preference**: For functional validation, prefer calling native widget methods (e.g., `setText()`, `setCurrentIndex()`) over raw hardware event simulation (e.g., `mouseClick()`) to ensure reliable and deterministic test execution.
*   **Headless Execution**: Tests must be runnable in a headless CI/CD environment. Set `export QT_QPA_PLATFORM=offscreen` before running `pytest` to validate headless compatibility.

### **Parsing & Fixture Tests**
*   **Contract Stability**: Parsing logic must be validated against local HTML samples stored in `tests/fixtures/`.
*   **No Live Requests**: Parser unit tests must **never** make live network requests; use `unittest.mock` to feed fixture data into the processing pipeline.

## 5. Debugging & Diagnostics

*   **Internal Logs**: We use the **`qtlog` fixture** to intercept internal Qt messages (`qDebug`, `qWarning`). Tests are configured to fail automatically if critical internal errors are detected.
*   **State Inspection**: If a headless test fails, review the captured logs in `storage/` or use `qtbot.screenshot()` to capture the visual state of a widget for diagnostic feedback.
*   **Interactive Pausing**: For local debugging with a display, use `qtbot.stop()` to pause execution and manually inspect the application state.

## 6. Submission Process

1.  **Issue Link**: All PRs should reference an existing issue or milestone from `WORKING_PROGRESS.md`.
2.  **Linting**: Ensure all pre-commit hooks pass.
3.  **Validation**: Verify that all tests pass headlessly.
4.  **Documentation**: Update relevant Markdown files in `docs/` if your changes affect the project structure or data pipeline.