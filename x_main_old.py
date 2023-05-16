logging.basicConfig(level=logging.ERROR)
hf_logging.set_verbosity_error()

FILE_NAME = "fetched_urls.json"
tokenizer = GPT2Tokenizer.from_pretrained("gpt2")


def get_assistant_response(messages):
    global stop_chatbot_response
    stop_chatbot_response = False

    messages = helper_messages.summarize_and_shorten_messages(messages)
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo", messages=messages, stream=True
        )
    except openai.error.RateLimitError as e:
        print(e)
        print()
        print("Rate limit exceeded? Retrying in a few seconds...")
        time.sleep(10)  # Wait for 10 seconds before retrying
        return get_assistant_response(messages)  # Retry the function call
    except Exception as e:
        print(f"Error while getting assistant response: {e}")
        return ""

    response_chunks = []
    print()

    threading.Thread(target=listen_for_enter_key).start()
    time.sleep(0.5)

    try:
        for chunk in response:
            content = chunk["choices"][0].get("delta", {}).get("content")
            if content is not None:
                response_chunks.append(content)
                print(content, end="")

        print("\n-------------------------------------------------")

        full_response = "".join(response_chunks)

        return full_response
    except KeyboardInterrupt:
        print("\nStopping streaming response due to user command.")
        return "[user cancelled assistant response]"



def print_system_messages(messages):
    print("System messages:")
    for idx, message in enumerate(messages):
        if message["role"] == "system":
            print(f"{idx}. {message['content']}")


def load_fetched_urls():
    if os.path.exists(FILE_NAME):
        with open(FILE_NAME, "r") as file:
            return json.load(file)
    else:
        return {}


fetched_urls = load_fetched_urls()


def load_system_messages():
    messages = [
        {
            "role": "system",
            "content": "You are an AI assistant who loves to use emojis in every response! 😍 Your primary goal is to communicate effectively while adding a touch of fun with emojis like 😄, 😉, or 😎. Whether you're providing programming help, general advice, or just chatting, make sure to always include at least one emoji in your responses for a more engaging conversation! 🎉 Let's get started and spread some emoji joy! 🚀",
        }
    ]
    for url_id, data in fetched_urls.items():
        messages.append(
            {
                "role": "system",
                "content": f"Content from {data['url']} (ID {url_id}):\n{data['summary']}",
                "url_id": url_id,
            }
        )
    if os.path.exists("conversation_history.json"):
        with open("conversation_history.json", "r") as file:
            history = json.load(file)
        if history:
            last_conversation = history[-1]
            messages += last_conversation
    return messages


def save_conversation_to_json(messages, assistant_message):
    if not os.path.exists("conversation_history.json"):
        history = []
    else:
        with open("conversation_history.json", "r") as file:
            history = json.load(file)
    new_conversation = [
        messages[-1],
        {"role": "assistant", "content": assistant_message},
    ]
    history.append(new_conversation)
    with open("conversation_history.json", "w") as file:
        json.dump(history, file, indent=2)


def save_fetched_urls():
    with open(FILE_NAME, "w") as file:
        json.dump(fetched_urls, file)


def clean_messages_for_api(messages):
    cleaned_messages = []
    for message in messages:
        cleaned_message = {"role": message["role"], "content": message["content"]}
        cleaned_messages.append(cleaned_message)
    return cleaned_messages


def truncate_oldest_messages(messages, tokenizer, max_tokens=4000):
    total_tokens = count_tokens(tokenizer, messages)
    removed_conversations = 0
    if os.path.exists("conversation_history.json"):
        with open("conversation_history.json", "r") as file:
            history = json.load(file)
        while total_tokens > max_tokens:
            removed_conversation = history.pop(0)
            messages = [
                message for message in messages if message not in removed_conversation
            ]
            total_tokens = count_tokens(tokenizer, messages)
            removed_conversations += 1

        with open("conversation_history.json", "w") as file:
            json.dump(history, file, indent=2)
    else:
        while total_tokens > max_tokens:
            messages.pop(0)
            total_tokens = count_tokens(tokenizer, messages)
    return messages, removed_conversations


def add_local_file(filename):
    if not os.path.exists(filename):
        return f"File '{filename}' not found. 😢 Please make sure the file path is correct. 📁"
    with open(filename, "r") as file:
        file_content = file.read()
    url_id = len(fetched_urls) + 1
    fetched_urls[url_id] = {"url": filename, "summary": file_content}
    save_fetched_urls()
    return f"Added file '{filename}' to system messages and JSON file! 🎉 (ID {url_id})"


