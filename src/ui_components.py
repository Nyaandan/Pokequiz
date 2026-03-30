from __future__ import annotations

import math
import random
from pathlib import Path

from kivy.clock import Clock
from kivy.factory import Factory
from kivy.properties import ColorProperty, ListProperty, StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image
from kivy.uix.screenmanager import Screen

base_color = (0.7, 0.7, 0.7, 0.5)
selection_color = (0.8, 0.4, 0, 0.8)
answer_color = (0.1, 0.8, 0.4, 0.8)
incorrect_color = (0.8, 0.1, 0.1, 0.8)
unset_color = (0.7, 0.7, 0.7, 0.2)


class ParticleBackdrop(FloatLayout):
    """
    Full-screen striped background (theme) plus drifting particles.
    particle_variant 'l' or 's' picks assets/bg/particles_*_{l|s}.png.
    Particles move in a random direction per burst, with random idle gaps between bursts.
    """

    particle_variant = StringProperty("l")
    theme = StringProperty("light")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (1, 1)
        self._tick_event = None
        self._sprites: list[dict] = []
        self._started = False
        self._bg_image = Image(fit_mode="fill")
        self._bg_image.size_hint = (1, 1)
        self.add_widget(self._bg_image)
        self._apply_stripes_source()

        self.bind(size=self._try_start_particles)  # type: ignore[attr-defined]

    def on_theme(self, instance, value) -> None:
        self._apply_stripes_source()

    def _apply_stripes_source(self) -> None:
        key = "dark" if self.theme == "dark" else "light"
        base = Path(__file__).resolve().parent.parent / "assets" / "bg"
        stripes = base / f"bg_motif_{key}.png"
        if stripes.is_file():
            self._bg_image.source = str(stripes)
        else:
            legacy = base / "background.png"
            self._bg_image.source = str(legacy) if legacy.is_file() else str(stripes)

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
        configs = [
            (f"{path}{prefix}red{suffix}.png", 38),
            (f"{path}{prefix}red{suffix}.png", 74),
            (f"{path}{prefix}green{suffix}.png", 52),
            (f"{path}{prefix}green{suffix}.png", 91),
            (f"{path}{prefix}blue{suffix}.png", 46),
            (f"{path}{prefix}blue{suffix}.png", 108),
        ]

        for i, (src, speed) in enumerate(configs):
            img = Image(source=src, fit_mode="contain", opacity=0)
            img.size_hint = (None, None)
            self.add_widget(img)
            sprite = {
                "img": img,
                "base_speed": float(speed),
                "vx": 0.0,
                "vy": 0.0,
                "pos": [0.0, 0.0],
                "state": "wait",
                "wait_until": 0.0,
                "_idx": i,
            }
            self._sprites.append(sprite)
            img.bind(texture=lambda inst, tex, sp=sprite: self._on_particle_texture(sp))  # type: ignore[attr-defined]

    def _on_particle_texture(self, sprite: dict) -> None:
        self._apply_particle_size(sprite["img"])
        t0 = Clock.get_boottime()
        sprite["state"] = "wait"
        sprite["wait_until"] = t0 + random.uniform(0, 1.4) + sprite["_idx"] * 0.22
        sprite["img"].opacity = 0

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

    def _begin_move(self, s: dict) -> None:
        img = s["img"]
        if (img.width <= 0 or img.height <= 0) and img.texture:
            self._apply_particle_size(img)
        iw = img.width or 1
        ih = img.height or 1
        w, h = self.width, self.height
        theta = random.uniform(0.0, math.tau)
        sp = s["base_speed"]
        s["vx"] = math.cos(theta) * sp
        s["vy"] = math.sin(theta) * sp
        s["pos"] = [
            random.uniform(-iw * 0.9, w + iw * 0.35),
            random.uniform(-ih * 0.9, h + ih * 0.35),
        ]
        img.pos = (s["pos"][0], s["pos"][1])
        img.opacity = 0.9
        s["state"] = "move"

    def _off_screen(self, s: dict) -> bool:
        x, y = s["pos"]
        img = s["img"]
        iw, ih = img.width, img.height
        w, h = self.width, self.height
        margin = max(iw, ih) * 0.55
        return x > w + margin or x < -iw - margin or y > h + margin or y < -ih - margin

    def _tick(self, dt: float) -> None:
        if not self._sprites or self.width <= 0:
            return
        now = Clock.get_boottime()
        for s in self._sprites:
            img = s["img"]
            if img.width <= 0 or img.height <= 0:
                if img.texture:
                    self._apply_particle_size(img)
                else:
                    continue
            if s["state"] == "wait":
                if now >= s["wait_until"]:
                    self._begin_move(s)
                continue

            x = s["pos"][0] + s["vx"] * dt
            y = s["pos"][1] + s["vy"] * dt
            s["pos"][0] = x
            s["pos"][1] = y
            img.pos = (x, y)
            if self._off_screen(s):
                s["state"] = "wait"
                s["wait_until"] = now + random.uniform(0.7, 3.8)
                img.opacity = 0


Factory.register("ParticleBackdrop", cls=ParticleBackdrop)


class ScoreCell(BoxLayout):
    status = StringProperty("unset")
    cell_color = ListProperty(list(unset_color))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._sync_color(self.status)

    def on_status(self, instance, value):
        self._sync_color(value)

    def set_status(self, status: str):
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


class ShinyButton(Button):
    img_source = StringProperty("assets/test/blank.png")
    option_name = StringProperty("")
    bg_color = ColorProperty((0.7, 0.7, 0.7, 0.5))

    def prepare(self, data: dict):
        self.bg_color = base_color
        self.img_source = data["sprite"]
        self.option_name = data["name"]

    def show_correct(self):
        self.bg_color = answer_color

    def show_incorrect(self):
        self.bg_color = selection_color

