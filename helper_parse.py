import re
import module_call_counter


def get_user_input():
    print("You: ", end="")
    user_input = ""
    while True:
        line = input()
        if line == "ignore":
            # Ignore everything above
            user_input = ""
        elif line == "!!":
            # Submit everything above and ignore "!!"
            break
        elif line.endswith("qq"):  # User input ended
            user_input += line[:-2]  # Add the current line without the trailing "qq"
            break
        else:
            user_input += line + "\n"  # Add the current line to user_input
    user_input = user_input.rstrip("\n")
    return user_input


module_call_counter.apply_call_counter_to_all(globals(), __name__)
