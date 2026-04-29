import customtkinter as ctk
import json
import os
import uuid
from datetime import datetime
from tkinter import filedialog, messagebox
import time
from functools import wraps

# --- НАСТРОЙКИ ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

DATA_FILE = "notes_data.json"


class NoteManager:
    """Управление данными заметок"""

    def __init__(self):
        self.notes = []
        self.load()

    def load(self):
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    self.notes = json.load(f)
            except Exception:
                self.notes = []
        else:
            self.notes = []

    def save(self):
        try:
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(self.notes, f, ensure_ascii=False, indent=4)
        except Exception:
            pass

    def create_note(self, title="Новая заметка"):
        new_note = {
            "id": str(uuid.uuid4()),
            "title": title,
            "content": "",
            "is_favorite": False,
            "is_archived": False,
            "is_deleted": False,
            "created_at": datetime.now().strftime("%d.%m.%Y %H:%M"),
            "updated_at": datetime.now().strftime("%d.%m.%Y %H:%M")
        }
        self.notes.append(new_note)
        self.save()
        return new_note

    def update_note(self, note_id, **kwargs):
        for note in self.notes:
            if note["id"] == note_id:
                note.update(kwargs)
                note["updated_at"] = datetime.now().strftime("%d.%m.%Y %H:%M")
                self.save()
                return note
        return None

    def get_notes(self, filter_type="all", search_query=""):
        filtered = []
        for note in self.notes:
            match = False
            if filter_type == "all" and not note["is_deleted"] and not note["is_archived"]:
                match = True
            elif filter_type == "favorite" and note["is_favorite"] and not note["is_deleted"]:
                match = True
            elif filter_type == "archive" and note["is_archived"] and not note["is_deleted"]:
                match = True
            elif filter_type == "trash" and note["is_deleted"]:
                match = True

            if match and search_query:
                if search_query.lower() not in note["title"].lower() and search_query.lower() not in note[
                    "content"].lower():
                    match = False

            if match:
                filtered.append(note)

        return sorted(filtered, key=lambda x: x["updated_at"], reverse=True)

    def import_markdown(self, filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            lines = content.split("\n")
            title = os.path.basename(filepath).replace(".md", "").replace(".txt", "")

            if lines and lines[0].startswith("#"):
                title = lines[0].lstrip("#").strip()
                content = "\n".join(lines[1:])

            new_note = {
                "id": str(uuid.uuid4()),
                "title": title,
                "content": content,
                "is_favorite": False,
                "is_archived": False,
                "is_deleted": False,
                "created_at": datetime.now().strftime("%d.%m.%Y %H:%M"),
                "updated_at": datetime.now().strftime("%d.%m.%Y %H:%M")
            }
            self.notes.append(new_note)
            self.save()
            return new_note
        except Exception:
            return None


class NoteCard(ctk.CTkFrame):
    """Карточка заметки в списке"""

    def __init__(self, parent, note_data, on_select, on_toggle_fav):
        super().__init__(parent, fg_color="transparent")
        self.note_data = note_data
        self.on_select = on_select
        self.on_toggle_fav = on_toggle_fav

        self.grid_columnconfigure(0, weight=1)

        self.card = ctk.CTkFrame(self, corner_radius=8, fg_color="#2b2b2b")
        self.card.grid(row=0, column=0, sticky="ew", pady=4, padx=5)
        self.card.grid_columnconfigure(0, weight=1)

        self.top_frame = ctk.CTkFrame(self.card, fg_color="transparent")
        self.top_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(8, 2))

        self.title_lbl = ctk.CTkLabel(self.top_frame, text=note_data["title"],
                                      font=ctk.CTkFont(weight="bold", size=13), anchor="w")
        self.title_lbl.pack(side="left", fill="x", expand=True)

        self.star_btn = ctk.CTkButton(self.top_frame, text="★" if note_data["is_favorite"] else "☆",
                                      width=28, height=28, fg_color="transparent",
                                      hover_color="#3a3a3a",
                                      text_color="#ffd700" if note_data["is_favorite"] else "gray",
                                      command=lambda: self.safe_toggle_fav())
        self.star_btn.pack(side="right")

        preview = note_data["content"][:60].replace("\n", " ")
        if len(note_data["content"]) > 60:
            preview += "..."

        self.preview_lbl = ctk.CTkLabel(self.card, text=preview, font=ctk.CTkFont(size=11),
                                        text_color="gray", anchor="w", justify="left")
        self.preview_lbl.grid(row=1, column=0, sticky="w", padx=10, pady=(0, 4))

        self.date_lbl = ctk.CTkLabel(self.card, text=note_data["updated_at"],
                                     font=ctk.CTkFont(size=10), text_color="gray", anchor="w")
        self.date_lbl.grid(row=2, column=0, sticky="w", padx=10, pady=(0, 8))

        # Безопасное绑定 событий
        for widget in [self.card, self.title_lbl, self.preview_lbl, self.date_lbl]:
            widget.bind("<Button-1>", lambda e: self.safe_select())

    def safe_select(self):
        try:
            self.on_select(self.note_data)
        except Exception:
            pass

    def safe_toggle_fav(self):
        try:
            self.on_toggle_fav(self.note_data["id"])
        except Exception:
            pass


