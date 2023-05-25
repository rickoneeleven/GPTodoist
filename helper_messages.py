import module_call_counter, helper_general
import tiktoken, os
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


module_call_counter.apply_call_counter_to_all(globals(), __name__)
