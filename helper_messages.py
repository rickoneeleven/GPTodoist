import module_call_counter, helper_general, helper_gpt, helper_messages
import tiktoken, os, json, datetime, shutil
from rich import print


encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")


def summarize_and_shorten_messages(messages, max_tokens=3000):
    token_count = num_tokens_from_messages(messages)

    if token_count > max_tokens:
        while token_count > max_tokens:
            messages.pop(0)
            token_count = num_tokens_from_messages(messages)
            print(f"popping, token count: {token_count}")

    return messages


def num_tokens_from_messages(messages, model="gpt-3.5-turbo-0301"):
    """Returns the number of tokens used by a list of messages."""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        print("Warning: model not found. Using cl100k_base encoding.")
        encoding = tiktoken.get_encoding("cl100k_base")
    if model == "gpt-3.5-turbo":
        print(
            "Warning: gpt-3.5-turbo may change over time. Returning num tokens assuming gpt-3.5-turbo-0301."
        )
        return num_tokens_from_messages(messages, model="gpt-3.5-turbo-0301")
    elif model == "gpt-4":
        print(
            "Warning: gpt-4 may change over time. Returning num tokens assuming gpt-4-0314."
        )
        return num_tokens_from_messages(messages, model="gpt-4-0314")
    elif model == "gpt-3.5-turbo-0301":
        tokens_per_message = (
            4  # every message follows <|start|>{role/name}\n{content}<|end|>\n
        )
        tokens_per_name = -1  # if there's a name, the role is omitted
    elif model == "gpt-4-0314":
        tokens_per_message = 3
        tokens_per_name = 1
    else:
        raise NotImplementedError(
            f"""num_tokens_from_messages() is not implemented for model {model}. See https://github.com/openai/openai-python/blob/main/chatml.md for information on how messages are converted to tokens."""
        )
    num_tokens = 0
    for message in messages:
        num_tokens += tokens_per_message
        for key, value in message.items():
            num_tokens += len(encoding.encode(value))
            if key == "name":
                num_tokens += tokens_per_name
    num_tokens += 3  # every reply is primed with <|start|>assistant<|message|>
    return num_tokens


def current_tokkies(messages):
    tokkies = num_tokens_from_messages(messages)
    print(f"current message tokkies: {tokkies}\n")


def print_conversation_history():
    conversation_file = "j_conversation_history.json"
    if os.path.exists(conversation_file):
        conversation_history = helper_general.load_json(conversation_file)
        for message in conversation_history:
            print(f"{message['role'].capitalize()}: {message['content']}")
        print("\n\n")


def save_conversation(user_message):
    conversation_file = "j_conversation_history.json"

    if not os.path.exists(conversation_file):
        print("j_conversation_history.json not found.")
        return

    messages = helper_general.load_json(conversation_file)

    # Generate the filename
    user_message_parts = user_message.split()
    if len(user_message_parts) > 1:
        filename = "_".join(user_message_parts[1:])
    else:
        filename = "default"

    filename = f"j_conv_{filename}.json"
    print(f"Filename: {filename}")

    # Save to j_saved_conversations.json
    saved_conversations_file = "j_saved_conversations.json"
    if not os.path.exists(saved_conversations_file):
        with open(saved_conversations_file, "w") as outfile:
            json.dump([], outfile, indent=2)

    saved_conversations = helper_general.load_json(saved_conversations_file)
    highest_id = max([c.get("id", 0) for c in saved_conversations], default=0) + 1
    todays_date = datetime.date.today().strftime("%Y-%m-%d")

    new_saved_conversation = {
        "id": highest_id,
        "filename": filename,
        "date": todays_date,
    }

    saved_conversations.append(new_saved_conversation)

    # Save the updated saved conversations list to j_saved_conversations.json
    with open(saved_conversations_file, "w") as outfile:
        json.dump(saved_conversations, outfile, indent=2)

    # Copy the existing j_conversation_history.json to the new filename
    with open(conversation_file, "r") as src_file, open(filename, "w") as dst_file:
        json.dump(json.load(src_file), dst_file, indent=2)


