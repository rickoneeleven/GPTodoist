import module_call_counter
import re


def extract_task_id_from_response(response_text):
    match = re.search(r"Task ID: (\d+)", response_text, re.IGNORECASE)
    return int(match.group(1)) if match else None


module_call_counter.apply_call_counter_to_all(globals(), __name__)
