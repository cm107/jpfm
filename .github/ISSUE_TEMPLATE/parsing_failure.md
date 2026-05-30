# Parsing Failure Report

## 1. Description
**Overview of the Failure**
Provide a brief summary of what went wrong (e.g., "The parser is no longer extracting the reading for common verbs on Jisho.org").

**Expected Output**
What metadata did you expect to see?

**Actual Output**
What did the application actually display or log?

---

## 2. Target Information
To help us reproduce this in a **headless environment**, please provide the specific search details.

*   **Target URL**: (e.g., `https://jisho.org/word/食べる`)
*   **Word/Term Searched**: 
*   **Dictionary Source**: (e.g., Jisho, Goo, Tangorin)

---

## 3. Failure Specifics
Which specific fields failed to parse? (Check all that apply)
- [ ] **Reading/Kana**
- [ ] **Primary Definition**
- [ ] **Part of Speech**
- [ ] **Example Sentences**
- [ ] **Pitch Accent**
- [ ] **Other**: (Please specify)

---

## 4. Diagnostic Data
Following the **`classifier_app` logging convention**, please provide the following details.

### **Parser Logs**
Paste the logs from the **`storage/`** or **`docs/`** directory. Look for specific `try-except` failure messages (e.g., `"Element ID 'reading-section' not found"`).
```text
(Paste logs here)
```

### **HTML Source (Required for Fixtures)**
To fix this and prevent future regressions, we need to add a new HTML fixture to **`tests/fixtures/`**. 
*   **Please upload the raw HTML source of the failing page as a `.txt` or `.html` attachment to this issue.**

---

## 5. Cache & Pipeline Status
*   **Was this a new search?**: (Yes/No)
*   **Did the app attempt to use cached metadata from `storage/`?**: (Yes/No)
*   **Is the issue reproducible after clearing the cache for this word?**: (Yes/No)

---

## 6. Environment Information
*   **App Version/Milestone**: (e.g., Milestone 02: Core Parser)
*   **OS**:
*   **Python Version**: (Baseline is 3.7+)