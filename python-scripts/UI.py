"""Tkinter interface for RawSTRaP's API-key and text-parsing workflow."""

from __future__ import annotations

import importlib.util
import os
import queue
import re
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog
from typing import Any, Callable


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PARSER_PATH = Path(__file__).with_name("parser.py")
GRAPHICS_PATH = Path(__file__).with_name("ui_graphics.py")
PROVIDER_PATH = Path(__file__).with_name("providers.py")
TEXT_DOCUMENT_PATTERNS = "*.txt *.md *.rst *.csv *.tsv *.json *.xml *.html *.htm *.yaml *.yml *.toml"
TEXT_DOCUMENT_EXTENSIONS = {
    ".txt", ".md", ".rst", ".csv", ".tsv", ".json", ".xml",
    ".html", ".htm", ".yaml", ".yml", ".toml",
}
_PARSER_MODULE: Any | None = None
_GRAPHICS_MODULE: Any | None = None
_PROVIDER_MODULE: Any | None = None
GOLD = "#efa900"
INK = "#111111"
PANEL = "#b0b0b0"
CANVAS_BACKGROUND = "#eef0f4"


def _load_parser_module() -> Any:
    """Load the sibling parser module once for sanitation and pipeline use."""
    global _PARSER_MODULE
    if _PARSER_MODULE is None:
        spec = importlib.util.spec_from_file_location("rawstrap_ui_parser", PARSER_PATH)
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not load parser module from {PARSER_PATH}")
        _PARSER_MODULE = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_PARSER_MODULE)
    return _PARSER_MODULE


def _load_graphics_module() -> Any:
    """Load the high-resolution artwork helper once."""
    global _GRAPHICS_MODULE
    if _GRAPHICS_MODULE is None:
        spec = importlib.util.spec_from_file_location("rawstrap_ui_graphics", GRAPHICS_PATH)
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not load graphics module from {GRAPHICS_PATH}")
        _GRAPHICS_MODULE = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_GRAPHICS_MODULE)
    return _GRAPHICS_MODULE


def _load_provider_module() -> Any:
    """Load the provider request adapters once."""
    global _PROVIDER_MODULE
    if _PROVIDER_MODULE is None:
        spec = importlib.util.spec_from_file_location("rawstrap_ui_providers", PROVIDER_PATH)
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not load provider module from {PROVIDER_PATH}")
        _PROVIDER_MODULE = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = _PROVIDER_MODULE
        spec.loader.exec_module(_PROVIDER_MODULE)
    return _PROVIDER_MODULE


