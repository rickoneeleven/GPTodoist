import module_call_counter, helper_general, helper_messages
import os, json, re


def shrink_code(code):
    # Remove all unnecessary spaces but keep newlines
    condensed_code = "\n".join(line.strip() for line in code.split("\n"))

    return condensed_code


def add_file(user_message):
    # Extract the filename from the user message
    filename = user_message.replace("add file ", "").strip()

    # Check if the file exists
    if not os.path.isfile(filename):
        print(f"File {filename} does not exist.")
        return

    # Read the contents of the file
    with open(filename, "r") as file:
        contents = file.read()

    # Shrink the code
    shrunk_contents = shrink_code(contents)

    # Prepend the filename to the shrunk contents
    final_contents = f"{filename}:\n{shrunk_contents}\n"

    # Append the final contents to system_messages.txt
    with open("system_message.txt", "a") as file:
        file.write(final_contents)

    # Load the JSON file if it exists, otherwise create an empty list
    if os.path.isfile("j_loaded_files.json"):
        with open("j_loaded_files.json", "r") as file:
            loaded_files = json.load(file)
    else:
        loaded_files = []

    # Append the new filename to the list
    loaded_files.append({"id": len(loaded_files) + 1, "filename": filename})

    # Write the updated list back to the JSON file
    with open("j_loaded_files.json", "w") as file:
        json.dump(loaded_files, file, indent=2)


def reset_all():
    if os.path.isfile("j_conv_DEFAULT.json"):
        os.rename("j_conv_DEFAULT.json", "j_conversation_history.json")

    if os.path.isfile("j_loaded_files.json"):
        os.remove("j_loaded_files.json")

    open("system_message.txt", "w").close()
    helper_messages.print_conversation_history()


def fresh_session():
    if os.path.isfile("j_conversation_history.json"):
        if not os.path.isfile("j_conv_DEFAULT.json"):
            os.rename("j_conversation_history.json", "j_conv_DEFAULT.json")
        else:
            os.remove("j_conversation_history.json")

    if os.path.isfile("j_loaded_files.json"):
        os.remove("j_loaded_files.json")

    open("system_message.txt", "w").close()


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
            # Remove leading and trailing newlines and any mention of ""
            code = re.sub("", "", code.strip())
            helper_general.write_to_file("refactored.py", code)


module_call_counter.apply_call_counter_to_all(globals(), __name__)
