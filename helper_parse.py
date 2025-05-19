# File: helper_parse.py
import re # Keep re import, though not used in this specific function, it might be used by other functions in this file later.
import module_call_counter
from rich import print # Using rich.print for consistency with other modules, if desired. Standard print is also fine.

def get_user_input(prompt_message: str = "You: ") -> str:
    """
    Gets potentially multi-line user input from the console.

    Args:
        prompt_message: The message to display to the user before input.

    Returns:
        The accumulated, stripped user input string.
    """
    print(f"[green]{prompt_message}[/green]", end="") # Using rich print style
    user_input_lines = []
    while True:
        try:
            line = input()
            if line == "ignore":
                # Ignore everything typed so far in this input session
                user_input_lines = []
                # Re-prompt after "ignore" to indicate readiness for new input
                print(f"[green]{prompt_message}[/green]", end="")
            elif line == "!!":
                # Submit everything accumulated so far
                break
            elif line.endswith("qq"):
                # Add the current line (without "qq") and submit
                user_input_lines.append(line[:-2])
                break
            else:
                # Add the current line
                user_input_lines.append(line)
        except EOFError:
            # Handle Ctrl+D as a way to submit input (common in Unix terminals)
            print("\n[yellow]EOF detected, submitting input.[/yellow]") # Optional: inform user
            break
        except KeyboardInterrupt:
            # Handle Ctrl+C gracefully: treat as clearing input and re-prompting or exiting
            print("\n[yellow]Input interrupted. Clearing current input.[/yellow]") # Or raise to exit
            user_input_lines = [] # Clear current input
            # Re-prompt or let the main loop handle exit
            print(f"[green]{prompt_message}[/green]", end="")


    # Join the collected lines and strip trailing newline characters
    # rstrip is important to remove the final newline if input ends with Enter
    # and also any newline added if the last line was not terminated with 'qq' or '!!'
    return "\n".join(user_input_lines).rstrip("\n")


# Apply call counter decorator (No changes needed if it's already correctly applied)
if 'module_call_counter' in globals() and hasattr(module_call_counter, 'apply_call_counter_to_all'):
    module_call_counter.apply_call_counter_to_all(globals(), __name__)
else:
    print("[yellow]Warning: module_call_counter not fully available in helper_parse.[/yellow]")