class RawSTRaPApp:
    """Own the welcome screen and coordinate the parsing pipeline."""

    def __init__(
        self,
        root: tk.Tk,
        provider: str = "",
        api_key: str = "",
        model_id: str = "",
        on_back: Callable[[], None] | None = None,
    ) -> None:
        self.root = root
        self.on_back = on_back
        self.root.title("RawSTRaP")
        self.root.geometry("567x573" if api_key else "520x555")
        self.root.resizable(False, False)
        self.root.configure(bg=CANVAS_BACKGROUND)

        self.provider = provider
        self.api_key = api_key
        self.model_id = model_id
        self.source = ""
        self.prepared_payload = ""
        self._result_queue: queue.Queue[tuple[bool, Any]] = queue.Queue()
        if api_key:
            self._draw_main_screen()
        else:
            self._draw_welcome_screen()

    def _draw_shell(self) -> tk.Canvas:
        self.root.geometry("567x573")
        canvas = tk.Canvas(
            self.root,
            width=567,
            height=573,
            bg=CANVAS_BACKGROUND,
            highlightthickness=0,
        )
        canvas.pack(fill="both", expand=True)
        return canvas

    def _set_art(self, canvas: tk.Canvas, **options: Any) -> int:
        """Render and attach smooth, supersampled screen artwork."""
        image = _load_graphics_module().render_screen(567, 573, **options)
        canvas.art_image = image
        if hasattr(canvas, "art_item"):
            canvas.itemconfigure(canvas.art_item, image=image)
            return canvas.art_item
        canvas.art_item = canvas.create_image(0, 0, image=image, anchor="nw")
        return canvas.art_item

    def _draw_welcome_screen(self) -> None:
        canvas = self._draw_shell()
        canvas.art_image = _load_graphics_module().render_screen(
            567,
            573,
            title="WELCOME!",
            subtitle="Enter an API Key to continue",
            title_y=113,
            subtitle_y=181,
            title_size=35,
            buttons=(
                {"bounds": (172, 402, 407, 449), "label": "Continue", "font_size": 15},
                {"bounds": (221, 464, 346, 503), "label": "Go Back ←", "font_size": 12},
            ),
        )
        canvas.create_image(0, 0, image=canvas.art_image, anchor="nw")

        entry_border = tk.Frame(self.root, bg=GOLD, padx=8, pady=8)
        self.key_entry = tk.Entry(
            entry_border,
            show="•",
            relief="flat",
            bd=0,
            bg=INK,
            fg=GOLD,
            insertbackground=GOLD,
            font=("Segoe UI", 14),
        )
        self.key_entry.pack(fill="both", expand=True)
        canvas.create_window(283, 327, width=350, height=52, window=entry_border)

        art_id = canvas.find_all()[0]
        canvas.tag_bind(art_id, "<Button-1>", self._welcome_art_click)
        self.key_entry.bind("<Return>", lambda _event: self._accept_api_key())
        self.key_entry.focus_set()

    def _welcome_art_click(self, event: tk.Event) -> None:
        if 172 <= event.x <= 407 and 402 <= event.y <= 449:
            self._accept_api_key()
        elif 221 <= event.x <= 346 and 464 <= event.y <= 503:
            self.root.destroy()

    def _accept_api_key(self) -> None:
        key = self.key_entry.get().strip()
        if not key:
            messagebox.showwarning("API key required", "Enter an API key to continue.", parent=self.root)
            self.key_entry.focus_set()
            return

        self.api_key = key
        self._draw_input_screen()

    def _draw_input_screen(self, source: str = "") -> None:
        for child in self.root.winfo_children():
            child.destroy()

        canvas = self._draw_shell()
        process_button = {"bounds": (172, 438, 407, 482), "label": "PROCESS", "font_size": 13}
        back_button = {"bounds": (221, 491, 346, 530), "label": "Go Back ←", "font_size": 12}
        process_art_id = self._set_art(
            canvas,
            title="RawSTRaP",
            subtitle="Paste the text you want to structure",
            title_y=88,
            subtitle_y=145,
            title_size=30,
            buttons=(process_button, back_button),
        )

        text_border = tk.Frame(self.root, bg=GOLD, padx=5, pady=5)
        self.source_text = tk.Text(
            text_border,
            wrap="word",
            relief="flat",
            bd=0,
            bg=INK,
            fg="#f5f5f5",
            insertbackground=GOLD,
            font=("Segoe UI", 11),
            padx=8,
            pady=8,
        )
        self.source_text.pack(fill="both", expand=True)
        canvas.create_window(283, 285, width=350, height=208, window=text_border)

        self.status_label = tk.Label(
            self.root,
            text=f"Selected model: {self.model_id}" if self.provider else "",
            bg=INK,
            fg=GOLD,
            font=("Georgia", 9),
            wraplength=340,
        )
        canvas.create_window(283, 411, width=340, height=34, window=self.status_label)
        if source:
            self.source_text.insert("1.0", source)
        canvas.tag_bind(process_art_id, "<Button-1>", self._process_art_click)
        canvas.tag_bind(process_art_id, "<Motion>", self._process_art_motion)
        self.process_hover = -1
        self.process_button_art = process_button
        self.input_back_button_art = back_button
        self.process_canvas = canvas
        self.processing = False

    def _process_art_click(self, event: tk.Event) -> None:
        if self.processing:
            return
        if 172 <= event.x <= 407 and 438 <= event.y <= 482:
            self._start_pipeline()
        elif 221 <= event.x <= 346 and 491 <= event.y <= 530:
            self.source = self.source_text.get("1.0", "end-1c")
            self._draw_main_screen()

    def _process_art_motion(self, event: tk.Event) -> None:
        if self.processing:
            return
        if 172 <= event.x <= 407 and 438 <= event.y <= 482:
            hover_index = 0
        elif 221 <= event.x <= 346 and 491 <= event.y <= 530:
            hover_index = 1
        else:
            hover_index = -1
        if hover_index == self.process_hover:
            return
        self.process_hover = hover_index
        self.process_button_art["fill"] = "#f6b500" if hover_index == 0 else GOLD
        self.input_back_button_art["fill"] = "#f6b500" if hover_index == 1 else GOLD
        self._set_art(
            self.process_canvas,
            title="RawSTRaP",
            subtitle="Paste the text you want to structure",
            title_y=88,
            subtitle_y=145,
            title_size=30,
            buttons=(self.process_button_art, self.input_back_button_art),
        )

    def _draw_main_screen(self) -> None:
        """Show the post-validation landing page from the supplied reference."""
        for child in self.root.winfo_children():
            child.destroy()

        canvas = self._draw_shell()
        self.landing_button_specs = (
            {"bounds": (172, 292, 407, 338), "label": "Talk it out!", "label_x": 273, "icon": "chat"},
            {"bounds": (172, 350, 407, 397), "label": "Upload file", "label_x": 273, "icon": "file"},
            {"bounds": (221, 490, 346, 529), "label": "Go Back ←", "font_size": 12},
        )
        self.landing_canvas = canvas
        self.landing_hover = -1
        art_id = self._render_landing_art()
        canvas.tag_bind(art_id, "<Button-1>", self._landing_click)
        canvas.tag_bind(art_id, "<Motion>", self._landing_motion)

    def _render_landing_art(self) -> int:
        buttons = []
        for index, button in enumerate(self.landing_button_specs):
            rendered = dict(button)
            if self.landing_hover == index:
                rendered["fill"] = "#f6b500"
            buttons.append(rendered)
        return self._set_art(
            self.landing_canvas,
            title="HORRAY!",
            subtitle="API key verified.",
            title_y=121,
            subtitle_y=190,
            title_size=39,
            buttons=tuple(buttons),
        )

    def _landing_button_at(self, x: int, y: int) -> int:
        for index, button in enumerate(self.landing_button_specs):
            x1, y1, x2, y2 = button["bounds"]
            if x1 <= x <= x2 and y1 <= y <= y2:
                return index
        return -1

    def _landing_click(self, event: tk.Event) -> None:
        index = self._landing_button_at(event.x, event.y)
        if index == 0:
            self._open_text_entry()
        elif index == 1:
            self._upload_text_file()
        elif index == 2:
            self._go_back_to_key_screen()

    def _go_back_to_key_screen(self) -> None:
        if self.on_back is not None:
            self.on_back()
        else:
            self._draw_welcome_screen()

    def _landing_motion(self, event: tk.Event) -> None:
        hover_index = self._landing_button_at(event.x, event.y)
        if hover_index == self.landing_hover:
            return
        self.landing_hover = hover_index
        self._render_landing_art()

    def _open_text_entry(self) -> None:
        """Open the text-entry step after the user chooses Talk it out."""
        self._draw_input_screen(source=self.source)

    def _upload_text_file(self) -> None:
        """Load a UTF-8 text file into the existing text-entry step."""
        selected_file = filedialog.askopenfilename(
            parent=self.root,
            title="Choose a text file",
            filetypes=(("Plain-text documents", TEXT_DOCUMENT_PATTERNS),),
        )
        if not selected_file:
            return
        if Path(selected_file).suffix.lower() not in TEXT_DOCUMENT_EXTENSIONS:
            messagebox.showerror(
                "Unsupported file",
                "Choose a plain-text documentation file.",
                parent=self.root,
            )
            return
        try:
            source = Path(selected_file).read_text(encoding="utf-8-sig")
            if "\x00" in source:
                raise ValueError("Binary files are not supported.")
        except (OSError, UnicodeError) as error:
            messagebox.showerror(
                "Could not open file",
                f"Choose a readable UTF-8 text file.\n\n{error}",
                parent=self.root,
            )
            return
        except ValueError as error:
            messagebox.showerror("Unsupported file", str(error), parent=self.root)
            return

        self.source = _load_parser_module().sanitize_source_text(source)
        self._draw_input_screen(source=self.source)

    def _start_pipeline(self) -> None:
        if self.processing:
            return
        raw_text = self.source_text.get("1.0", "end-1c")
        parser = _load_parser_module()
        source = parser.sanitize_source_text(raw_text)
        if source != raw_text:
            self.source_text.delete("1.0", "end")
            self.source_text.insert("1.0", source)
        if not source:
            self.status_label.config(text="Enter some text before processing.")
            self.source_text.focus_set()
            return

        self.source = source
        if self.provider:
            self.prepared_payload = parser.prepare_provider_payload(source)
            storage = self._ask_storage_options(parser)
            if storage is None:
                return
            database_path, table_name = storage
            provider_label = _load_provider_module().PROVIDERS[self.provider].label
            confirmed_free = messagebox.askyesno(
                "Confirm free API access",
                f"The sanitized source and prompt will be sent to {provider_label} using "
                f"model {self.model_id}. Continue only if you have verified in the "
                "provider console that this key and model are on a free tier and this "
                "request will not incur charges. RawSTRaP cannot verify billing status.",
                parent=self.root,
            )
            if not confirmed_free:
                self.status_label.config(text="No request was sent.")
                return
            if Path(database_path).exists() and not messagebox.askyesno(
                "Database already exists",
                "This database file already exists. Rows will be added to the selected "
                "table; existing rows will not be replaced. Continue?",
                parent=self.root,
            ):
                return

            self.status_label.config(text="Sending payload to the selected provider…")
            self.processing = True
            self._set_process_button_enabled(False)
            threading.Thread(
                target=self._run_provider_pipeline_worker,
                args=(source, self.prepared_payload, database_path, table_name),
                daemon=True,
            ).start()
            self.root.after(100, self._poll_pipeline_result)
            return

        if not os.environ.get("RAWSTRAP_API_URL"):
            self.status_label.config(text="Set RAWSTRAP_API_URL before processing.")
            return

        self.status_label.config(text="Sending text to the API…")
        self.processing = True
        self._set_process_button_enabled(False)
        threading.Thread(
            target=self._run_pipeline_worker,
            args=(source,),
            daemon=True,
        ).start()
        self.root.after(100, self._poll_pipeline_result)

    def _ask_storage_options(self, parser: Any) -> tuple[Path, str] | None:
        """Collect a database filename and table name from GUI dialogs."""
        database_name = simpledialog.askstring(
            "Database name",
            "Name the SQLite database (letters, numbers, spaces, dots, underscores, or hyphens):",
            parent=self.root,
        )
        if database_name is None:
            return None
        database_name = database_name.strip()
        if database_name.lower().endswith(".db"):
            database_name = database_name[:-3]
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 _.-]{0,63}", database_name, flags=re.ASCII):
            messagebox.showerror(
                "Invalid database name",
                "Use 1-64 letters, numbers, spaces, dots, underscores, or hyphens; begin with a letter or number.",
                parent=self.root,
            )
            return None

        table_name = simpledialog.askstring(
            "Table name",
            "Name the table (start with a letter or underscore; use only letters, numbers, and underscores):",
            parent=self.root,
        )
        if table_name is None:
            return None
        table_name = table_name.strip()
        try:
            parser.validate_table_name(table_name)
        except ValueError as error:
            messagebox.showerror("Invalid table name", str(error), parent=self.root)
            return None
        return PROJECT_ROOT / f"{database_name}.db", table_name

    def _run_provider_pipeline_worker(
        self,
        source: str,
        payload: str,
        database_path: Path,
        table_name: str,
    ) -> None:
        try:
            csv_response = _load_provider_module().generate_csv(
                self.provider, self.api_key, self.model_id, payload
            )
            result = _load_parser_module().save_provider_csv(
                source,
                csv_response,
                database_path=database_path,
                table_name=table_name,
            )
            result["database_path"] = database_path
            result["table_name"] = table_name
            self._result_queue.put((True, result))
        except Exception as error:
            self._result_queue.put((False, str(error)))

    def _run_pipeline_worker(self, source_text: str) -> None:
        try:
            result = _load_parser_module().run_pipeline(source_text, api_key=self.api_key)
            self._result_queue.put((True, result))
        except Exception as error:
            self._result_queue.put((False, str(error)))

    def _poll_pipeline_result(self) -> None:
        try:
            succeeded, result = self._result_queue.get_nowait()
        except queue.Empty:
            self.root.after(100, self._poll_pipeline_result)
            return

        self.processing = False
        self._set_process_button_enabled(True)
        if not succeeded:
            self.status_label.config(text=f"Could not process text: {result}")
            return

        self.status_label.config(
            text=(
                f"Saved {result['record_count']} row(s) to {result['table_name']} "
                f"in {Path(result['database_path']).name}."
                if "database_path" in result
                else f"Saved {result['record_count']} row(s). CSV: {Path(result['csv_path']).name}"
            )
        )
        self._draw_success_screen(Path(result["csv_path"]))

    def _draw_success_screen(self, csv_path: Path) -> None:
        """Show the completed-processing screen and retain its output for preview."""
        for child in self.root.winfo_children():
            child.destroy()

        self.result_csv_path = csv_path
        canvas = self._draw_shell()
        self.success_button_specs = (
            {"bounds": (172, 330, 407, 375), "label": "Preview File", "font_size": 16},
            {"bounds": (172, 384, 407, 429), "label": "Open File Location", "font_size": 14},
            {"bounds": (221, 440, 346, 480), "label": "Go Back ←", "font_size": 12},
        )
        self.success_hover = -1
        art_id = self._render_success_art(canvas)
        canvas.tag_bind(art_id, "<Button-1>", self._success_art_click)
        canvas.tag_bind(art_id, "<Motion>", self._success_art_motion)
        self.success_canvas = canvas

    def _render_success_art(self, canvas: tk.Canvas) -> int:
        buttons = []
        for index, button in enumerate(self.success_button_specs):
            rendered = dict(button)
            if self.success_hover == index:
                rendered["fill"] = "#f6b500"
            buttons.append(rendered)
        return self._set_art(
            canvas,
            title="WELL DONE!",
            subtitle="Shall we see the results?",
            title_y=157,
            subtitle_y=311,
            title_size=39,
            buttons=tuple(buttons),
        )

    def _success_button_at(self, x: int, y: int) -> int:
        for index, button in enumerate(self.success_button_specs):
            x1, y1, x2, y2 = button["bounds"]
            if x1 <= x <= x2 and y1 <= y <= y2:
                return index
        return -1

    def _success_art_click(self, event: tk.Event) -> None:
        index = self._success_button_at(event.x, event.y)
        if index == 0:
            self._preview_result_file()
        elif index == 1:
            self._open_result_location()
        elif index == 2:
            self._draw_input_screen(source=self.source)

    def _success_art_motion(self, event: tk.Event) -> None:
        hover_index = self._success_button_at(event.x, event.y)
        if hover_index == self.success_hover:
            return
        self.success_hover = hover_index
        self._render_success_art(self.success_canvas)

    def _preview_result_file(self) -> None:
        """Display the generated CSV in a read-only window."""
        try:
            content = self.result_csv_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            messagebox.showerror(
                "Could not preview file",
                f"The result file could not be read.\n\n{error}",
                parent=self.root,
            )
            return

        preview = tk.Toplevel(self.root)
        preview.title(f"Preview: {self.result_csv_path.name}")
        preview.geometry("720x500")
        preview.configure(bg=INK)
        text = tk.Text(
            preview,
            wrap="none",
            bg=INK,
            fg="#f5f5f5",
            insertbackground=GOLD,
            font=("Consolas", 10),
            padx=12,
            pady=12,
        )
        vertical = tk.Scrollbar(preview, orient="vertical", command=text.yview)
        horizontal = tk.Scrollbar(preview, orient="horizontal", command=text.xview)
        text.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        text.grid(row=0, column=0, sticky="nsew")
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal.grid(row=1, column=0, sticky="ew")
        preview.grid_rowconfigure(0, weight=1)
        preview.grid_columnconfigure(0, weight=1)
        text.insert("1.0", content)
        text.configure(state="disabled")

    def _open_result_location(self) -> None:
        """Reveal the generated CSV in the operating system's file browser."""
        try:
            if not self.result_csv_path.is_file():
                raise FileNotFoundError(f"Result file not found: {self.result_csv_path}")
            if sys.platform == "win32":
                subprocess.Popen(["explorer", "/select,", str(self.result_csv_path)])
            elif sys.platform == "darwin":
                subprocess.Popen(["open", "-R", str(self.result_csv_path)])
            else:
                subprocess.Popen(["xdg-open", str(self.result_csv_path.parent)])
        except OSError as error:
            messagebox.showerror(
                "Could not open file location",
                f"The result folder could not be opened.\n\n{error}",
                parent=self.root,
            )

    def _set_process_button_enabled(self, enabled: bool) -> None:
        """Prevent duplicate submissions while the background request runs."""
        self.process_button_art["fill"] = GOLD if enabled else "#b67f00"
        self._set_art(
            self.process_canvas,
            title="RawSTRaP",
            subtitle="Paste the text you want to structure",
            title_y=88,
            subtitle_y=145,
            title_size=30,
            buttons=(self.process_button_art, self.input_back_button_art),
        )


def launch(provider: str = "", api_key: str = "", model_id: str = "") -> None:
    """Open the application, optionally with a validated provider session."""
    root = tk.Tk()
    RawSTRaPApp(root, provider=provider, api_key=api_key, model_id=model_id)
    root.mainloop()


if __name__ == "__main__":
    launch()
