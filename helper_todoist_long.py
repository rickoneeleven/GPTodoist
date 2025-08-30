"""
Long-term task management module.
This module serves as the public interface for long-term task functionality,
importing and re-exporting functions from specialized sub-modules.
"""

import module_call_counter

# Import all public functions from sub-modules
from long_term_core import (
    get_long_term_project_id,
    find_task_by_index as _find_task_by_index,  # Private in this module
    is_task_recurring,
    is_task_due_today_or_earlier
)

from long_term_operations import (
    delete_task,
    reschedule_task,
    handle_recurring_task,
    handle_non_recurring_task,
    touch_task,
    add_task,
    rename_task,
    change_task_priority,
    postpone_task
)

from long_term_indexing import (
    get_categorized_tasks,
    get_all_long_tasks_sorted_by_index,
    fetch_tasks  # Deprecated but kept for compatibility
)

from long_term_display import (
    format_task_for_display,
    display_tasks,
    display_all_long_tasks
)

# Apply call counter to all imported functions
module_call_counter.apply_call_counter_to_all(globals(), __name__)