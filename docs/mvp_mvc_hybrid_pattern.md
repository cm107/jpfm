# MVP/MVC Hybrid Pattern Rules

To achieve 100% headless automation and strict separation of concerns, this project employs a hybrid architectural approach. We use **MVP** as the primary application framework to isolate business logic and **MVC** specifically when leveraging Qt’s optimized data-handling widgets.

## 1. Primary Application Framework: MVP (Model-View-Presenter)
**Rule**: Use MVP for the high-level coordination of all application features, including parsing, Anki card generation, and configuration management.

### **Components**
*   **Model**: The "Dictionary Manager" service and parsing engine. It handles all data processing, web requests (using HTML fixtures for testing), and interactions with the `storage/` directory.
*   **View (Passive)**: PySide6 `QWidget` or `QMainWindow` subclasses. These must be "dumb" and contain **no business logic**. They only emit signals when users interact with them and provide public methods for the Presenter to update their state.
*   **Presenter**: The middleman that contains the application logic. It listens to View signals, interacts with the Model, and explicitly updates the View.

### **Testing Strategy**
*   **Logic Isolation**: Test the Presenter using standard Python unit tests by providing it with a **Mock View**. This allows for verification of the processing pipeline without launching a `QApplication`.
*   **Headless UI**: Use the **`qtbot` fixture** from `pytest-qt` to simulate interactions with the View (e.g., `qtbot.mouseClick`) and verify it communicates correctly with the Presenter.

---

## 2. Component-Level Framework: MVC (Model-View-Controller)
**Rule**: Use MVC exclusively when utilizing Qt’s native **Model/View Architecture** for complex data displays, such as the dictionary results table or history lists.

### **Components**
*   **Model**: Subclasses of `QAbstractItemModel` (e.g., `QAbstractListModel` or `QAbstractTableModel`). This holds the data structure for the UI.
*   **View**: Standard Qt view widgets like `QTableView`, `QListView`, or `QTreeView`.
*   **Controller**: Built into the Qt framework; it handles the translation of user inputs into model index changes.

### **Testing Strategy**
*   **Structural Validation**: Use the **`qtmodeltester` fixture** to automatically verify the integrity of custom models.
*   **Automatic Checks**: The tester will catch common bugs like off-by-one errors in row insertions, incorrect index resolution, or row count mismatches without manual interaction.

---

## 3. Communication & Data Rules

| Rule Category | Requirement |
| :--- | :--- |
| **Signal Flow** | Use **strongly typed signals** for all communication between the View and Presenter. |
| **Logic Placement** | Parsing or Anki creation logic must **never** be inside a PySide6 Widget class. |
| **State Management** | The View should not maintain state; it should reflect the state provided by the Presenter or the `QAbstractItemModel`. |
| **Internal Errors** | Leverage the **`qtlog` interceptor** to capture internal Qt errors (qDebug, qWarning) during automated tests to identify rendering or layout failures. |

## 4. Summary of When to Use Which
*   **Use MVP when**: You are defining the "How the app works" logic (e.g., "When I click search, fetch from the web, then show results").
*   **Use MVC when**: You are defining the "How data is organized for a table" logic (e.g., "Column 1 is the Kanji, Column 2 is the Reading").

By adhering to this hybrid model, the core logic remains testable in isolation (MVP/Presenter), while complex UI data management remains robust and structurally sound (MVC/ModelTester).