import random
import requests
import src.user_settings as user_settings


def select_target_pokemon_number():
    pokemon_no = random.randint(1, 1025)
    print(f"Selected Pokémon number: {pokemon_no}")
    return pokemon_no

def prepare_question(pokemon_no: int) -> dict | None:
    res_pkg = {
        "version": None,
        "dex_entry": None,
        "choices": [],
        "answer": None,
    }

    pokemon_data, species_data = fetch_pokemon_data(pokemon_no)
    if not pokemon_data or not species_data:
        print(f"Failed to fetch data for Pokémon number {pokemon_no}.")
        return None

    correct_pokemon_info, dex_entry = extract_species_data(species_data, description=True)
    if not dex_entry:
        print("[No dex entry found for locale and version]")
        return None
    res_pkg["dex_entry"] = dex_entry["entry"]
    res_pkg["version"] = dex_entry["version"]

    sprite = extract_pokemon_data(pokemon_data)
    if sprite:
        correct_pokemon_info["sprite"] = sprite

    other_options = 0
    while other_options < 3:
        random_pokemon_no = get_random_pokemon_by_type(
            random.choice(pokemon_data["types"])["type"]["name"]
        )
        if random_pokemon_no == 0 or random_pokemon_no == pokemon_no:
            continue
        random_pokemon_data, random_species_data = fetch_pokemon_data(random_pokemon_no)
        if not random_pokemon_data or not random_species_data:
            continue
        random_pokemon_info, _ = extract_species_data(random_species_data, description=False)
        if random_pokemon_info:
            sprite = extract_pokemon_data(random_pokemon_data)
            if sprite:
                random_pokemon_info["sprite"] = sprite
            res_pkg["choices"].append(random_pokemon_info)
            other_options += 1

    random.shuffle(res_pkg["choices"])
    random_idx = random.randint(0, 3)
    res_pkg["choices"].insert(random_idx, correct_pokemon_info)
    res_pkg["answer"] = random_idx
    return res_pkg

def fetch_pokemon_data(pokemon_no: int) -> tuple:
    response = requests.get(f"https://pokeapi.co/api/v2/pokemon/{pokemon_no}")
    if response.status_code != 200:
        return None, None
    pokemon_data = response.json()

    response = requests.get(f"https://pokeapi.co/api/v2/pokemon-species/{pokemon_no}")
    if response.status_code != 200:
        return None, None
    species_data = response.json()
    return pokemon_data, species_data

def extract_pokemon_data(pokemon_data):
    sprites = pokemon_data.get("sprites", {})
    keys = user_settings.get_sprite_path_keys()
    sprite_url: object = sprites
    for key in keys:
        if not isinstance(sprite_url, dict):
            break
        sprite_url = sprite_url.get(key, {})
    if not isinstance(sprite_url, str):
        return None
    return sprite_url

def extract_species_data(species_data, description: bool):
    pokemon_info = {}
    dex_entry = {}
    locale = user_settings.get_locale()

    names = species_data.get("names", [])
    locale_name = next((n["name"] for n in names if n["language"]["name"] == locale), None)
    if locale_name:
        pokemon_info["name"] = locale_name

    genera = species_data.get("genera", [])
    locale_genus = next((g["genus"] for g in genera if g["language"]["name"] == locale), None)
    if locale_genus:
        pokemon_info["genus"] = locale_genus

    if description:
        entries = species_data.get("flavor_text_entries", [])
        dex_entries_en = [entry for entry in entries if entry["language"]["name"] == "en"]
        selected_entry = random.choice(dex_entries_en) if dex_entries_en else None
        if selected_entry:
            entry = selected_entry["flavor_text"]
            dex_entry["entry"] = str(entry).replace(
                species_data.get("name", "").capitalize(),
                user_settings.redaction_symbol,
            )
            dex_entry["version"] = " ".join(
                map[str](str.capitalize, selected_entry["version"]["name"].split("-"))
            )
    return pokemon_info, dex_entry

def get_random_pokemon_by_type(pokemon_type: str) -> int:
    response = requests.get(f"https://pokeapi.co/api/v2/type/{pokemon_type}")
    if response.status_code != 200:
        return 0
    type_data = response.json()
    pokemon_list = type_data.get("pokemon", [])
    if not pokemon_list:
        return 0
    pokemon_no = 0
    while pokemon_no <= 0 or pokemon_no > 1025:
        random_pokemon = random.choice(pokemon_list)
        pokemon_no = int(random_pokemon["pokemon"]["url"].split("/")[-2])
    return pokemon_no

def get_question():
    pokemon_no = select_target_pokemon_number()
    return prepare_question(pokemon_no)
