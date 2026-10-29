"""Root launcher: welcome → provider → key validation → main UI."""

from __future__ import annotations

import importlib.util
import queue
import sys
import threading
import tkinter as tk
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
PROVIDER_MODULE_PATH = ROOT / "python-scripts" / "providers.py"
UI_MODULE_PATH = ROOT / "python-scripts" / "UI.py"
GRAPHICS_MODULE_PATH = ROOT / "python-scripts" / "ui_graphics.py"
GOLD = "#e3a004"
INK = "#111111"
PANEL = "#b0b0b0"
BACKGROUND = "#121212"
PROVIDER_OPTIONS = (
	("Google Gemini", "gemini"),
	("OpenAI", "openai"),
	("xAI", "xai"),
	("Anthropic Claude", "anthropic"),
	("Groq-hosted Llama", "groq"),
)


def _load_module(module_name: str, module_path: Path) -> Any:
	spec = importlib.util.spec_from_file_location(module_name, module_path)
	if spec is None or spec.loader is None:
		raise ImportError(f"Could not load module from {module_path}")
	module = importlib.util.module_from_spec(spec)
	sys.modules[module_name] = module
	spec.loader.exec_module(module)
	return module


def _draw_screen_art(
	canvas: tk.Canvas,
	*,
	title: str,
	subtitle: str,
	buttons: tuple[dict[str, Any], ...] = (),
	title_y: int = 113,
	subtitle_y: int = 181,
	title_size: int = 35,
) -> int:
	"""Render screen decoration and text at high resolution, then downsample."""
	graphics = _load_module("rawstrap_ui_graphics", GRAPHICS_MODULE_PATH)
	image = graphics.render_screen(
		520, 555, title=title, subtitle=subtitle, buttons=buttons,
		title_y=title_y, subtitle_y=subtitle_y, title_size=title_size,
	)
	canvas.art_image = image
	return canvas.create_image(0, 0, image=image, anchor="nw")


