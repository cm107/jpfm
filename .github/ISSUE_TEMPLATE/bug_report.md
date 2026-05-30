# Bug Report

## 1. Description
**Describe the bug**
A clear and concise description of what the bug is.

**Expected behavior**
A clear and concise description of what you expected to happen.

**Actual behavior**
A clear and concise description of what actually happened.

---

## 2. Headless Reproduction & Testing
To support our "no-user-in-the-loop" workflow, please verify if this issue is detectable through automated testing.

- [ ] **Reproducible Headlessly?**: Can this bug be reproduced by running the test suite in a headless environment (e.g., using `export QT_QPA_PLATFORM=offscreen` or `xvfb-run`)?
- [ ] **Existing Test Failure?**: Is there an existing test in the `tests/` directory that fails because of this bug?
- [ ] **Qt Log Interception**: Did the `qtlog` interceptor or the project's logging system capture any internal warnings or critical errors (e.g., `qWarning`, `qCritical`)?

---

## 3. Diagnostic Data
Please provide the following information to help pinpoint the state divergence without manual interaction.

### **Log Output**
Paste relevant logs from the `storage/` directory or the `pytest-qt` console output here. Ensure any captured exceptions from Qt slots or virtual methods are included.
```text
(Paste logs here)
```

### **UI Component Details**
If the bug relates to a specific UI element, provide the **Widget Object Name** (the `objectName()` property). This allows us to map the failure to `qtbot` screenshots and logs.
*   **Failing Widget(s)**: (e.g., `btn_search`, `results_table`)

---

## 4. Environment Information
- **OS**: [e.g., Ubuntu 22.04, Windows 11]
- **Python Version**: (Project baseline is 3.7+)
- **PySide6 Version**:
- **Project Milestone**: (Refer to `WORKING_PROGRESS.md` if applicable)

---

## 5. Additional Context
Add any other context about the problem here, such as whether this bug affects the "Efficient Pipeline" or if it is a visual regression in the GUI layer.