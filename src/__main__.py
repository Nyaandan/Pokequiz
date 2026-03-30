"""Allow `python -m src` from the project root."""

from src.app import PokeQuizApp

if __name__ == "__main__":
    PokeQuizApp().run()
