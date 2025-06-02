# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

GPTodoist is a CLI application for managing Todoist tasks with enhanced features for timesheets, long-term task tracking, and diary entries. The application uses the Todoist API and provides a custom command interface for efficient task management.

## Development Commands

### Running the Application
```bash
python3 main.py
```

### Installing Dependencies
```bash
pip3 install -r requirements.txt
```

### Environment Setup
The application requires a Todoist API key:
```bash
export TODOIST_API_KEY="YOUR_ACTUAL_API_KEY"
```

## Architecture

### Core Components

1. **main.py** - Entry point that runs the main loop, handles backups, and orchestrates command processing
2. **state_manager.py** - Centralized state management for JSON files, device ID verification, and backup timestamps
3. **helper_commands.py** - Command parser and router for all user commands
4. **module_call_counter.py** - Debugging utility that wraps functions to count calls

### Helper Modules

- **helper_todoist_part1.py** - Core Todoist operations (complete, delete, update tasks)
- **helper_todoist_part2.py** - Display and task creation functions
- **helper_todoist_long.py** - Long-term task management with [index] prefixes
- **helper_diary.py** - Diary and weekly audit functionality
- **helper_timesheets.py** - Timesheet generation from completed tasks
- **helper_tasks.py** - Task factory and manipulation utilities
- **helper_parse.py** - User input parsing with multi-line support
- **helper_general.py** - Utilities for JSON handling, connectivity, and backups
- **helper_regex.py** - Regex patterns for parsing task properties

### Data Files

The application uses JSON files for persistence:
- `j_todoist_filters.json` - Filter configurations with active filter selection
- `j_active_task.json` - Currently selected task with device ID lock
- `j_todays_completed_tasks.json` - Daily completed task log
- `j_diary.json` - Diary entries and timesheet data
- `j_options.json` - Application settings and backup timestamp
- `j_grafted_tasks.json` - Grafting task tracking

### Key Design Patterns

1. **Device ID Verification**: Prevents concurrent modifications by verifying device ID before commands
2. **State Persistence**: All state is managed through JSON files via state_manager
3. **Command Pattern**: All user commands are routed through helper_commands.ifelse_commands()
4. **Multi-line Input**: Commands can span multiple lines using `!!` to submit or `qq` for single line completion

## Testing

No formal test framework is currently configured. Manual testing is performed through the CLI interface.

## Important Implementation Notes

1. All JSON operations should use `helper_general.load_json()` and `save_json()` for robust error handling
2. Device ID verification happens in the main loop before command execution
3. The application uses Rich for terminal formatting
4. Backup process runs automatically every hour
5. Long-term tasks use `[index]` prefixes for identification
6. Fuzzy matching is available for task completion using `~~~`

### Core Development Principles

Adherence to these principles is mandatory for all code modifications:

1.  **Simplicity, Clarity & Conciseness:** Prioritize simple, logical, easy-to-understand code. Break down complexity. Write only necessary code.
2.  **Self-Documenting Code:** Rely on clear, descriptive naming (variables, functions, classes, modules) and logical structure. Purpose should be evident without comments.
3.  **Minimal Comments:** Avoid comments. Refactor unclear code instead. Remove existing redundant comments during refactoring. Code must be the source of clarity.
4.  **Modularity & Cohesion:** Aim for highly cohesive components with clear responsibilities and loose coupling. Controllers/Coordinators avoid unrelated logic. (Crucial for AI processing as noted in Guiding Pillars)
5.  **DRY (Don't Repeat Yourself):** Extract and reuse common logic patterns.
6.  **Dependency Management:** Prefer constructor injection. Avoid direct creation of complex services within consumers.