def fetch_url_content(url):
    try:
        response = requests.get(url)
        raw_response = response.text
        soup = BeautifulSoup(raw_response, "html.parser")
        for script in soup(["script", "style"]):
            script.extract()
        text_content = soup.get_text().strip()
        return text_content, raw_response
    except Exception as e:
        print(f"Error fetching URL content: {e}")
        return None, None


def list_cached_items(fetched_urls):
    for url_id, data in fetched_urls.items():
        print(f"ID {url_id}: {data['url']}")


def load_conversation_from_file(filename):
    if not os.path.exists(filename):
        return []
    messages = []
    with open(filename, "r") as file:
        lines = file.readlines()
    with open(filename, "w") as file:
        for line in lines:
            if line.strip() == "-----":
                file.write(line)
                continue
            try:
                role, content = line.strip().split(": ", 1)
                messages.append({"role": role.lower(), "content": content})
                file.write(line)
            except ValueError:
                print(f"Warning: Removed malformed line in {filename}: {line.strip()}")
    return messages


def process_message(message):
    url_regex = r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"
    file_regex = r"\b\w+\.\w+\b"
    urls = re.findall(url_regex, message)
    files = re.findall(file_regex, message)
    summary = None
    url = None
    file_id = None
    if urls:
        url = urls[0]
        summary, _ = fetch_url_content(url)
        message = message.replace(url, "").strip()
    elif files:
        file_name = files[0]
        for msg in messages:
            if msg["role"] == "system" and file_name in msg["content"]:
                file_id = msg["content"].split("ID ")[1].split(")")[0]
                break
        if file_id:
            message = f"Please analyze the content of the file with ID {file_id}. {message.replace(file_name, '').strip()}"
    return message, summary, url


openai.api_key = get_openai_api_key()


def delete_item_by_id(url_id):
    url_id = str(url_id)
    if url_id in fetched_urls:
        del fetched_urls[url_id]
        save_fetched_urls()

        global messages
        messages = [
            message
            for message in messages
            if message["role"] != "system" or message.get("url_id") != url_id
        ]

        return f"Deleted item with ID {url_id} from cache and system messages! 🗑️"
    else:
        return (
            f"Item with ID {url_id} not found in cache. 😕 Please double-check the ID. 🔍"
        )


messages = load_system_messages()
messages += load_conversation_from_file("conversation_history.txt")
while True:
    user_message = input("User: ")
    user_message_with_reminder = (
        f"Remember to use emojis in your response! 😊 {user_message}"
    )

    if user_message.lower() == "cache":
        print_system_messages(messages)
        continue

    if user_message.lower().startswith("add "):
        filename = user_message[4:].strip()
        result_message = add_local_file(filename)
        print(f"Assistant: {result_message}")

        fetched_urls = load_fetched_urls()
        messages = load_system_messages()

        continue

    if user_message.lower() == "commands":
        print_commands()
        continue

    if user_message.lower() == "list":
        list_cached_items(fetched_urls)
        continue

    if user_message.lower().startswith("delete "):
        try:
            url_id = int(user_message[7:].strip())
            result_message = delete_item_by_id(url_id)
            print(f"Assistant: {result_message}")
            continue
        except ValueError:
            print("Assistant: Invalid ID format. 😕 Please enter a valid integer ID. 🔢")

    user_message, summary, url = process_message(user_message)

    if summary:
        url_id = len(fetched_urls) + 1
        fetched_urls[url_id] = {"url": url, "summary": summary}
        save_fetched_urls()

    messages.append({"role": "user", "content": user_message_with_reminder})

    if summary:
        messages.append(
            {
                "role": "system",
                "content": f"Content from URL (ID {url_id}):\n{summary}",
                "url_id": url_id,
            }
        )

    token_count = count_tokens(tokenizer, messages)
    print(f"Tokens after user message: {token_count}")

    if token_count > 4000:
        messages, removed_conversations = truncate_oldest_messages(messages, tokenizer)
        token_count = count_tokens(tokenizer, messages)
        print(f"Tokens after truncating oldest messages: {token_count}")
        if removed_conversations:
            print(
                f"Removed {removed_conversations} oldest conversations from the JSON file."
            )

    cleaned_messages = clean_messages_for_api(messages)
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=cleaned_messages,
    )

    assistant_message = response.choices[0].message["content"]
    print()
    print(f"Assistant: {assistant_message}")
    print("--------------------------------------------------------------")

    save_conversation_to_json(messages, assistant_message)
