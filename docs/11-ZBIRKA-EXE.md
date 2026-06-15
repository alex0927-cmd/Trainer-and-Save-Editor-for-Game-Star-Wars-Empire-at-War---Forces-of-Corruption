# 11. Збірка EXE: PyInstaller, залежності, запуск

## Результат збірки

```
EAW_FOC_Tools\dist\
├── EAW_FOC_Editor.exe
└── EAW_FOC_Trainer.exe
```

Обидва — **onefile**, **windowed** (без консолі).

---

## Залежності

`requirements.txt`:

```
pymem>=1.13.0
keyboard>=0.13.5
pyinstaller>=6.0.0
```

| Пакет | Призначення |
|-------|-------------|
| `pymem` | Читання/запис RAM `swfoc.exe` |
| `keyboard` | Глобальні гарячі клавіші трейнера |
| `pyinstaller` | Збірка exe |

### Проблема з pip

Якщо `pip install` падає з `WinError 10013`:

```bash
uv pip install -r requirements.txt --python python
```

---

## build.bat

```bat
cd /d "%~dp0"
uv pip install -r requirements.txt
python -m PyInstaller EAW_FOC_Trainer.spec
python -m PyInstaller EAW_FOC_Editor.spec
```

### EAW_FOC_Trainer.spec (ключові параметри)

| Параметр | Значення |
|----------|----------|
| Entry point | `trainer_main.py` (не `trainer/app.py`) |
| `hiddenimports` | `pymem`, `keyboard`, `shared.*`, `trainer.*` |
| `upx` | `False` (стабільність) |
| `console` | `False` |

`trainer_main.py` додає корінь проєкту в `sys.path` — вирішує `ModuleNotFoundError: shared`.

---

## Запуск без збірки

### Рекомендовано: bat-файли

```
Запуск_Трейнера.bat   → адмін + pymem + keyboard + trainer_main.py
Запуск_Редактора.bat  → editor_main.py
```

### Вручну

```bash
cd EAW_FOC_Tools
set PYTHONPATH=.
python trainer_main.py
```

---

## Windows Security та exe

| Проблема | Рішення |
|----------|---------|
| SmartScreen блокує exe | `Запуск_Трейнера.bat` |
| AV false positive | Виняток у Defender |
| exe не стартує | Зібрати з `console=True` для дебагу |

Непідписаний exe часто блокується — bat через Python є обхідним шляхом.

---

## Runtime-файли (поруч із трейнером)

Після використання з'являються:

| Файл | Опис |
|------|------|
| `trainer_calibration.json` | Адреси RAM |
| `trainer_hotkeys.json` | Гарячі клавіші |
| `trainer.log` | Лог (якщо увімкнено галочку) |

---

## Типові проблеми збірки

| Проблема | Рішення |
|----------|---------|
| `ModuleNotFoundError: shared` | Entry `trainer_main.py` + `pathex` у spec |
| `No module named keyboard` | `pip install keyboard` |
| `No module named pymem` | `pip install pymem` |
| Hotkey не працює в зібраному exe | Запуск від адміна; `collect_submodules('keyboard')` у spec |

---

## Версії на момент документації

- Python **3.14**
- PyInstaller **6.21**
- pymem **1.14**
- keyboard **0.13.5**
- Windows **11** build 26200

---

## Наступний документ

[12-DOVIDNYK-ZMIN.md](12-DOVIDNYK-ZMIN.md)
