import PyInstaller.__main__
import os

# Имя вашего основного скрипта
APP_NAME = 'main.py'
# Название итогового файла
DIST_NAME = 'ProNotes'

PyInstaller.__main__.run([
    APP_NAME,
    '--onefile',             # Создать один .exe файл
    '--windowed',            # Без консольного окна (черного фона)
    '--name', DIST_NAME,     # Имя файла
    '--icon', 'NONE',        # Можно указать путь к .ico для иконки
    '--clean',               # Очистить временные файлы перед сборкой
    '--noconfirm',           # Не спрашивать подтверждение при перезаписи
])

print(f"\n✅ Готово! Файл {DIST_NAME}.exe находится в папке 'dist'")