import module_call_counter
import ast, astunparse, os, json


def shrink_code(code):
    # Parse the code into an AST
    tree = ast.parse(code)

    # Remove docstrings
    for node in ast.walk(tree):
        if isinstance(
            node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)
        ):
            node.docstring = None

    # Remove comments and unnecessary whitespace by unparsing the AST back into code
    code_without_comments = astunparse.unparse(tree)

    # Remove all unnecessary spaces but keep newlines
    condensed_code = "\n".join(
        line.strip() for line in code_without_comments.split("\n")
    )

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
    # Delete j_conversation_history.json if it exists
    if os.path.isfile("j_conversation_history.json"):
        os.remove("j_conversation_history.json")

    # Delete j_loaded_files.json if it exists
    if os.path.isfile("j_loaded_files.json"):
        os.remove("j_loaded_files.json")

    # Empty system_messages.txt
    open("system_message.txt", "w").close()


module_call_counter.apply_call_counter_to_all(globals(), __name__)
