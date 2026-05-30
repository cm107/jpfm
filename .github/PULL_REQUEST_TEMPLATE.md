# Pull Request Template

## Description
*Please provide a brief summary of the changes and the problem they solve. Reference any relevant issues or milestones from `WORKING_PROGRESS.md`.*

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Refactoring (architectural improvement, no functional changes)
- [ ] Test update (adding/improving tests or fixtures)

## Architectural Compliance (MVP/MVC)
- [ ] **Separation of Concerns**: Is the business logic (parsing, Anki creation) strictly isolated from the PySide6 View classes?
- [ ] **Signal Communication**: Does the View communicate with the Presenter/Manager solely through strongly typed signals?
- [ ] **Passive View**: Does the View contain zero business logic or direct Model manipulation?
- [ ] **Cache Awareness**: If this PR affects the processing pipeline, does it check the `storage/` directory before initiating new web requests?

## Testing & Validation
- [ ] **Headless Execution**: Do all new tests pass in a headless environment (e.g., using `QT_QPA_PLATFORM=offscreen`)?
- [ ] **Pytest-qt Best Practices**:
    - [ ] Have all new widgets been registered using `qtbot.addWidget(widget)` to prevent window leaks?
    - [ ] Do tests prefer native API methods (e.g., `setText()`) over raw event simulation where possible?
    - [ ] Are asynchronous operations handled via `qtbot.waitSignal`?
- [ ] **Fixture Testing**: If parsing logic was modified, have new HTML fixtures been added to `tests/fixtures/` to maintain contract stability?
- [ ] **Model Integrity**: If a custom `QAbstractItemModel` was added, has it been validated with the `qtmodeltester` fixture?

## Documentation & Code Style
- [ ] **Type Hinting**: Do all new function signatures include strict type hinting?
- [ ] **Docstrings**: Are all classes and methods documented using Google or NumPy-style docstrings?
- [ ] **Logging**: Has the comprehensive logging system been used to track state transitions and errors?
- [ ] **Project Tracking**: Has `WORKING_PROGRESS.md` been updated to reflect completed tasks or milestones?

## Diagnostic Checks
- [ ] I have verified that no internal Qt warnings or critical errors are emitted (via `qtlog` interceptor).
- [ ] I have verified that no exceptions are silently swallowed within slots or virtual methods.