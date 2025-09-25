DATETIME of last agent review: 25/09/2025 14:55

# Todoist CLI Helper

A command-line interface (CLI) tool designed for efficient interaction with your Todoist account. It focuses on managing your active task, handling a separate list of long-term tasks, viewing tasks, and generating daily timesheet entries based on completed items.

## Installation

1.  **Prerequisites:**
    - Python 3 (tested with Python 3.11+; 3.10 also works)
    - `pip` (Python package installer)

2.  **Clone the Repository (if applicable):**
    ```bash
    git clone <your-repository-url>
    cd <repository-directory>
    ```

3.  **Create and Activate a Virtual Environment (recommended):**
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate   # Windows: .venv\Scripts\activate
    python -m pip install --upgrade pip setuptools wheel
    ```

4.  **Install Dependencies:**
    Ensure you are in the project directory containing `requirements.txt`, then:
    ```bash
    pip install -r requirements.txt
    ```

5.  **Deactivating the Environment:**
    ```bash
    deactivate
    ```

## Configuration

1.  **Todoist API Key:**
    The tool requires your Todoist API key to interact with your account. Set it as an environment variable.
    *   Find your API key in Todoist: Settings -> Integrations -> Developer -> API token.
    *   Add the key to your shell's configuration file (e.g., `~/.bashrc`, `~/.zshrc`). If using the virtual environment above, ensure this is set in the shell before running the app:
        ```bash
        export TODOIST_API_KEY="YOUR_ACTUAL_API_KEY"
        ```
    *   Reload your shell configuration (e.g., `source ~/.bashrc`) or open a new terminal window.

2.  **Active Filters (`j_todoist_filters.json`):**
    This JSON file defines different Todoist filter views you can switch between using the `flip` command. The tool uses the filter marked as `isActive: 1` to fetch and display tasks.

    *   **File:** `j_todoist_filters.json` (create this file in the same directory as `main.py` if it doesn't exist)
    *   **Structure:** A JSON list `[]` containing one or more filter objects `{}`.
    *   **Filter Object Fields:**
        *   `"id"`: (Currently unused integer, can be anything unique like 1, 2, etc.)
        *   `"filter"`: (String) The Todoist filter query string (e.g., `"(today | overdue) & #Work"`).
        *   `"isActive"`: (Integer) Set to `1` for the filter to be active, `0` for inactive. **Only one filter should have `isActive: 1` at any time.** The `flip` command toggles the `isActive` status between the defined filters.
        *   `"project_id"`: (String, Optional) The ID of the Todoist project where tasks created with the `add task` command should go. If empty or omitted, tasks go to the Inbox or your default project. Find project IDs via the Todoist web app URL or API tools.

    *   **Example `j_todoist_filters.json`:**
        ```json
        [
          {
            "id": 1,
            "filter": "(no due date | today | overdue) & #Inbox",
            "isActive": 1,
            "project_id": ""
          },
          {
            "id": 2,
            "filter": "(today | overdue | no due date) & #RCP",
            "isActive": 0,
            "project_id": "2294289600"
          }
        ]
        ```
        In this example, the `#Inbox` filter is initially active. Running `flip` would set `#Inbox`'s `isActive` to `0` and `#RCP`'s `isActive` to `1`.

## Usage

1.  **Run the Application:**
    ```bash
    # In a new shell, from the project root
    source .venv/bin/activate   # Windows: .venv\Scripts\activate
    python main.py
    ```

## Migrating State (Old -> New)

If you used GPTodoist on another machine, copy your state files to avoid missing-timesheets alerts and to bring over today’s completed items.

- Key files in the project root on the old machine:
  - `j_diary.json` — timesheets/diary entries (used for the weekly audit)
  - `j_todays_completed_tasks.json` — rolling log of completed tasks (all days)
  - `j_number_of_todays_completed_tasks.json` — today’s completed count (recomputed by the merge tool)

### Option A: Straight copy (replace)

1) On the old machine (from the project root):
```bash
tar -czf gptodoist-state.tar.gz j_diary.json j_todays_completed_tasks.json j_number_of_todays_completed_tasks.json || true
```

2) Transfer the archive to the new machine and extract it in the new project root:
```bash
scp <old>:/path/to/repo/gptodoist-state.tar.gz .
tar -xzf gptodoist-state.tar.gz
```

### Option B: Merge manually (no tool provided)

This repository does not include a merge tool. If you have already created entries on the new machine and want to merge:

