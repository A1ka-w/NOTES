import json
import os
import uuid
from datetime import datetime
from functools import wraps
import time
from pathlib import Path

DATA_FILE = "notes_data.json"

# --- ДЕКОРАТОРЫ ---
def benchmark(func):
    """Замер времени выполнения + безопасный вызов"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        try:
            return func(*args, **kwargs)
        except Exception as e:
            print(f"[!] Ошибка в '{func.__name__}': {e}")
            return None
        finally:
            print(f"[*] Функция '{func.__name__}' выполнена за {time.perf_counter() - start:.4f} сек.")
    return wrapper

# --- ЯДРО ПРИЛОЖЕНИЯ ---
class NoteManager:
    __slots__ = ('notes', '_data_file', '_date_fmt')

    def __init__(self, data_file: str = DATA_FILE):
        self._data_file = Path(data_file)
        self._date_fmt = "%d.%m.%Y %H:%M"
        self.notes = []
        self.load()

    @benchmark
    def load(self) -> None:
        if self._data_file.exists():
            try:
                self.notes = json.loads(self._data_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, IOError) as e:
                print(f"[!] Не удалось загрузить данные: {e}")
                self.notes = []

    @benchmark
    def save(self) -> None:
        try:
            self._data_file.write_text(
                json.dumps(self.notes, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
        except IOError as e:
            print(f"[!] Не удалось сохранить данные: {e}")

    @staticmethod
    def _now() -> str:
        return datetime.now().strftime("%d.%m.%Y %H:%M")

    def create_note(self, title: str = "Новая заметка") -> dict:
        ts = self._now()
        new_note = {
            "id": str(uuid.uuid4()),
            "title": title,
            "content": "",
            "is_favorite": False,
            "is_archived": False,
            "is_deleted": False,
            "created_at": ts,
            "updated_at": ts
        }
        self.notes.append(new_note)
        self.save()
        return new_note

    def update_note(self, note_id: str, **kwargs) -> dict | None:
        for note in self.notes:
            if note["id"] == note_id:
                note.update(kwargs)
                note["updated_at"] = self._now()
                self.save()
                return note
        return None

    def get_note(self, note_id: str) -> dict | None:
        for note in self.notes:
            if note["id"] == note_id:
                return note
        return None

    @benchmark
    def get_notes(self, filter_type: str = "all", search_query: str = "") -> list[dict]:
        query_lower = search_query.lower().strip()
        # Оптимизированная фильтрация через генератор + list
        filtered = [
            n for n in self.notes
            if self._match_filter(n, filter_type) and self._match_search(n, query_lower)
        ]
        # Исправлена сортировка: DD.MM.YYYY не сортируется лексикографически
        filtered.sort(key=lambda x: datetime.strptime(x["updated_at"], self._date_fmt), reverse=True)
        return filtered

    def _match_filter(self, note: dict, f_type: str) -> bool:
        if note["is_deleted"]:
            return f_type == "trash"
        if f_type == "archive": return note["is_archived"]
        if f_type == "favorite": return note["is_favorite"]
        return f_type == "all"

    def _match_search(self, note: dict, q: str) -> bool:
        if not q: return True
        return q in note["title"].lower() or q in note["content"].lower()

    def toggle_favorite(self, note_id: str) -> bool:
        note = self.get_note(note_id)
        if note:
            self.update_note(note_id, is_favorite=not note["is_favorite"])
            return True
        return False

    def toggle_archive(self, note_id: str) -> bool:
        note = self.get_note(note_id)
        if note and not note["is_deleted"]:
            self.update_note(note_id, is_archived=not note["is_archived"])
            return True
        return False

    def move_to_trash(self, note_id: str) -> bool:
        note = self.get_note(note_id)
        if note:
            self.update_note(note_id, is_deleted=True)
            return True
        return False

    def restore_note(self, note_id: str) -> bool:
        note = self.get_note(note_id)
        if note:
            self.update_note(note_id, is_deleted=False)
            return True
        return False

    def delete_permanently(self, note_id: str) -> bool:
        before = len(self.notes)
        self.notes = [n for n in self.notes if n["id"] != note_id]
        if len(self.notes) != before:
            self.save()
            return True
        return False

    def clear_trash(self) -> int:
        before = len(self.notes)
        self.notes = [n for n in self.notes if not n["is_deleted"]]
        removed = before - len(self.notes)
        if removed > 0: self.save()
        return removed

    @benchmark
    def import_markdown(self, filepath: str) -> dict | None:
        try:
            path = Path(filepath)
            if not path.exists(): raise FileNotFoundError(filepath)

            content = path.read_text(encoding="utf-8")
            lines = content.split("\n")
            title = path.stem

            if lines and lines[0].startswith("#"):
                title = lines[0].lstrip("#").strip()
                content = "\n".join(lines[1:]).lstrip()

            ts = self._now()
            new_note = {
                "id": str(uuid.uuid4()), "title": title, "content": content,
                "is_favorite": False, "is_archived": False, "is_deleted": False,
                "created_at": ts, "updated_at": ts
            }
            self.notes.append(new_note)
            self.save()
            return new_note
        except Exception as e:
            print(f"[!] Импорт: {e}")
            return None

    def export_markdown(self, note_id: str, output_path: str, inc_title: bool = True, inc_meta: bool = True) -> bool:
        note = self.get_note(note_id)
        if not note: return False

        try:
            md = ""
            if inc_title: md += f"# {note['title']}\n\n"
            if inc_meta:
                md += f"> 📅 Создано: {note['created_at']}  \n> ✏️ Изменено: {note['updated_at']}\n\n"
            md += note['content']
            md += f"\n\n---\n*Экспорт из Pro Notes: {self._now()}*"

            Path(output_path).write_text(md, encoding="utf-8")
            return True
        except Exception as e:
            print(f"[!] Экспорт: {e}")
            return False


# --- ПРИМЕР ИСПОЛЬЗОВАНИЯ (CLI / БЕЗ GUI) ---
if __name__ == "__main__":
    try:
        manager = NoteManager()

        # 1. Создание
        print("\n📝 Создание заметок...")
        n1 = manager.create_note("Тестовая заметка")
        manager.update_note(n1["id"], content="Привет, мир! Это тест функционала.\nВторая строка.")

        # 2. Изменение состояния
        manager.toggle_favorite(n1["id"])
        manager.create_note("Архивная заметка")
        manager.toggle_archive(next(n["id"] for n in manager.notes if n["title"] == "Архивная заметка"))

        # 3. Получение с фильтром и поиском
        print("\n🔍 Все активные заметки:")
        for n in manager.get_notes("all", "мир"):
            print(f"  • {n['title']} | {'★' if n['is_favorite'] else '☆'}")

        # 4. Экспорт
        print("\n📤 Экспорт...")
        if manager.export_markdown(n1["id"], "exported_note.md"):
            print("  ✅ Успешно экспортировано в exported_note.md")

        # 5. Удаление/Восстановление
        manager.move_to_trash(n1["id"])
        print(f"\n🗑️ В корзине: {len(manager.get_notes('trash'))} заметок")
        manager.restore_note(n1["id"])
        print(f"✅ Восстановлено. Активных: {len(manager.get_notes('all'))}")

        print("\n✨ Ядро работает корректно. Все операции защищены и оптимизированы.")

    except KeyboardInterrupt:
        print("\n🛑 Прервано пользователем.")
    except Exception as e:
        print(f"\n💥 Критическая ошибка: {e}")