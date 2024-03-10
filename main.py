import os, readline, subprocess
import helper_todoist, helper_commands, module_call_counter, helper_general, helper_parse
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
        helper_todoist.get_next_todoist_task(api)
        helper_todoist.print_completed_tasks_count()
        helper_todoist.check_if_grafting(api)
        user_message = helper_parse.get_user_input()
        print("processing... ++++++++++++++++++++++++++++++++++++++++++++++")
        if not helper_general.connectivity_check():
            continue
        if helper_commands.ifelse_commands(api, user_message):
            continue
        # didn't match any ifelse_commands
        print()
        print("[bold][wheat1]          eh?[/wheat1][/bold]\n")
        continue


module_call_counter.apply_call_counter_to_all(globals(), __name__)
main_loop()