1) Open both old and new files side-by-side and reconcile manually:
   - `j_diary.json`: merge per-day entries. Keep valid JSON; prefer the most complete record for overlapping dates.
   - `j_todays_completed_tasks.json`: append missing entries, ensuring each item has a unique integer `id` and a `datetime` in `YYYY-MM-DD HH:MM:SS`.
   - `j_number_of_todays_completed_tasks.json`: optional, it will be recalculated by the app as you complete tasks.

2) Save merged files to the new project root and run the app. The application will read these files via `state_manager`.

2.  **Interaction:**
    *   The application will display the next task based on your active filter, completed task counts, and other status info.
    *   It will then prompt you for input (`You: `).
    *   **Multi-line Input:**
        *   Type your command. For multi-line commands or notes, press Enter to go to the next line.
        *   End a single line and submit immediately by typing `qq` at the end of the line (e.g., `add task My new task qq`).
        *   Submit all lines typed so far by entering `!!` on a new line.
        *   Clear all lines typed so far (before submitting) by entering `ignore` on a new line.
    *   Enter a command and press Enter (or use the multi-line triggers).

3.  **Exit:** Press `CTRL+C`.

## Commands Reference

Commands are matched case-insensitively.

**Core Task Actions (Active Task):**

*   `done`: Completes the currently displayed active task and logs it to the daily completed list (`j_todays_completed_tasks.json`).
*   `skip`: Completes the currently displayed active task *without* logging it.
*   `delete`: Deletes the currently displayed active task from Todoist.
*   `time <due_string>`: Sets/updates the due date/time for the active task (e.g., `time tomorrow 9am`, `time next monday`). Handles recurring task warnings.
*   `postpone <due_string>`: Postpones the active task. For recurring tasks, it completes the current instance and creates a new one with the specified due date. For non-recurring, it updates the due date.
*   `rename <new_name>`: Renames the active task.
*   `priority <1|2|3|4>`: Changes the priority of the active task (1=P1 High, 4=P4 Low).

**Task Creation:**

*   `add task <content>`: Adds a new task. Uses the `project_id` from the active filter in `j_todoist_filters.json` if specified, otherwise adds to Inbox/default. Supports Todoist's natural language for dates/times/priority within the `<content>` (e.g., `add task Review report p1 tomorrow`).
*   `xx <task_name>`: Logs an ad-hoc task directly to the daily completed list (`j_todays_completed_tasks.json`) without adding it to Todoist first.

**Fuzzy Matching / Search:**

*   `~~~ <fuzzy_name>`: Attempts to find and complete a task from the active filter based on fuzzy name matching.
*   `||| <search_term>`: Performs a search across your Todoist tasks using the provided search term via the API and displays results.

**Display & View Commands:**

*   `all` / `show all`: Clears the screen and displays all tasks matching the current active filter.
*   `completed` / `show completed`: Clears the screen and displays tasks logged as completed today from `j_todays_completed_tasks.json`.
*   `flip`: Switches the `isActive` flag in `j_todoist_filters.json` to the next filter definition, changing the active view.
*   `clear`: Clears the terminal screen.

**Long-Term Task Management (Operates on "Long Term Tasks" Project):**

*   `show long`: Clears the screen and displays *due* tasks from the "Long Term Tasks" project, categorized into One-Shots and Recurring. Tasks require `[index]` prefix.
*   `show long all`: Clears the screen and displays *all* tasks from the "Long Term Tasks" project, sorted by their `[index]` prefix.
*   `add long <task_name>`: Adds a new task to the "Long Term Tasks" project, automatically assigning the next available `[index]` prefix.
*   `time long <index> <schedule>`: Reschedules the long-term task with the specified `[index]` using the `<schedule>` string (e.g., `time long 5 every! monday 9am`).
*   `skip long <index>`: "Touches" the long-term task with `[index]`. Completes recurring instances, pushes non-recurring to tomorrow. Does *not* log completion.
*   `touch long <index>`: "Touches" the long-term task with `[index]`. Completes recurring instances, pushes non-recurring to tomorrow. *Logs* non-recurring touches to the daily completed list.
*   `rename long <index> <new_name>`: Renames the long-term task with `[index]`, preserving the index prefix.
*   `delete long <index>`: Deletes the long-term task with `[index]` from Todoist.

**Diary & Timesheets:**

*   `diary`: Shows a summary of diary entries (prompts for day or week).
*   `diary <objective>`: Updates the `overall_objective` field for today's entry in the diary file (`j_diary.json`).
*   `timesheet`: Initiates the process to generate a timesheet entry in the diary file (`j_diary.json`) based on selecting tasks from the daily completed list (`j_todays_completed_tasks.json`).
