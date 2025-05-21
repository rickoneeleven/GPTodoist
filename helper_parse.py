# File: helper_parse.py
import re
import module_call_counter
from rich import print # Using rich.print for consistency

def get_user_input(prompt_message: str = "You: ") -> str:
    """
    Gets potentially multi-line user input from the console.

    Args:
        prompt_message: The message to display to the user before input.

    Returns:
        The accumulated, stripped user input string.
    """
    print(f"[green]{prompt_message}[/green]", end="")
    user_input_lines = []
    while True:
        try:
            line = input()
            if line == "ignore":
                user_input_lines = []
                print(f"[green]{prompt_message}[/green]", end="")
            elif line == "!!":
                break
            elif line.endswith("qq"):
                user_input_lines.append(line[:-2])
                break
            else:
                user_input_lines.append(line)
        except EOFError:
            print("\n[yellow]EOF detected, submitting current input.[/yellow]")
            break
        except KeyboardInterrupt:
            # Inform the user and then re-raise to allow program termination.
            print("\n[yellow]Keyboard interrupt detected. Exiting application...[/yellow]")
            raise # <<< THIS IS THE KEY CHANGE: Re-raise KeyboardInterrupt
            # The 'raise' statement will cause the exception to propagate
            # up the call stack, allowing the main loop or Python interpreter
            # to terminate the program as expected.

    return "\n".join(user_input_lines).rstrip("\n")


# Apply call counter decorator
if 'module_call_counter' in globals() and hasattr(module_call_counter, 'apply_call_counter_to_all'):
    module_call_counter.apply_call_counter_to_all(globals(), __name__)
else:
    print("[yellow]Warning: module_call_counter not fully available in helper_parse.[/yellow]")