def generate_filename(assistant_response):
    # Remove any punctuation and replace spaces with underscores
    cleaned_response = "".join(
        c if c.isalnum() else "_" if c.isspace() else "" for c in assistant_response
    )

    # Truncate the response to the first 5 words
    words = cleaned_response.split("_")[:5]
    truncated_response = "_".join(words)

    # Generate the filename
    filename = f"j_conv_{truncated_response}.json"

    return filename


def show_saved_conversations():
    saved_conversations_file = "j_saved_conversations.json"

    if not os.path.exists(saved_conversations_file):
        print("j_saved_conversations.json not found.")
        return

    saved_conversations = helper_general.load_json(saved_conversations_file)

    for conversation in saved_conversations:
        conversation_id = f"[{conversation['id']}]"
        filename = conversation["filename"]
        date = conversation["date"]

        print(f"{conversation_id:<7} {filename:<65} {date}")


def delete_conversation(user_message):
    saved_conversations_file = "j_saved_conversations.json"

    if not os.path.exists(saved_conversations_file):
        print("j_saved_conversations.json not found.")
        return

    saved_conversations = helper_general.load_json(saved_conversations_file)

    # Extract the conversation ID from the user_message
    parts = user_message.split()
    if len(parts) < 3 or not parts[2].isdigit():
        print("Invalid user_message format. It should be like 'delete conv ID'.")
        return

    id = int(parts[2])

    # Find the conversation with the given id
    conversation_to_delete = None
    for conversation in saved_conversations:
        if conversation["id"] == id:
            conversation_to_delete = conversation
            break

    # If the conversation was found, delete it and remove it from the list
    if conversation_to_delete:
        filename = conversation_to_delete["filename"]

        # Remove the JSON file
        if os.path.exists(filename):
            os.remove(filename)
        else:
            print(f"The file {filename} does not exist.")

        # Remove the entry from the j_saved_conversations.json list
        saved_conversations.remove(conversation_to_delete)

        # Save the updated saved conversations list to j_saved_conversations.json
        with open(saved_conversations_file, "w") as outfile:
            json.dump(saved_conversations, outfile, indent=2)

        print(f"Conversation {id} has been deleted.")
    else:
        print(f"Conversation with id {id} not found.")


def load_conversation(user_message):
    conversation_file = "j_conversation_history.json"
    saved_conversations_file = "j_saved_conversations.json"

    if not os.path.exists(saved_conversations_file):
        print("j_saved_conversations.json not found.")
        return

    saved_conversations = helper_general.load_json(saved_conversations_file)

    # Extract the conversation ID from the user_message
    parts = user_message.split()
    if len(parts) < 3 or not parts[2].isdigit():
        print("Invalid user_message format. It should be like 'load conv ID'.")
        return

    id = int(parts[2])

    # Find the conversation with the given id
    conversation_to_load = None
    for conversation in saved_conversations:
        if conversation["id"] == id:
            conversation_to_load = conversation
            break

    if conversation_to_load:
        filename = conversation_to_load["filename"]

        if os.path.exists(filename):
            # Delete the existing j_conversation_history.json if it exists
            if os.path.exists(conversation_file):
                os.remove(conversation_file)

            # Move the looked up filename.json to j_conversation_history.json
            shutil.copy2(filename, conversation_file)

            # Remove the JSON file
            os.remove(filename)

            # Remove the entry from the j_saved_conversations.json list
            saved_conversations.remove(conversation_to_load)

            # Save the updated saved conversations list to j_saved_conversations.json
            with open(saved_conversations_file, "w") as outfile:
                json.dump(saved_conversations, outfile, indent=2)

            helper_messages.print_conversation_history()
        else:
            print(f"The file {filename} does not exist.")
    else:
        print(f"Conversation with id {id} not found.")


module_call_counter.apply_call_counter_to_all(globals(), __name__)
