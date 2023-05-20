import module_call_counter
import re


def create_task_id_prompt(user_message):
    # Remove any 4-digit number at the end and everything after it
    user_message = re.sub(r"\b\d{4}.*$", "", user_message).strip()
    prompt = f"{user_message}. What was the task ID of that task? Respond with [Task ID: X], in that format exactly, including the square brackets. never fabricate a task id, and also ask me about when i've eaten today. i'm trying to lose weight and could do with your help."
    return prompt


module_call_counter.apply_call_counter_to_all(globals(), __name__)
