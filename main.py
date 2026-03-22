import os
from pathlib import Path


def _font_search_dirs() -> list[Path]:
    dirs: list[Path] = []
    if os.name == "nt":
        windir = os.environ.get("WINDIR", r"C:\Windows")
        dirs.append(Path(windir) / "Fonts")
    else:
        dirs.extend(
            [
                Path("/Library/Fonts"),
                Path("/System/Library/Fonts"),
                Path("/System/Library/Fonts/Supplemental"),
            ]
        )
    return [d for d in dirs if d.is_dir()]


def _first_font(*candidates: str) -> Path | None:
    for base in _font_search_dirs():
        for name in candidates:
            p = base / name
            if p.is_file():
                return p
    return None


def _first_sitka_semibold() -> Path | None:
    """
    Prefer Sitka Semibold (Windows: often 'Sitka Text Semibold.ttf' or similar).
    Uses glob so minor filename differences still match.
    """
    for base in _font_search_dirs():
        # Prefer .ttf, then .ttc (collection; Kivy may use first face).
        for pattern in ("sitka*semibold*.ttf", "sitka*semibold*.ttc"):
            try:
                matches = sorted(base.glob(pattern))
            except OSError:
                continue
            for p in matches:
                if p.is_file():
                    return p
    return _first_font(
        "Sitka Text Semibold.ttf",
        "SitkaText-Semibold.ttf",
        "SitkaTextSemibold.ttf",
        "Sitka Semibold.ttf",
    )


def _apply_default_ui_font() -> None:
    """
    Set Kivy default font to Sitka Semibold when available, else Arial.
    Must run before importing kivy.app (and most other Kivy modules).
    """
    sitka_semibold = _first_sitka_semibold()
    arial = _first_font(
        "arial.ttf",
        "ARIAL.TTF",
        "Arial.ttf",
    )
    chosen = sitka_semibold or arial
    if chosen is None:
        return

    path = str(chosen.resolve())
    from kivy.config import Config

    # [family_name, regular, italic, bold, bolditalic] — single-file fallback for styles
    Config.set("kivy", "default_font", ["PokeQuizUI", path, path, path, path])


_apply_default_ui_font()

import random
import test_data
from data_collector import get_question
from kivy.app import App
from kivy.clock import Clock
from kivy.factory import Factory
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.properties import StringProperty, NumericProperty, ListProperty, ColorProperty

DEBUG = True # Debug mode will use generic test data instead of calling the API
base_color = (.7, .7, .7, .5)
selection_color = (.8, .4, 0, .8)
answer_color = (.1, .8, .4, .8)
incorrect_color = (.8, .1, .1, .8)
unset_color = (.7, .7, .7, .2)

# Diagonal drift (bottom-left → top-right): equal x/y step in screen space.
_SQRT2_INV = 0.7071067811865476


