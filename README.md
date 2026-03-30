# PokéQuiz (WIP)

Test your knowledge of the Pokédex. A small [Kivy](https://kivy.org/) quiz app that pulls Pokémon data from [PokéAPI](https://pokeapi.co/) (when not running in local test mode).

## Requirements

- **Python** 3.10 or newer
- **Kivy** 2.3.x (matches `#:kivy 2.3.1` in the UI definition)
- **requests** (used when fetching live questions from PokéAPI)

Install dependencies (example):

```bash
pip install "kivy>=2.3" requests
```

Platform-specific Kivy setup is documented on the [Kivy installation page](https://kivy.org/doc/stable/gettingstarted/installation.html).

## Running the app

From the **project root** (`pokequiz/`), either:

```bash
python main.py
```

or:

```bash
python -m src
```

Both load the same `PokeQuizApp` in `src/app.py`. In **VS Code**, use the launch configuration **“Python Debugger: Module src”** (or run `main.py`) with the workspace folder as the current working directory so asset paths resolve correctly.

## Project layout

| Path                  | Purpose                                                       |
|-----------------------|---------------------------------------------------------------|
| `main.py`             | Thin entrypoint for local development                         |
| `src/`                | Application code (`app`, UI widgets, data layer, settings)    |
| `src/pokequiz.kv`     | Kivy screen and widget definitions                            |
| `assets/`             | Backgrounds, particles, test images                           |
| `user_settings.json`  | Saved preferences (created at runtime; gitignored)            |

## Debug vs live API

In `src/app.py`, `DEBUG = True` uses bundled test data from `src/test_data.py` instead of calling the API. Set `DEBUG = False` to use `src/data_collector.py` and the network; ensure PokéAPI is reachable.
