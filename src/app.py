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
    for base in _font_search_dirs():
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
    sitka_semibold = _first_sitka_semibold()
    arial = _first_font("arial.ttf", "ARIAL.TTF", "Arial.ttf")
    chosen = sitka_semibold or arial
    if chosen is None:
        return
    path = str(chosen.resolve())
    from kivy.config import Config

    Config.set("kivy", "default_font", ["PokeQuizUI", path, path, path, path])


_apply_default_ui_font()

from kivy.app import App
from kivy.clock import Clock
from kivy.properties import ListProperty, NumericProperty, StringProperty
from kivy.uix.screenmanager import ScreenManager

from src import test_data, user_settings
from src.data_collector import get_question
from src.ui_components import GameScreen, MenuScreen, ScoreCell, SettingsScreen

DEBUG = True


class PokeQuizApp(App):
    question_no = NumericProperty(0)
    score = NumericProperty(0)
    q_text = StringProperty(test_data.q_text)
    q_version = StringProperty(test_data.q_version)
    buttons = ListProperty([])
    score_label_text = StringProperty("")

    ui_theme = StringProperty("light")
    theme_card_rgba = ListProperty([1.0, 1.0, 1.0, 1.0])
    theme_settings_panel_rgba = ListProperty([1.0, 1.0, 1.0, 0.96])
    theme_tab_bg_rgba = ListProperty([0.98, 0.98, 0.99, 1.0])
    theme_text_main = ListProperty([0.12, 0.12, 0.15, 1.0])
    theme_text_question = ListProperty([0.1, 0.1, 0.12, 1.0])
    theme_muted = ListProperty([0.4, 0.4, 0.45, 1.0])

    current_mode_limit = None
    indefinite_window_size = 5
    answer_received = False
    correct_answer: int
    game_end = False
    scorebox_cells = []
    scorebox_grid = None
    game_screen_ref = None
    sm = None
    _pending_continue_event = None
    answer_results = []
    last_five_results = []

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._settings_applying = False
        self._settings_spinners_bound = False
        self._setup_static_text()
        self._apply_theme_colors_only()

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
            btn.disabled = True
            self.buttons.append(btn)

        self.current_mode_limit = None
        self._reset_game_state(limit=None)
        self._setup_scorebox_cells(cell_count=self.indefinite_window_size)
        sm.current = "menu"
        self._apply_theme_to_backdrops()
        return sm

    def _apply_theme_colors_only(self) -> None:
        t = user_settings.get_theme()
        self.ui_theme = t
        if t == "dark":
            self.theme_card_rgba = [0.16, 0.17, 0.22, 0.94]
            self.theme_settings_panel_rgba = [0.14, 0.15, 0.18, 0.96]
            self.theme_tab_bg_rgba = [0.2, 0.21, 0.26, 1.0]
            self.theme_text_main = [0.92, 0.93, 0.96, 1.0]
            self.theme_text_question = [0.95, 0.96, 0.98, 1.0]
            self.theme_muted = [0.65, 0.66, 0.72, 1.0]
        else:
            self.theme_card_rgba = [1.0, 1.0, 1.0, 1.0]
            self.theme_settings_panel_rgba = [1.0, 1.0, 1.0, 0.96]
            self.theme_tab_bg_rgba = [0.98, 0.98, 0.99, 1.0]
            self.theme_text_main = [0.12, 0.12, 0.15, 1.0]
            self.theme_text_question = [0.1, 0.1, 0.12, 1.0]
            self.theme_muted = [0.4, 0.4, 0.45, 1.0]

    def _apply_theme_to_backdrops(self) -> None:
        if self.sm is None:
            return
        t = user_settings.get_theme()
        for name in ("menu", "game", "settings"):
            scr = self.sm.get_screen(name)
            bd = scr.ids.get("particle_backdrop")
            if bd is not None:
                bd.theme = t

    def _sync_ui_theme_from_settings(self) -> None:
        self._apply_theme_colors_only()
        self._apply_theme_to_backdrops()

    def _setup_static_text(self):
        self.q_text = "Select a mode to start."
        self.q_version = ""
        self.score_label_text = "Score: 0"

    def set_mode(self, mode: str):
        if mode == "endless":
            self._switch_to_new_game(limit=None)
        else:
            self._switch_to_new_game(limit=int(mode))

    def _switch_to_new_game(self, limit):
        self._cancel_pending_continue()
        self.current_mode_limit = limit
        self._reset_game_state(limit=limit)
        self._setup_scorebox_cells(
            cell_count=(self.indefinite_window_size if limit is None else int(limit))
        )
        for btn in self.buttons:
            btn.disabled = False
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
        self._cancel_pending_continue()
        self._reset_game_state(limit=None)
        for btn in self.buttons:
            btn.disabled = True
        if self.sm is not None:
            self.sm.current = "menu"

    def open_settings_screen(self):
        self._cancel_pending_continue()
        self._reset_game_state(limit=None)
        for btn in self.buttons:
            btn.disabled = True
        if self.sm is not None:
            self.sm.current = "settings"
        Clock.schedule_once(lambda dt: self.refresh_settings_ui(), 0)

    def refresh_settings_ui(self):
        if self.sm is None:
            return
        ids = self.sm.get_screen("settings").ids
        self._bind_settings_spinners_once(ids)
        self._apply_sprite_spinner(ids)
        self._apply_locale_spinner(ids)
        self._apply_theme_spinner(ids)

    def _bind_settings_spinners_once(self, ids):
        if self._settings_spinners_bound:
            return
        ids.sprite_spinner.bind(text=self._on_sprite_spinner_text)
        ids.locale_spinner.bind(text=self._on_locale_spinner_text)
        ids.theme_spinner.bind(text=self._on_theme_spinner_text)
        self._settings_spinners_bound = True

    def _apply_sprite_spinner(self, ids):
        opts = user_settings.SPRITE_OPTIONS
        self._settings_applying = True
        ids.sprite_spinner.values = [o[0] for o in opts]
        cur = user_settings.get_sprites_variant()
        ids.sprite_spinner.text = next((o[0] for o in opts if o[1] == cur), opts[0][0])
        self._settings_applying = False

    def _apply_locale_spinner(self, ids):
        opts = user_settings.LOCALE_OPTIONS
        self._settings_applying = True
        ids.locale_spinner.values = [o[0] for o in opts]
        code = user_settings.get_locale()
        ids.locale_spinner.text = next((o[0] for o in opts if o[1] == code), opts[0][0])
        self._settings_applying = False

    def _apply_theme_spinner(self, ids):
        opts = user_settings.THEME_OPTIONS
        self._settings_applying = True
        ids.theme_spinner.values = [o[0] for o in opts]
        cur = user_settings.get_theme()
        ids.theme_spinner.text = next((o[0] for o in opts if o[1] == cur), opts[0][0])
        self._settings_applying = False

    def _on_sprite_spinner_text(self, spinner, text):
        if self._settings_applying or not text:
            return
        for lbl, code in user_settings.SPRITE_OPTIONS:
            if lbl == text:
                user_settings.set_sprites_variant(code)
                return

    def _on_locale_spinner_text(self, spinner, text):
        if self._settings_applying or not text:
            return
        for lbl, code in user_settings.LOCALE_OPTIONS:
            if lbl == text:
                user_settings.set_locale(code)
                return

    def _on_theme_spinner_text(self, spinner, text):
        if self._settings_applying or not text:
            return
        for lbl, code in user_settings.THEME_OPTIONS:
            if lbl == text:
                if code != user_settings.get_theme():
                    user_settings.set_theme(code)
                    self._sync_ui_theme_from_settings()
                return

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
        if limit is not None:
            self.q_text = ""

    def _setup_scorebox_cells(self, cell_count: int):
        if not self.scorebox_grid:
            return
        self.scorebox_grid.clear_widgets()
        self.scorebox_grid.cols = int(cell_count)
        self.scorebox_cells = []
        for _ in range(int(cell_count)):
            cell = ScoreCell(status="unset")
            self.scorebox_grid.add_widget(cell)
            self.scorebox_cells.append(cell)

    def prepare_question(self):
        if DEBUG:
            question_data = test_data.get_pkg()
        else:
            question_data = get_question()
            if not question_data:
                print("Failed to prepare question.")
                return False
        self.q_version = question_data["version"]
        self.q_text = question_data["dex_entry"]
        choices = question_data["choices"]
        for button, choice in zip(self.buttons, choices):
            button.prepare(choice)
        self.correct_answer = question_data["answer"]
        self.answer_received = False
        return True

    def receive_answer(self, answer):
        if self.answer_received or self.game_end:
            return
        self.answer_received = True
        is_correct = answer == self.correct_answer
        if is_correct:
            self.score += 1
        if self.current_mode_limit is None:
            self.score_label_text = f"Score: {self.score}"
        else:
            self.score_label_text = f"Score: {self.score}/{int(self.current_mode_limit)}"
        status = "correct" if is_correct else "incorrect"
        if self.current_mode_limit is None:
            self.last_five_results.pop(0)
            self.last_five_results.append(status)
            for i, cell in enumerate(self.scorebox_cells):
                cell.set_status(self.last_five_results[i])
        else:
            idx = int(self.question_no) - 1
            if 0 <= idx < len(self.answer_results):
                self.answer_results[idx] = status
                if 0 <= idx < len(self.scorebox_cells):
                    self.scorebox_cells[idx].set_status(status)
        self.buttons[answer].show_incorrect()
        self.buttons[self.correct_answer].show_correct()
        self._pending_continue_event = Clock.schedule_once(self.continue_game_loop, 3)

    def continue_game_loop(self, dt=0):
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
            self.game_end = True
            self.answer_received = True
            for btn in self.buttons:
                btn.disabled = True
            self.q_text = "Failed to prepare question. Game over."
            self.q_version = ""
            return