class ParticleBackdrop(FloatLayout):
    """
    Full-screen background image plus drifting particle layers.
    Use particle_variant 'l' or 's' to pick assets/bg/particles_*_{l|s}.png for all colors.
    """

    particle_variant = StringProperty("l")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (1, 1)
        self._tick_event = None
        self._sprites = []
        self._started = False

        bg = Image(
            source="assets/bg/background.png",
            allow_stretch=True,
            keep_ratio=False,
            fit_mode="fill",
        )
        bg.size_hint = (1, 1)
        self.add_widget(bg)

        self.bind(size=self._try_start_particles)  # type: ignore[attr-defined]

    def on_parent(self, *args):
        if self.parent is None and self._tick_event is not None:
            self._tick_event.cancel()
            self._tick_event = None

    def _try_start_particles(self, *args):
        if self._started or self.width <= 0 or self.height <= 0:
            return
        self._started = True
        self._spawn_particles()
        if self._tick_event is None:
            self._tick_event = Clock.schedule_interval(self._tick, 1 / 60.0)

    def _spawn_particles(self):
        for s in self._sprites:
            self.remove_widget(s["img"])
        self._sprites.clear()

        path = "assets/bg/"
        prefix = "particle_"
        suffix = f"_{self.particle_variant}"
        # Two layers per color, different speeds (px/s).
        configs = [
            (f"{path}{prefix}red{suffix}.png", 38),
            (f"{path}{prefix}red{suffix}.png", 74),
            (f"{path}{prefix}green{suffix}.png", 52),
            (f"{path}{prefix}green{suffix}.png", 91),
            (f"{path}{prefix}blue{suffix}.png", 46),
            (f"{path}{prefix}blue{suffix}.png", 108),
        ]

        for src, speed in configs:
            img = Image(source=src, fit_mode="contain", opacity=0.9)
            img.size_hint = (None, None)
            self.add_widget(img)
            sprite = {"img": img, "speed": float(speed), "pos": [0.0, 0.0]}
            self._sprites.append(sprite)
            img.bind(texture=lambda inst, tex, sp=sprite: self._on_particle_texture(sp))  # type: ignore[attr-defined]

    def _on_particle_texture(self, sprite):
        self._apply_particle_size(sprite["img"])
        self._randomize_bottom_left(sprite)

    def _apply_particle_size(self, img: Image) -> None:
        if self.width <= 0 or self.height <= 0:
            return
        tw, th = img.texture_size
        if tw <= 0 or th <= 0:
            return
        w, h = self.width, self.height
        scale = min(w * 0.42 / tw, h * 0.42 / th, 2.2)
        img.width = tw * scale
        img.height = th * scale

    def _randomize_bottom_left(self, sprite: dict) -> None:
        img = sprite["img"]
        iw = img.width or 1
        ih = img.height or 1
        w, h = self.width, self.height
        sprite["pos"] = [
            random.uniform(-iw * 1.1, w * 0.45),
            random.uniform(-ih * 1.1, h * 0.45),
        ]
        img.pos = (sprite["pos"][0], sprite["pos"][1])

    def _tick(self, dt: float) -> None:
        if not self._sprites or self.width <= 0:
            return
        W, H = self.width, self.height
        for s in self._sprites:
            img = s["img"]
            if img.width <= 0 or img.height <= 0:
                if img.texture:
                    self._apply_particle_size(img)
                else:
                    continue
            sp = s["speed"]
            x = s["pos"][0] + sp * dt * _SQRT2_INV
            y = s["pos"][1] + sp * dt * _SQRT2_INV
            s["pos"][0] = x
            s["pos"][1] = y
            img.pos = (x, y)
            iw, ih = img.width, img.height
            # Off past top-right: respawn toward bottom-left.
            if x > W + iw * 0.35 and y > H + ih * 0.35:
                self._randomize_bottom_left(s)


Factory.register("ParticleBackdrop", cls=ParticleBackdrop)


class ScoreCell(BoxLayout):
    """
    Small colored box used to show whether a question was answered correctly.
    """
    status = StringProperty("unset")  # "unset" | "correct" | "incorrect"
    cell_color = ListProperty(list(unset_color))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._sync_color(self.status)

    def on_status(self, instance, value):
        self._sync_color(value)

    def set_status(self, status: str):
        """
        Explicit setter used by game logic to keep status and color in sync
        even if property callbacks are skipped in edge cases.
        """
        self.status = status
        self._sync_color(status)

    def _sync_color(self, status: str):
        if status == "correct":
            self.cell_color = list(answer_color)
        elif status == "incorrect":
            self.cell_color = list(incorrect_color)
        else:
            self.cell_color = list(unset_color)

class GameScreen(Screen):
    pass

class MenuScreen(Screen):
    pass

class SettingsScreen(Screen):
    pass

# Class for the quiz buttons
class ShinyButton(Button):
    img_source = StringProperty("assets/test/blank.png")
    option_name = StringProperty("")
    bg_color = ColorProperty((.7, .7, .7, .5))

    def __init__(self, **kwargs):
        super(ShinyButton, self).__init__(**kwargs)

    def prepare(self, data: dict):
        self.bg_color = base_color
        self.img_source = data["sprite"]
        self.option_name = data["name"]

    # Change the button color to green for the correct answer
    def show_correct(self):
        self.bg_color = answer_color

    # Change the button color to red for a selected wrong answer
    def show_incorrect(self):
        self.bg_color = selection_color

