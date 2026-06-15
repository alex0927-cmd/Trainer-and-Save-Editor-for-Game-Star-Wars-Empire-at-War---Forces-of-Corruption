# 07. Архітектура проєкту EAW_FOC_Tools

## Структура каталогів (актуальна)

```
EAW_FOC_Tools/
├── build.bat                      # збірка exe
├── requirements.txt               # pymem, keyboard, pyinstaller
├── README.md                      # короткий опис
├── Запуск_Трейнера.bat            # запуск трейнера від адміна (рекомендовано)
├── Запуск_Редактора.bat           # запуск редактора
├── trainer_main.py                # entry point трейнера
├── editor_main.py                 # entry point редактора
├── EAW_FOC_Trainer.spec           # PyInstaller spec
├── EAW_FOC_Editor.spec
├── trainer_calibration.json       # (runtime) збережені адреси RAM
├── trainer_hotkeys.json           # (runtime) гарячі клавіші
├── trainer.log                    # (runtime) файловий лог
├── docs/                          # документація
├── dist/
│   ├── EAW_FOC_Editor.exe
│   └── EAW_FOC_Trainer.exe
├── build/                         # артефакти PyInstaller
├── editor/
│   ├── __init__.py
│   └── app.py                     # GUI редактора XML
├── trainer/
│   ├── __init__.py
│   ├── app.py                     # GUI трейнера
│   ├── cheats.py                  # 11 читів + auto-bind + freeze
│   ├── scanner.py                 # сканер RAM + snapshot diff + AoB
│   ├── hotkeys.py                 # глобальні гарячі клавіші
│   ├── hotkey_store.py            # JSON для hotkey
│   ├── file_logger.py             # запис trainer.log
│   └── calibration_store.py       # JSON для адрес RAM
└── shared/
    ├── __init__.py
    ├── bootstrap.py               # sys.path для frozen/dev
    ├── paths.py                   # шлях до data2
    ├── process.py                 # підключення до swfoc.exe
    └── xml_store.py               # читання/запис XML тегів
```

---

## Чому Python + tkinter

| Вимога | Рішення |
|--------|---------|
| GUI на Windows | `tkinter` — вбудований у Python |
| Доступ до пам'яті | `pymem` — Read/WriteProcessMemory |
| Глобальні hotkey | `keyboard` — low-level hook Windows |
| Один exe | PyInstaller `--onefile --windowed` |
| Мінімум залежностей | 3 пакети у requirements |

---

## Модуль `shared/paths.py`

### `find_game_root()`

1. `EAW_FOC_ROOT` (env)
2. Відносний `../data2` від `EAW_FOC_Tools`
3. `C:\Games\Star Wars Empire At War Collection\data2`

### `PROCESS_NAMES`

```python
PROCESS_NAMES = ("swfoc.exe", "sweaw.exe")
```

---

## Модуль `shared/process.py`

| Функція | Призначення |
|---------|-------------|
| `list_game_processes()` | Toolhelp32 snapshot → `[(name, pid)]` |
| `attach()` | `pymem.Pymem` + base address модуля |

Повертає `GameProcess(pm, name, pid, base, is_64bit)`.

**Виправлення:** `pm.is_64_bit` — властивість, не метод.

---

## Модуль `shared/xml_store.py`

| Функція | Призначення |
|---------|-------------|
| `read_tag` / `write_tag` | regex-робота з XML |
| `replace_all_tags` | масова заміна |
| `set_planet_credits` | всі `Planet_Credit_Value` |
| `backup_file` | `.bak_YYYYMMDD_HHMMSS` |
| `GAMECONSTANTS_PRESETS` | пресети читів |

---

## Модуль `trainer/scanner.py`

### `MemoryScanner`

| Метод | Опис |
|-------|------|
| `first_scan_int` / `first_scan_float` | перший прохід по **всій readable RAM** |
| `next_scan_int` / `next_scan_float` | фільтрація попередніх results |
| `capture_int_snapshot` | snapshot для auto-bind |
| `diff_snapshots` | порівняння до/після |
| `reset` | очистити results |

`iter_readable_regions()` — VirtualQueryEx по всьому адресному простору процесу.

`MAX_RESULTS = 500` для класичного скану; snapshot — до 150 000 записів.

### `pattern_scan_module`

CE-синтаксис `F3 0F ?? 86` → regex для `pymem.pattern.pattern_scan_module`.

---

## Модуль `trainer/cheats.py`

### `PlayerTrainer`

**Стан чита** — `CheatState`:

```python
@dataclass
class CheatState:
    enabled: bool
    addresses: list[int]
    patch_backup: dict[int, bytes]
    target_value: float | None
```

**Ключові методи:**

| Метод | Роль |
|-------|------|
| `get_live_values()` | читання для UI |
| `apply_user_value()` | запис «Бажане» |
| `pull_current_into_target()` | «Зчитати» |
| `start_auto_bind()` / `finish_auto_bind()` | 2-крокове зв'язування |
| `set_cheat()` | увімк/вимк чита |
| `_maintenance_loop()` | freeze кожні 150 мс |

---

## Модуль `trainer/hotkeys.py`

`HotkeyManager` — `keyboard.add_hotkey`, capture через `keyboard.hook`.

Див. [14-HARIACHI-KLAVISHI.md](14-HARIACHI-KLAVISHI.md).

---

## Модуль `trainer/file_logger.py`

`SessionFileLogger` — append у `trainer.log`, потокобезпечний.

Див. [15-FAYLOVE-LOGUVANNYA.md](15-FAYLOVE-LOGUVANNYA.md).

---

## Модуль `trainer/app.py`

`TrainerApp(tk.Tk)` — повний GUI:

- підключення до процесу
- 4 рядки значень (поточне / бажане / зчитати / застосувати / авто-зв'язати)
- 11 чекбоксів читів
- блок гарячих клавіш (20 дій)
- журнал + галочка файлового логування
- live refresh 1 с

---

## Діаграма потоків (трейнер)

```
[Користувач / Hotkey]
        │
        ▼
[trainer/app.py GUI]
        │
        ├─► HotkeyManager (keyboard, фон)
        ├─► SessionFileLogger (trainer.log)
        │
        ▼
[shared/process.py] ──► swfoc.exe (PID)
        │
        ▼
[PlayerTrainer]
        ├─► MemoryScanner (auto-bind, calibrate)
        ├─► _maintenance_loop (freeze 150ms)
        └─► pattern_scan + _patch (AoB хуки)
        │
        ▼
[calibration_store / hotkey_store] ──► JSON на диску
```

---

## Залежності (`requirements.txt`)

```
pymem>=1.13.0
keyboard>=0.13.5
pyinstaller>=6.0.0
```

Встановлення:

```bash
pip install -r requirements.txt
# або: uv pip install -r requirements.txt
```

---

## Наступні документи

- [08-EDITOR-DETALNO.md](08-EDITOR-DETALNO.md)
- [09-TRAINER-DETALNO.md](09-TRAINER-DETALNO.md)
- [14-HARIACHI-KLAVISHI.md](14-HARIACHI-KLAVISHI.md)
- [15-FAYLOVE-LOGUVANNYA.md](15-FAYLOVE-LOGUVANNYA.md)
- [16-AVTO-ZVYAZUVANNYA-TA-ZNACHENNYA.md](16-AVTO-ZVYAZUVANNYA-TA-ZNACHENNYA.md)
