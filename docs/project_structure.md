# Project Structure

This document outlines the directory layout and architectural principles of the Japanese Dictionary Parser and Flashcard Creator. The repository is designed to be **modular**, **test-driven**, and **cache-aware** to improve on the original `jp_dict` implementation.

## Directory Overview

*   **`app/`**: Contains the core application logic, replacing the previous CLI-focused `jp_dict` directory. This includes the PySide6 View components and the underlying Dictionary Manager service.
*   **`.github/`**: Houses CI/CD workflows and the `.github/copilot-instructions.md` file, which enforces strict coding standards and architectural boundaries for AI-assisted development.
*   **`config/`**: A dedicated directory for application configuration. All constants, paths, and GUI parameters must reside in a central **`config.yaml`** to eliminate hard-coded values in the source.
*   **`docs/`**: Stores technical documentation, including the architectural blueprint and project roadmap.
*   **`scripts/`**: Contains utility scripts for batch processing, database migrations, or auxiliary maintenance tasks.
*   **`storage/`**: Acts as a local cache for parsed data and metadata. This directory is central to the project's efficiency, ensuring that metadata is never recalculated if a cached version exists.
*   **`tests/`**: A comprehensive testing suite utilizing `pytest-qt` for automated, headless validation.
    *   **`fixtures/`**: Contains saved HTML samples of target webpages. These are used for **Contract Testing** to verify that the parser remains functional despite changes to external website formats.
    *   **Fixture versioning**: Each source may contain `current/` and `legacy/` subdirectories to distinguish the latest contract fixtures from earlier historical samples.
*   **`main.py`**: The primary entry point for the application.
*   **`WORKING_PROGRESS.md`**: A living document used to track milestone completion and project status.

## Core Architectural Principles

### 1. Separation of Concerns (MVC/MVP)
The application strictly follows a decoupled pattern (MVC or MVP). Logic for webpage parsing, Anki flashcard creation, and data management must remain entirely separate from the PySide6 Widget classes. All communication between the logic and the GUI is handled through **strongly typed signals**.

### 2. Efficient Pipeline
To address the performance issues of the original implementation, the processing pipeline is **cache-aware**. Before initiating a web request, the system checks the `storage/` directory for existing metadata.

### 3. Automated Headless Testing
The project is designed to minimize manual "user-in-the-loop" testing. Every GUI component and logic service is validated programmatically using **`pytest-qt`** and simulated interactions (e.g., `qtbot.mouseClick`), allowing for full CI/CD validation on headless runners.

### 4. Comprehensive Logging
Following the convention of the `classifier_app`, a robust logging system is implemented across all modules. This allows for detailed state diagnostics and debugging of headless test failures by reviewing logs in the `storage/` or `docs/` directories.