# The app entry point
class PokeQuizApp(App):
    question_no = NumericProperty(0)
    score = NumericProperty(0)
    q_text = StringProperty(test_data.q_text)
    q_version = StringProperty(test_data.q_version)
    buttons = ListProperty([])

    score_label_text = StringProperty("")

    # Mode configuration:
    # - bounded: total_questions = 4/10/20
    # - indefinite: no end; scorebox shows only last 5 correctness results
    current_mode_limit = None  # int | None
    indefinite_window_size = 5

    answer_received = False
    correct_answer: int
    game_end = False

    # Created/managed dynamically to support variable scorebox sizes.
    scorebox_cells = []
    scorebox_grid = None
    game_screen_ref = None
    sm = None

    _pending_continue_event = None

    # For bounded mode (len == current_mode_limit)
    answer_results = []
    # For indefinite mode (len == indefinite_window_size)
    last_five_results = []

    def __init__(self, **kwargs):
        super(PokeQuizApp, self).__init__(**kwargs)
        self._setup_static_text()

    def build(self):
        sm = ScreenManager()
        self.sm = sm
        menu_screen = MenuScreen(name="menu")
        game_screen = GameScreen(name="game")
        settings_screen = SettingsScreen(name="settings")
        sm.add_widget(menu_screen)
        sm.add_widget(game_screen)
        sm.add_widget(settings_screen)
        self.game_screen_ref = game_screen
        self.scorebox_grid = game_screen.ids.get("scorebox_grid")

        self.buttons = []
        for i in range(4):
            btn = sm.get_screen("game").ids[f"answer_button_{i}"]
            btn.bind(on_release=lambda instance, idx=i: self.receive_answer(idx))
            btn.disabled = True  # enabled when a mode is selected
            self.buttons.append(btn)

        # Initialize scorebox for the menu (keep UI sane even before starting).
        self.current_mode_limit = None
        self._reset_game_state(limit=None)
        self._setup_scorebox_cells(cell_count=self.indefinite_window_size)

        sm.current = "menu"
        return sm

    def _setup_static_text(self):
        # Text shown on screen before a mode is selected.
        self.q_text = "Select a mode to start."
        self.q_version = ""
        self.score_label_text = "Score: 0"

    def set_mode(self, mode: str):
        """
        Called from KV menu buttons.
        mode: '4' | '10' | '20' | 'indefinite'
        """
        if mode == "indefinite":
            self._switch_to_new_game(limit=None)
        else:
            self._switch_to_new_game(limit=int(mode))

    def _switch_to_new_game(self, limit):
        self._cancel_pending_continue()
        self.current_mode_limit = limit
        self._reset_game_state(limit=limit)
        self._setup_scorebox_cells(cell_count=(
            self.indefinite_window_size if limit is None else int(limit)
        ))

        # Enable answer buttons and start the first question.
        for btn in self.buttons:
            btn.disabled = False

        # Switch to the game UI.
        if self.sm is not None:
            self.sm.current = "game"

        self.continue_game_loop()

    def _cancel_pending_continue(self):
        if self._pending_continue_event is not None:
            try:
                self._pending_continue_event.cancel()
            except Exception:
                pass
            self._pending_continue_event = None

    def open_menu(self):
        """
        Accessible mid-game; cancels pending transitions and returns to mode picker.
        """
        self._cancel_pending_continue()
        self._reset_game_state(limit=None)

        for btn in self.buttons:
            btn.disabled = True

        if self.sm is not None:
            self.sm.current = "menu"

    def open_settings_screen(self):
        """
        Accessible mid-game; currently resets the game and shows an empty settings screen.
        """
        self._cancel_pending_continue()
        self._reset_game_state(limit=None)

        for btn in self.buttons:
            btn.disabled = True

        if self.sm is not None:
            self.sm.current = "settings"

    def _reset_game_state(self, limit):
        self.game_end = False
        self.answer_received = False

        self.question_no = 0
        self.score = 0

        self.q_version = ""

        if limit is None:
            self.answer_results = []
            self.last_five_results = ["unset"] * self.indefinite_window_size
            self._setup_static_text()
        else:
            self.answer_results = ["unset"] * int(limit)
            self.last_five_results = []
            self.score_label_text = f"Score: 0/{int(limit)}"

        # q_text is set by _setup_static_text for menu; for games it will be replaced on next question.
        if limit is not None:
            self.q_text = ""

    def _setup_scorebox_cells(self, cell_count: int):
        """
        Populate the scorebox grid with `ScoreCell` widgets.
        """
        if not self.scorebox_grid:
            return

        self.scorebox_grid.clear_widgets()
        self.scorebox_grid.cols = int(cell_count)
        self.scorebox_cells = []

        for _ in range(int(cell_count)):
            cell = ScoreCell(status="unset")
            self.scorebox_grid.add_widget(cell)
            self.scorebox_cells.append(cell)
    
    # Retrieve and format question data to display
    def prepare_question(self):
        if DEBUG:
             #print(f"Preparing question {self.question_no} with test data")
             question_data = test_data.get_pkg()
        else:
            #print(f"Preparing question {self.question_no}")
            question_data = get_question()
            if not question_data:
                print("Failed to prepare question.")
                return False
        
        self.q_version = question_data['version']
        self.q_text = question_data['dex_entry']
        choices = question_data['choices']
        for button, choice in zip(self.buttons, choices):
            button.prepare(choice)
        self.correct_answer = question_data['answer']
        self.answer_received = False
        return True

    # Will be called from the answers buttons when clicked by the user
    def receive_answer(self, answer):
        if self.answer_received or self.game_end:
            return
        #print(f"Received answer: {answer}")
        self.answer_received = True
        is_correct = (answer == self.correct_answer)
        if is_correct:
            self.score += 1

        # Update score label.
        if self.current_mode_limit is None:
            self.score_label_text = f"Score: {self.score}"
        else:
            self.score_label_text = f"Score: {self.score}/{int(self.current_mode_limit)}"

        status = "correct" if is_correct else "incorrect"

        # Update scorebox for bounded vs indefinite modes.
        if self.current_mode_limit is None:
            # Slide window of last N answers (indefinite mode).
            self.last_five_results.pop(0)
            self.last_five_results.append(status)
            for i, cell in enumerate(self.scorebox_cells):
                cell.set_status(self.last_five_results[i])
        else:
            # question_no is 1-based; answer_results is 0-based.
            idx = int(self.question_no) - 1
            if 0 <= idx < len(self.answer_results):
                self.answer_results[idx] = status
                if 0 <= idx < len(self.scorebox_cells):
                    self.scorebox_cells[idx].set_status(status)
        
        # Give feedback about correct answer
        self.buttons[answer].show_incorrect()
        self.buttons[self.correct_answer].show_correct()
        self._pending_continue_event = Clock.schedule_once(self.continue_game_loop, 3)
    
    # Main game loop, in progress
    def continue_game_loop(self, dt=0):
        # Bounded modes end after the last answer.
        if self.current_mode_limit is not None and self.question_no >= self.current_mode_limit:
            self.game_end = True
            self.answer_received = True
            for btn in self.buttons:
                btn.disabled = True
            self.q_text = f"Game over! Score: {self.score}/{int(self.current_mode_limit)}"
            self.q_version = ""
            return

        self.question_no += 1
        ok = self.prepare_question()
        if not ok:
            # If fetching/building the question fails, end the game gracefully.
            self.game_end = True
            self.answer_received = True
            for btn in self.buttons:
                btn.disabled = True
            self.q_text = "Failed to prepare question. Game over."
            self.q_version = ""
    
if __name__ == '__main__':
    app = PokeQuizApp()
    app.run()
