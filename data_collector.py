import requests
import random

# User settings (MOVE TO ANOTHER FILE)
sprites_version = "other-home-front_default"
locale = "fr"
redaction_symbol = "???"
#print(f"Using sprites from version {sprites_version} and locale '{locale}'")

def select_target_pokemon_number():
    pokemon_no = random.randint(1, 1025)
    print(f"Selected Pokémon number: {pokemon_no}")
    return pokemon_no

def prepare_question(pokemon_no : int) -> dict | None:
    res_pkg = {
        "version": None,
        "dex_entry": None,
        "choices": [], # name, genus, and sprite (url?) for the 4 choices
        "answer": None
    }

    pokemon_data, species_data = fetch_pokemon_data(pokemon_no)
    if not pokemon_data or not species_data:
        print(f"Failed to fetch data for Pokémon number {pokemon_no}.")
        return None

    correct_pokemon_info, dex_entry = extract_species_data(species_data, description=True)
    if not dex_entry:
        print(f"[No dex entry found for locale and version]")
        return None
    res_pkg["dex_entry"] = dex_entry["entry"]
    res_pkg["version"] = dex_entry["version"]

    sprite = extract_pokemon_data(pokemon_data)
    if sprite:
        correct_pokemon_info["sprite"] = sprite
    #res_pkg["choices"].append(correct_pokemon_info)
    #res_pkg["answer"] = correct_pokemon_info["name"]

    other_options = 0

    while other_options < 3:
        random_pokemon_no = get_random_pokemon_by_type(random.choice(pokemon_data['types'])['type']['name'])
        if random_pokemon_no == 0 or random_pokemon_no == pokemon_no:
            print(f"Failed to get a valid random Pokémon number. Skipping this choice.")
            continue

        # Fetch data for the random Pokémon and add it to choices
        random_pokemon_data, random_species_data = fetch_pokemon_data(random_pokemon_no)
        if not random_pokemon_data or not random_species_data:
            print(f"Failed to fetch data for random Pokémon number {random_pokemon_no}. Skipping this choice.")
            continue

        random_pokemon_info, _ = extract_species_data(random_species_data, description=False)
        if random_pokemon_info:
            sprite = extract_pokemon_data(random_pokemon_data)
            if sprite:
                random_pokemon_info["sprite"] = sprite
            res_pkg["choices"].append(random_pokemon_info)
            other_options += 1

    random.shuffle(res_pkg["choices"])
    random_idx = random.randint(0,3)
    res_pkg["choices"].insert(correct_pokemon_info)
    res_pkg["answer"] = random_idx
    return res_pkg

# Fetch the relevant data from the API
def fetch_pokemon_data(pokemon_no: int) -> tuple:
    url = f"https://pokeapi.co/api/v2/pokemon/{pokemon_no}"
    response = requests.get(url)
    if response.status_code != 200:
        print(f"Failed to fetch data for Pokémon number {pokemon_no}. Status code: {response.status_code}")
        return None, None
    pokemon_data = response.json()

    url = f"https://pokeapi.co/api/v2/pokemon-species/{pokemon_no}"
    response = requests.get(url)
    if response.status_code != 200:
        print(f"Failed to fetch species data for Pokémon number {pokemon_no}. Status code: {response.status_code}")
        return None, None
    species_data = response.json()

    return pokemon_data, species_data

# Extract the sprite for the specified version
def extract_pokemon_data(pokemon_data):
    sprites = pokemon_data.get('sprites', {})
    sprite_path = sprites_version.split('-')
    sprite_url = sprites
    for key in sprite_path:
        sprite_url = sprite_url.get(key, {})

    if not isinstance(sprite_url, str):
        print(f"[No sprite found for version {sprites_version}]")
        return None
    
    return sprite_url

    response = requests.get(sprite_url)
    if response.status_code != 200:
        print(f"Failed to fetch sprite from URL. Status code: {response.status_code}")
        return None
    
    return response.content