class WelcomeFlow:
	"""Display welcome/provider/key screens and verify credentials once."""

	def __init__(self, root: tk.Tk) -> None:
		self.root = root
		self.root.title("RawSTRaP")
		self.root.geometry("520x555")
		self.root.resizable(False, False)
		self.root.configure(bg=BACKGROUND)
		self.provider = ""
		self.api_key = ""
		self._results: queue.Queue[tuple[bool, Any]] = queue.Queue()
		self._draw_welcome_screen()

	def _draw_shell(self) -> tk.Canvas:
		canvas = tk.Canvas(
			self.root, width=520, height=555, bg=BACKGROUND, highlightthickness=0
		)
		canvas.pack(fill="both", expand=True)
		return canvas

	def _draw_welcome_screen(self) -> None:
		self.root.geometry("520x555")
		for child in self.root.winfo_children():
			child.destroy()
		canvas = self._draw_shell()
		art_id = _draw_screen_art(
			canvas,
			title="WELCOME!",
			subtitle="Choose an API provider to continue",
			buttons=(
				{"bounds": (145, 402, 362, 445), "label": "Continue", "font_size": 15},
				{"bounds": (203, 462, 317, 502), "label": "Exit", "font_size": 12},
			),
		)

		select_border = tk.Frame(self.root, bg=GOLD, padx=8, pady=8)
		selected_label = next(
			(label for label, provider_id in PROVIDER_OPTIONS if provider_id == self.provider),
			PROVIDER_OPTIONS[0][0],
		)
		self.provider_var = tk.StringVar(value=selected_label)
		self.provider_menu = tk.OptionMenu(
			select_border,
			self.provider_var,
			*(label for label, _provider_id in PROVIDER_OPTIONS),
		)
		self.provider_menu.config(
			bg=INK, fg=GOLD, activebackground="#252525", activeforeground=GOLD,
			bd=0, highlightthickness=0, anchor="center", font=("Segoe UI", 12),
		)
		self.provider_menu["menu"].config(bg=INK, fg=GOLD, activebackground=GOLD, activeforeground=INK)
		self.provider_menu.pack(fill="both", expand=True)
		canvas.create_window(254, 327, width=341, height=52, window=select_border)

		canvas.tag_bind(art_id, "<Button-1>", self._welcome_art_click)
		canvas.tag_bind(art_id, "<Motion>", self._welcome_art_motion)
		self.provider_menu.bind("<Return>", lambda _event: self._select_provider())
		self.welcome_canvas = canvas
		self.welcome_art_id = art_id
		self.welcome_hover = -1

	def _welcome_art_click(self, event: tk.Event) -> None:
		if 145 <= event.x <= 362 and 402 <= event.y <= 445:
			self._select_provider()
		elif 203 <= event.x <= 317 and 462 <= event.y <= 502:
			self.root.destroy()

	def _welcome_art_motion(self, event: tk.Event) -> None:
		if 145 <= event.x <= 362 and 402 <= event.y <= 445:
			hover_index = 0
		elif 203 <= event.x <= 317 and 462 <= event.y <= 502:
			hover_index = 1
		else:
			hover_index = -1
		if hover_index == self.welcome_hover:
			return
		self.welcome_hover = hover_index
		image = _load_module("rawstrap_ui_graphics", GRAPHICS_MODULE_PATH).render_screen(
			520, 555,
			title="WELCOME!",
			subtitle="Choose an API provider to continue",
			buttons=(
				{"bounds": (145, 402, 362, 445), "label": "Continue", "font_size": 15,
				 "fill": "#f6b500" if hover_index == 0 else GOLD},
				{"bounds": (203, 462, 317, 502), "label": "Exit", "font_size": 12,
				 "fill": "#f6b500" if hover_index == 1 else GOLD},
			),
			title_y=113, subtitle_y=181, title_size=35,
		)
		self.welcome_canvas.art_image = image
		self.welcome_canvas.itemconfigure(self.welcome_art_id, image=image)

	def _select_provider(self) -> None:
		label = self.provider_var.get()
		self.provider = next(
			(provider_id for option_label, provider_id in PROVIDER_OPTIONS if option_label == label),
			"",
		)
		if not self.provider:
			return
		self._draw_key_screen(label)

	def _draw_key_screen(self, provider_label: str, api_key: str = "") -> None:
		self.root.geometry("520x555")
		for child in self.root.winfo_children():
			child.destroy()
		canvas = self._draw_shell()
		art_id = _draw_screen_art(
			canvas,
			title="API KEY",
			subtitle=f"Enter your {provider_label} key to continue",
			buttons=(
				{"bounds": (145, 415, 362, 458), "label": "Continue", "font_size": 15},
				{"bounds": (203, 468, 317, 507), "label": "Go Back ←", "font_size": 12},
			),
			title_size=32,
		)

		entry_border = tk.Frame(self.root, bg=GOLD, padx=8, pady=8)
		self.key_entry = tk.Entry(
			entry_border, show="•", relief="flat", bd=0, bg=INK,
			fg=GOLD, insertbackground=GOLD, font=("Segoe UI", 14),
		)
		self.key_entry.pack(fill="both", expand=True)
		if api_key:
			self.key_entry.insert(0, api_key)
		canvas.create_window(254, 327, width=341, height=52, window=entry_border)

		self.status_label = tk.Label(
			self.root, text="One non-generative model-list request will verify the key.",
			bg=INK, fg=GOLD, font=("Georgia", 9), wraplength=335,
		)
		canvas.create_window(254, 373, width=340, height=34, window=self.status_label)
		canvas.tag_bind(art_id, "<Button-1>", self._key_art_click)
		self.key_entry.bind("<Return>", lambda _event: self._validate_key())
		self.key_entry.focus_set()
		self.validation_canvas = canvas
		self.validation_button = art_id
		self.validating = False

	def _key_art_click(self, event: tk.Event) -> None:
		if 145 <= event.x <= 362 and 415 <= event.y <= 458:
			self._validate_key()
		elif 203 <= event.x <= 317 and 468 <= event.y <= 507:
			self._draw_welcome_screen()

	def _validate_key(self) -> None:
		if self.validating:
			return
		api_key = self.key_entry.get().strip()
		if not api_key:
			self.status_label.config(text="Enter an API key to continue.")
			self.key_entry.focus_set()
			return

		self.validating = True
		self.validation_canvas.itemconfigure(self.validation_button, state="disabled")
		self.status_label.config(text="Checking the key… no prompt or source text is sent.")
		threading.Thread(
			target=self._validate_worker, args=(self.provider, api_key), daemon=True
		).start()
		self.root.after(100, self._poll_validation)

	def _validate_worker(self, provider: str, api_key: str) -> None:
		try:
			providers = _load_module("rawstrap_providers", PROVIDER_MODULE_PATH)
			model_count, model_id = providers.validate_api_key(
				provider, api_key, include_model=True
			)
			self._results.put((True, (provider, api_key, model_count, model_id)))
		except Exception as error:
			self._results.put((False, str(error)))

	def _poll_validation(self) -> None:
		try:
			succeeded, result = self._results.get_nowait()
		except queue.Empty:
			self.root.after(100, self._poll_validation)
			return

		self.validating = False
		self.validation_canvas.itemconfigure(self.validation_button, state="normal")
		if not succeeded:
			self.status_label.config(text=result)
			return

		provider, api_key, model_count, model_id = result
		self.status_label.config(
			text=f"Key verified. {model_count} model(s) available; selected {model_id}."
		)
		self.root.after(250, lambda: self._open_ui(provider, api_key, model_id))

	def _open_ui(self, provider: str, api_key: str, model_id: str) -> None:
		self.api_key = api_key
		ui_module = _load_module("rawstrap_main_ui", UI_MODULE_PATH)
		self.ui_app = ui_module.RawSTRaPApp(
			self.root,
			provider=provider,
			api_key=api_key,
			model_id=model_id,
			on_back=self._return_to_key_screen,
		)

	def _return_to_key_screen(self) -> None:
		provider_label = next(
			(label for label, provider_id in PROVIDER_OPTIONS if provider_id == self.provider),
			"API provider",
		)
		self._draw_key_screen(provider_label, api_key=self.api_key)


def main() -> None:
	root = tk.Tk()
	WelcomeFlow(root)
	root.mainloop()


if __name__ == "__main__":
	main()