class ExportDialog(ctk.CTkToplevel):
    """Диалог экспорта"""

    def __init__(self, parent, callback):
        super().__init__(parent)
        self.title("Экспорт в Markdown")
        self.geometry("350x250")
        self.resizable(False, False)
        self.callback = callback
        self.grab_set()
        self.transient(parent)

        # Обработка закрытия окна
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        ctk.CTkLabel(self, text="Настройки экспорта", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=15)

        self.inc_title = ctk.BooleanVar(value=True)
        self.inc_meta = ctk.BooleanVar(value=True)

        ctk.CTkCheckBox(self, text="Включить заголовок (#)", variable=self.inc_title).pack(pady=5)
        ctk.CTkCheckBox(self, text="Включить мета-данные", variable=self.inc_meta).pack(pady=5)

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=20)

        ctk.CTkButton(btn_frame, text="Отмена", width=100, command=self.destroy, fg_color="gray").pack(side="left",
                                                                                                       padx=10)
        ctk.CTkButton(btn_frame, text="Экспорт", width=100,
                      command=self.safe_confirm).pack(side="right", padx=10)

    def safe_confirm(self):
        try:
            self.callback(self.inc_title.get(), self.inc_meta.get())
        except Exception:
            pass
        finally:
            self.destroy()


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Pro Notes")
        self.geometry("1200x700")
        self.minsize(900, 600)

        # Обработка закрытия приложения
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.manager = NoteManager()
        self.current_filter = "all"
        self.current_note_id = None

        # Настройка сетки
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=2)
        self.grid_rowconfigure(0, weight=1)

        self._create_sidebar()
        self._create_list_panel()
        self._create_editor_panel()

        self.refresh_list()

    def on_closing(self):
        try:
            self.manager.save()
        except Exception:
            pass
        self.destroy()

    def _create_sidebar(self):
        """Левая панель навигации"""
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(6, weight=1)

        ctk.CTkLabel(self.sidebar, text="✎ Pro Notes", font=ctk.CTkFont(size=20, weight="bold")).grid(row=0, column=0,
                                                                                                      padx=20, pady=20)

        nav_items = [("📄 Все", "all"), ("★ Избранное", "favorite"), ("📦 Архив", "archive"), ("🗑️ Корзина", "trash")]
        self.nav_btns = {}

        for i, (text, f_type) in enumerate(nav_items):
            btn = ctk.CTkButton(self.sidebar, text=text, anchor="w",
                                command=lambda t=f_type: self.safe_set_filter(t),
                                fg_color="transparent", hover_color="#3a3a3a")
            btn.grid(row=i + 1, column=0, padx=10, pady=4, sticky="ew")
            self.nav_btns[f_type] = btn

        self.set_filter("all")

        ctk.CTkButton(self.sidebar, text="+ Новая", height=40, command=self.safe_create_new_note,
                      fg_color="#1f6feb", hover_color="#1555b0").grid(row=7, column=0, padx=20, pady=10)

        ctk.CTkButton(self.sidebar, text="📥 Импорт .md", height=35, command=self.safe_import_markdown,
                      fg_color="transparent", border_width=1, border_color="gray").grid(row=8, column=0, padx=20,
                                                                                        pady=5)

        self.theme_switch = ctk.CTkSwitch(self.sidebar, text="Тема", command=self.safe_toggle_theme)
        self.theme_switch.grid(row=9, column=0, padx=20, pady=20)

    def _create_list_panel(self):
        """Центральная панель со списком"""
        self.list_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="#2b2b2b")
        self.list_frame.grid(row=0, column=1, sticky="nsew")
        self.list_frame.grid_columnconfigure(0, weight=1)
        self.list_frame.grid_rowconfigure(1, weight=1)

        self.search_entry = ctk.CTkEntry(self.list_frame, placeholder_text="🔍 Поиск...", height=40)
        self.search_entry.grid(row=0, column=0, padx=15, pady=15, sticky="ew")
        # Используем keyrelease для поиска
        self.search_entry.bind("<KeyRelease>", lambda e: self.safe_refresh_list())

        self.scroll_frame = ctk.CTkScrollableFrame(self.list_frame, label_text="Заметки")
        self.scroll_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        self.scroll_frame.grid_columnconfigure(0, weight=1)

    def _create_editor_panel(self):
        """Правая панель редактора"""
        self.editor_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="#1a1a1a")
        self.editor_frame.grid(row=0, column=2, sticky="nsew")
        self.editor_frame.grid_columnconfigure(0, weight=1)
        self.editor_frame.grid_rowconfigure(2, weight=1)

        toolbar = ctk.CTkFrame(self.editor_frame, fg_color="transparent", height=50)
        toolbar.grid(row=0, column=0, sticky="ew", padx=20, pady=10)

        self.btn_archive = ctk.CTkButton(toolbar, text="📦 Архив", width=90, command=self.safe_toggle_archive,
                                         state="disabled")
        self.btn_archive.pack(side="left", padx=3)

        self.btn_delete = ctk.CTkButton(toolbar, text="🗑️ Удалить", width=90, fg_color="#c0392b",
                                        hover_color="#922b21", command=self.safe_move_to_trash, state="disabled")
        self.btn_delete.pack(side="left", padx=3)

        self.btn_restore = ctk.CTkButton(toolbar, text="↩️ Восстановить", width=110, fg_color="#27ae60",
                                         hover_color="#1e8449", command=self.safe_restore_note, state="disabled")

        self.btn_export = ctk.CTkButton(toolbar, text="📤 Экспорт .md", width=110, fg_color="#8e44ad",
                                        hover_color="#6c3483", command=self.safe_export_markdown, state="disabled")
        self.btn_export.pack(side="right", padx=3)

        self.title_entry = ctk.CTkEntry(self.editor_frame, placeholder_text="Заголовок",
                                        font=ctk.CTkFont(size=22, weight="bold"), height=50, state="disabled")
        self.title_entry.grid(row=1, column=0, sticky="ew", padx=30, pady=(10, 5))
        self.title_entry.bind("<KeyRelease>", lambda e: self.safe_content_change())

        self.text_area = ctk.CTkTextbox(self.editor_frame, font=ctk.CTkFont(size=15), state="disabled")
        self.text_area.grid(row=2, column=0, sticky="nsew", padx=30, pady=10)
        self.text_area.bind("<KeyRelease>", lambda e: self.safe_content_change())

        self.status_lbl = ctk.CTkLabel(self.editor_frame, text="", text_color="gray", anchor="w")
        self.status_lbl.grid(row=3, column=0, sticky="w", padx=30, pady=10)

        self.stats_lbl = ctk.CTkLabel(self.editor_frame, text="", text_color="gray", anchor="e")
        self.stats_lbl.grid(row=3, column=0, sticky="e", padx=30, pady=10)

    # --- БЕЗОПАСНЫЕ ОБЕРТКИ ДЛЯ СОБЫТИЙ ---

    def safe_set_filter(self, f_type):
        try:
            self.set_filter(f_type)
        except Exception:
            pass

    def safe_create_new_note(self):
        try:
            self.create_new_note()
        except Exception:
            pass

    def safe_import_markdown(self):
        try:
            self.import_markdown()
        except Exception:
            pass

    def safe_toggle_theme(self):
        try:
            self.toggle_theme()
        except Exception:
            pass

    def safe_refresh_list(self):
        try:
            self.refresh_list()
        except Exception:
            pass

    def safe_content_change(self):
        try:
            self.on_content_change()
        except Exception:
            pass

    def safe_toggle_archive(self):
        try:
            self.toggle_archive()
        except Exception:
            pass

    def safe_move_to_trash(self):
        try:
            self.move_to_trash()
        except Exception:
            pass

    def safe_restore_note(self):
        try:
            self.restore_note()
        except Exception:
            pass

    def safe_export_markdown(self):
        try:
            self.export_markdown()
        except Exception:
            pass

    # --- ОСНОВНАЯ ЛОГИКА ---

    def toggle_theme(self):
        mode = "Light" if ctk.get_appearance_mode() == "Dark" else "Dark"
        ctk.set_appearance_mode(mode)
        self.theme_switch.configure(text="Темная" if mode == "Light" else "Светлая")
        color = "#f0f0f0" if mode == "Light" else "#2b2b2b"
        self.list_frame.configure(fg_color=color)

    def set_filter(self, f_type):
        self.current_filter = f_type
        for ft, btn in self.nav_btns.items():
            btn.configure(fg_color="#3a3a3a" if ft == f_type else "transparent")
        self.clear_editor()
        self.refresh_list()

    def refresh_list(self):
        try:
            for widget in self.scroll_frame.winfo_children():
                widget.destroy()

            notes = self.manager.get_notes(self.current_filter, self.search_entry.get())

            if not notes:
                ctk.CTkLabel(self.scroll_frame, text="Нет заметок", text_color="gray").grid(row=0, column=0, pady=40)
                return

            for i, note in enumerate(notes):
                card = NoteCard(self.scroll_frame, note, on_select=self.load_note, on_toggle_fav=self.toggle_favorite)
                card.grid(row=i, column=0, sticky="ew")
        except Exception:
            pass

    def create_new_note(self):
        note = self.manager.create_note()
        self.refresh_list()
        self.load_note(note)

    def load_note(self, note):
        try:
            self.current_note_id = note["id"]

            self.title_entry.configure(state="normal")
            self.text_area.configure(state="normal")
            self.btn_export.configure(state="normal")

            self.title_entry.delete(0, "end")
            self.title_entry.insert(0, note["title"])

            self.text_area.delete("1.0", "end")
            self.text_area.insert("1.0", note["content"])

            is_trash = note["is_deleted"]
            self.btn_delete.configure(state="disabled" if is_trash else "normal")
            self.btn_archive.configure(state="disabled" if is_trash else "normal")
            self.btn_restore.configure(state="normal" if is_trash else "disabled")
            self.btn_export.configure(state="disabled" if is_trash else "normal")

            if is_trash:
                self.title_entry.configure(state="disabled")
                self.text_area.configure(state="disabled")

            self.update_stats(note["content"])
            self.status_lbl.configure(text=f"Изменено: {note['updated_at']}")
        except Exception:
            pass

    def clear_editor(self):
        try:
            self.current_note_id = None
            self.title_entry.configure(state="disabled")
            self.text_area.configure(state="disabled")
            self.title_entry.delete(0, "end")
            self.text_area.delete("1.0", "end")
            for btn in [self.btn_delete, self.btn_archive, self.btn_restore, self.btn_export]:
                btn.configure(state="disabled")
            self.status_lbl.configure(text="")
            self.stats_lbl.configure(text="")
        except Exception:
            pass

    def on_content_change(self):
        try:
            if self.current_note_id:
                title = self.title_entry.get()
                content = self.text_area.get("1.0", "end-1c")
                self.manager.update_note(self.current_note_id, title=title, content=content)
                self.status_lbl.configure(text=f"✓ Сохранено: {datetime.now().strftime('%H:%M:%S')}")
                self.update_stats(content)
        except Exception:
            pass

    def update_stats(self, content):
        try:
            words = len(content.split())
            chars = len(content)
            self.stats_lbl.configure(text=f"📊 {words} слов | {chars} символов")
        except Exception:
            pass

    def toggle_favorite(self, note_id):
        try:
            note = next((n for n in self.manager.notes if n["id"] == note_id), None)
            if note:
                self.manager.update_note(note_id, is_favorite=not note["is_favorite"])
                self.refresh_list()
                if self.current_note_id == note_id:
                    self.load_note(note)
        except Exception:
            pass

    def toggle_archive(self):
        try:
            if self.current_note_id:
                note = next((n for n in self.manager.notes if n["id"] == self.current_note_id), None)
                if note:
                    self.manager.update_note(self.current_note_id, is_archived=not note["is_archived"])
                    self.refresh_list()
                    self.clear_editor()
        except Exception:
            pass

    def move_to_trash(self):
        try:
            if self.current_note_id:
                self.manager.update_note(self.current_note_id, is_deleted=True)
                self.refresh_list()
                self.clear_editor()
        except Exception:
            pass

    def restore_note(self):
        try:
            if self.current_note_id:
                self.manager.update_note(self.current_note_id, is_deleted=False)
                self.refresh_list()
                self.clear_editor()
        except Exception:
            pass

    def export_markdown(self):
        try:
            if not self.current_note_id:
                return

            note = next((n for n in self.manager.notes if n["id"] == self.current_note_id), None)
            if not note:
                return

            ExportDialog(self, lambda t, m: self._do_export(note, t, m))
        except Exception:
            pass

    def _do_export(self, note, inc_title, inc_meta):
        try:
            content = ""
            if inc_title:
                content += f"# {note['title']}\n\n"
            if inc_meta:
                content += f"> 📅 Создано: {note['created_at']}  \n"
                content += f"> ✏️ Изменено: {note['updated_at']}\n\n"
            content += note['content']
            content += f"\n\n---\n*Экспорт из Pro Notes: {datetime.now().strftime('%d.%m.%Y %H:%M')}*"

            filepath = filedialog.asksaveasfilename(
                defaultextension=".md",
                filetypes=[("Markdown", "*.md"), ("Текст", "*.txt"), ("Все", "*.*")],
                initialfile=f"{note['title']}.md",
                title="Сохранить файл"
            )

            if filepath:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(content)
                self.status_lbl.configure(text=f"✓ Экспортировано: {os.path.basename(filepath)}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить файл:\n{e}")

    def import_markdown(self):
        try:
            filepath = filedialog.askopenfilename(
                filetypes=[("Markdown", "*.md"), ("Текст", "*.txt"), ("Все", "*.*")],
                title="Импорт файла"
            )
            if filepath:
                note = self.manager.import_markdown(filepath)
                if note:
                    self.refresh_list()
                    self.load_note(note)
                    self.status_lbl.configure(text=f"✓ Импортировано: {note['title']}")
                else:
                    messagebox.showerror("Ошибка", "Не удалось импортировать файл")
        except Exception:
            pass


if __name__ == "__main__":
    try:
        app = App()
        app.mainloop()
    except KeyboardInterrupt:
        pass
    except Exception:
        pass

def benchmark(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        end = time.perf_counter()
        print(f"[*] Функция '{func.__name__}' выполнена")
        return result
    return wrapper

@benchmark
def def_name():
    pass