# Extract the name and genus in the specified locale, and optionally a Pokédex entry in English for a random version
def extract_species_data(species_data, description: bool):
    pokemon_info = {}
    dex_entry = {}

    names = species_data.get('names', [])
    locale_name = next((name['name'] for name in names if name['language']['name'] == locale), None)
    if locale_name:
        pokemon_info["name"] = locale_name
    else:
        print(f"[No name found for locale]")

    # Extract the genus in the specified locale
    genera = species_data.get('genera', [])
    locale_genus = next((genus['genus'] for genus in genera if genus['language']['name'] == locale), None)
    if locale_genus:
        pokemon_info["genus"] = locale_genus
    else:
        print(f"[No genus found for locale]")

    if description:
        # Extract a Pokédex entry in English for a random version
        flavor_text_entries = species_data.get('flavor_text_entries', [])
        dex_entries_en = [entry for entry in flavor_text_entries if entry['language']['name'] == "en"]
        selected_entry = random.choice(dex_entries_en) if dex_entries_en else None
        if selected_entry:
            entry = selected_entry["flavor_text"]
            # Redact the Pokémon's name in the entry if it appears.
            dex_entry["entry"] = str(entry).replace(species_data.get("name", "").capitalize(), redaction_symbol)
            dex_entry["version"] = " ".join(list(map(str.capitalize, selected_entry["version"]["name"].split('-'))))
        else:
            print(f"[No dex entry found for locale and version]")
    
    return pokemon_info, dex_entry      

def get_random_pokemon_by_type(pokemon_type: str) -> int:
    url = f"https://pokeapi.co/api/v2/type/{pokemon_type}"
    response = requests.get(url)
    if response.status_code != 200:
        print(f"Failed to fetch data for Pokémon type '{pokemon_type}'. Status code: {response.status_code}")
        return 0
    
    type_data = response.json()
    pokemon_list = type_data.get('pokemon', [])
    if not pokemon_list:
        print(f"No Pokémon found for type '{pokemon_type}'.")
        return 0
    
    pokemon_no = 0
    while pokemon_no <= 0 or pokemon_no > 1025:
        random_pokemon = random.choice(pokemon_list)
        pokemon_url = random_pokemon['pokemon']['url']
        pokemon_no = int(pokemon_url.split('/')[-2])  # Extract Pokémon number from URL

    return pokemon_no

def get_question():
    pokemon_no = select_target_pokemon_number()
    question_data = prepare_question(pokemon_no)
    if question_data:
        return question_data
    else:
        return None

# TESTING
def format_question_data(question_data):
    formatted = "\n"
    formatted += f"Version: {question_data['version']}\n"
    formatted += f"Dex Entry:\n{question_data['dex_entry']}\n"
    formatted += "Choices:\n"
    for choice in question_data['choices']:
        formatted += f"  - Name: {choice.get('name', 'Unknown')}\n"
        formatted += f"    Genus: {choice.get('genus', 'Unknown')}\n"
        formatted += f"    Sprite URL: {choice.get('sprite', 'No sprite')}\n"
    formatted += f"Answer: {question_data['answer']}\n"
    return formatted

DEBUG = False
DEBUG_GAME = False

if __name__ == "__main__":
    game_over = False
    if DEBUG:
        pkg = prepare_question(25)
        if isinstance(pkg, dict):
            for element in pkg:
                print(f"{element}: {pkg[element]}")
    else:
        while not game_over:
            if DEBUG_GAME:
                try:
                    pokemon_no = int(input("Enter a Pokémon number (1-1025): "))
                except ValueError:
                    break
            else:
                pokemon_no = select_target_pokemon_number()

            question_data = prepare_question(pokemon_no)
            if question_data:
                print(format_question_data(question_data))
                while True:
                    try:
                        answer = int(input("Enter the number of the correct choice (1-4): "))
                        if answer == 0:
                            game_over = True
                            break
                        elif 1 <= answer <= 4:
                            selected_choice = question_data['choices'][answer - 1]
                            if selected_choice['name'] == question_data['answer']:
                                print("Correct!")
                            else:
                                print(f"Wrong! The correct answer was: {question_data['answer']}")
                            break
                        else:
                            raise ValueError
                    except ValueError:
                        print("Invalid input. Please enter a number between 1 and 4, or 0 to end game.")
                
            else:
                print("Failed to prepare question data. Please try again.")

