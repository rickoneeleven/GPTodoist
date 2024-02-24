import module_call_counter, helper_general
import os, re


def shrink_code(code):
    # Remove all unnecessary spaces but keep newlines
    condensed_code = "\n".join(line.strip() for line in code.split("\n"))

    return condensed_code


def fresh_session():
    if os.path.isfile("j_conversation_history.json"):
        if not os.path.isfile("j_conv_DEFAULT.json"):
            os.rename("j_conversation_history.json", "j_conv_DEFAULT.json")
        else:
            os.remove("j_conversation_history.json")

    if os.path.isfile("j_loaded_files.json"):
        os.remove("j_loaded_files.json")

    open("system_message.txt", "w").close()
    helper_general.backup_json_files()


def extract_and_save_code_sections(assistant_message, output_filename="refactored.py"):
    """
    Extract code between triple backticks and write to the specified output file.

    Args:
        assistant_message (str): The message containing code sections.
        output_filename (str, optional): The file to save the extracted code sections. Defaults to "refactored.py".
    """
    code_sections = re.findall(r"```(?:.*?)?(.*?)```", assistant_message, re.DOTALL)
    if code_sections:
        for i, code in enumerate(code_sections):
            code = re.sub("python", "", code.strip())  # Remove any mention of "python"
            helper_general.write_to_file("refactored.py", code)


module_call_counter.apply_call_counter_to_all(globals(), __name__)
