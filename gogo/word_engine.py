"""
This module provides functions to save and retrieve a list of Word objects to and from a JSON file.
"""


from objects.word_obj import Word

def save_words(Words: list[Word], file_path: str = "words.json", avoid_duplicates: bool = True):
    """
    Save a list of Word objects to a JSON file.
    If the file already exists, words will be appended to the existing data. If the file does not exist, it will be created.

    :param Words: List of Word objects to save.
    :param file_path: Path to the JSON file where data will be saved. (default: "words.json")
    :param avoid_duplicates: If True (default), words that are equal to an existing entry
        (same language, word_type, sentence, target, past, v3) will not be added again.
    """
    import json
    import os

    # Check if the file exists
    if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
        # Read existing data from the file
        with open(file_path, 'r', encoding='utf-8') as file:
            existing_data = json.load(file)
    else:
        existing_data = []

    existing_words = [Word(**item) for item in existing_data] if avoid_duplicates else []

    new_data = []
    for word in Words:
        if avoid_duplicates and word in existing_words:
            continue
        new_data.append(word.__dict__)

    # Append new data to existing data
    existing_data.extend(new_data)

    # Write the combined data back to the file
    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(json.dumps(existing_data, ensure_ascii=False, indent=4))

def get_words(file_path: str = "words.json") -> list[Word]:
    """
    Read a list of Word objects from a JSON file.

    :param file_path: Path to the JSON file where data is stored. (default: "words.json")
    :return: List of Word objects read from the file.
    """
    import json
    import os

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"The file {file_path} does not exist.")

    with open(file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)

    words = []
    for item in data:
        # JSON has no tuple type, so "sentence" comes back as a list.
        # Convert it back to a tuple to match the Word type hint.
        item = dict(item)
        item["sentence"] = tuple(item["sentence"])
        word = Word(**item)
        words.append(word)

    return words


# TESTING :)

""" Example_words = [Word(language="en", word_type="verb", sentence=("He can", "to school every day"), target="walk", past="walked", v3="walked"),
                 Word(language="en", word_type="noun", sentence=("The", "is on the table"), target="book"),
                 Word(language="en", word_type="adjective", sentence=("The", "is very"), target="beautiful")]

save_words(Example_words, "words.json") """ ## --> it works :)

# Now we will test getting the word data from the json file

""" for word in get_words("words.json"):
    print(f"Language: {word.language}, Type: {word.word_type}, Sentence: {word.sentence}, Target: {word.target}, Past: {word.past}, V3: {word.v3}") """

# Reading the words from the json file works too. Now we can use this to store and retrieve word data in a more structured format.