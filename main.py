import os, readline
import helper_todoist_part1, helper_todoist_part2, helper_commands, module_call_counter, helper_general, helper_parse, helper_diary
from rich import print
from dateutil.parser import parse
from todoist_api_python.api import TodoistAPI

TODOIST_API_KEY = os.environ["TODOIST_API_KEY"]
api = TodoistAPI(TODOIST_API_KEY)
readline.set_auto_history(
    True
)  # fakenews, here to stop readlines import warning, we use readlines so input() supports left and right arrows


def main_loop():
    while True:
        helper_todoist_part2.get_next_todoist_task(api)
        helper_todoist_part1.print_completed_tasks_count()
        helper_todoist_part2.check_if_grafting(api)
        helper_diary.weekly_audit()
        helper_diary.purge_old_completed_tasks()
        # Update recurring long task patterns to use 'every!'
        helper_todoist_part1.update_recurrence_patterns(api)
        user_message = helper_parse.get_user_input()
        print("processing... ++++++++++++++++++++++++++++++++++++++++++++++")
        if not helper_general.connectivity_check():
            continue
        if not helper_todoist_part1.verify_device_id_before_command():
            continue
        if helper_commands.ifelse_commands(api, user_message):
            continue
        # didn't match any ifelse_commands
        print()
        print("[bold][wheat1]          eh?[/wheat1][/bold]\n")
        continue


module_call_counter.apply_call_counter_to_all(globals(), __name__)
main_loop()