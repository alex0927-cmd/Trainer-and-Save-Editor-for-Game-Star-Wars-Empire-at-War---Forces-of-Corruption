# 16. Авто-зв'язування, live-значення та збереження калібрування

## Огляд

Цей документ описує систему **читання / запису значень з RAM гри** без ручного введення адрес — через авто-зв'язування (2 кроки), live-моніторинг і збереження калібрування між запусками трейнера.

---

## Архітектура даних

### `CheatState` (dataclass)

```python
@dataclass
class CheatState:
    enabled: bool = False
    addresses: list[int] = []       # адреси в RAM
    patch_backup: dict[int, bytes] = {}
    alloc_address: int | None = None
    target_value: float | None = None  # бажане значення користувача
```

`target_value` — число з поля **«Бажане»** після «Застосувати» або після авто-зв'язування.

### Мапінг параметрів

| kind (ключ) | CheatState / сховище | Тип RAM |
|-------------|---------------------|---------|
| `credits` | `self.credits` | int / float |
| `tactical_credits` | `self.tactical_credits` | int / float |
| `health` | `self._health_watch: dict[addr, peak_hp]` | float |
| `cooldown` | `self._cooldown_addrs: list[int]` | float |

---

## Читання значень

### `get_live_values()`

Повертає словник для UI:

```python
{
    "credits": read_addresses(credits.addresses),
    "tactical_credits": read_addresses(tactical_credits.addresses),
    "health": read_float(first_health_addr),
    "cooldown": read_float(first_cooldown_addr),
}
```

`None` — якщо зв'язування відсутнє.

### `read_addresses(addresses)`

Перебирає до 5 адрес, для кожної:

1. `read_int` — якщо 0 ≤ value ≤ 999 999 999 → повертає float
2. Інакше `read_float` — той самий діапазон

**Чому обидва типи:** у `swfoc.exe` знайдено рядок `Credits:%f` — кредити можуть бути float.

### `pull_current_into_target(kind)`

1. Викликає `get_live_values()`
2. Оновлює `target_value` для credits / tactical_credits
3. Повертає число для заповнення поля «Бажане» в GUI

---

## Запис значень

### `apply_user_value(kind, value)`

| kind | Дія |
|------|-----|
| `credits` / `tactical_credits` | `state.target_value = value` → `write_addresses` → `_persist_bindings()` |
| `health` | `write_float` на всі адреси `_health_watch`, оновити peak |
| `cooldown` | `write_float` на `_cooldown_addrs` |

Також оновлює `CREDIT_TARGET` / `TACTICAL_CREDIT_TARGET` при застосуванні кредитів.

### `write_addresses(addresses, value)`

Для кожної адреси:

```python
pm.write_int(addr, int(value))
pm.write_float(addr, float(value))
```

---

## Авто-зв'язування (2 кроки)

### Ідея

Замість ручного введення «5000 → скан → 4500 → уточнити»:

1. Зберегти **snapshot** усіх int у діапазоні в writable RAM
2. Користувач змінює значення **в грі**
3. Другий snapshot → **diff** → адреси, де число змінилось

Це класичний підхід Cheat Engine «Unknown initial value → Changed value», автоматизований для конкретного діапазону.

### `capture_int_snapshot(min, max, writable_only=True)`

Файл: `trainer/scanner.py`

```
для кожного readable регіону RAM (≤ 8 МБ):
    якщо writable_only і регіон не writable → skip
    для кожного offset кратного 4:
        value = int32 LE
        якщо min ≤ value ≤ max:
            snapshot[addr] = value
            (макс. 150 000 записів)
```

### `diff_snapshots(before, after)`

```python
for addr, old_value in before.items():
    new_value = after.get(addr)
    if new_value is not None and new_value != old_value:
        changed.append((addr, old_value, new_value))
```

### Діапазони пошуку

| kind | min | max |
|------|-----|-----|
| `credits` | 0 | 99 999 999 |
| `tactical_credits` | 0 | 999 999 |
| `health` | 50 | 500 000 |
| `cooldown` | 0 | 600 |

### `finish_auto_bind` — вибір адрес

1. Сортування за адресою (пріоритет нижніх / heap)
2. Береться до **20** кандидатів, для credits/tactical — **5** адрес
3. Для health — до **8** адрес у `_health_watch`
4. `new_value` = нове значення з першого знайденого diff
5. `_persist_bindings()` → JSON

### Особливий випадок: cooldown

Один крок через `calibrate_cooldown(value)`:

1. Користувач вводить очікуваний час перезарядки в «Бажане»
2. «Авто-зв'язати» → `first_scan_float(value)` одразу
3. Не потребує другого кроку

---

## Live-оновлення в GUI

### Таймер

```python
def _tick_live_refresh(self):
    self._update_live_labels()
    self.after(1000, self._tick_live_refresh)  # кожні 1 с
```

Запускається після «Підключитися», зупиняється при закритті.

### Відображення

| Тип | Формат |
|-----|--------|
| Кредити / HP | `9 999 999` (з пробілами) |
| Cooldown | `12.5` (один знак після коми) |
| Немає даних | `—` |

---

## Збереження: `trainer_calibration.json`

Файл: `trainer/calibration_store.py`

### Формат

```json
{
  "addresses": {
    "credits": [12345678, 12345682],
    "tactical_credits": [],
    "health": [87654321],
    "cooldown": [11223344]
  }
}
```

### Коли зберігається

- Після успішного `finish_auto_bind`
- Після `apply_user_value` для credits/tactical
- Після `refine_credits` / калібрування

### Коли завантажується

При створенні `PlayerTrainer` → `_load_saved_bindings()`:

- відновлює `addresses` для credits і tactical_credits
- читає поточне значення з RAM → `target_value`
- лог: `Завантажено збережене зв'язування [credits]: 4500`

### Обмеження

| Ситуація | Наслідок |
|----------|----------|
| Перезапуск `swfoc.exe` | Адреси **інші** — зв'язування не працює |
| Перезапуск трейнера (гра та сама) | Може працювати, якщо гра не перезавантажувалась |
| Зміна сейву / нова місія | Можливо потрібне повторне авто-зв'язування |

**Рекомендація:** після кожного запуску гри — авто-зв'язати кредити заново (2 кроки, ~30 секунд).

---

## Порівняння: авто-зв'язати vs класичне сканування

| | Авто-зв'язати | calibrate_credits + refine |
|--|---------------|---------------------------|
| Введення точного числа | Не потрібно | Потрібно 2 рази |
| Кроків у UI | 2 кнопки | Скан + Уточнити |
| API | `start_auto_bind` / `finish_auto_bind` | `calibrate_credits` / `refine_credits` |
| Доступ у GUI | Так | Лише програмно (API залишено в `cheats.py`) |

Класичне сканування залишено для сумісності та тестів.

---

## Діаграма потоку auto-bind

```
[Крок 1: Авто-зв'язати]
        │
        ▼
capture_int_snapshot(0, 99_999_999)
        │
        ▼
_auto_bind_before = snapshot  (зберегти в RAM трейнера)
        │
        ▼
[Користувач змінює кредити В ГРІ]
        │
        ▼
[Крок 2: Авто-зв'язати]
        │
        ▼
capture_int_snapshot() знову
        │
        ▼
diff_snapshots(before, after)
        │
        ▼
credits.addresses = top 5 candidates
credits.target_value = new_value
        │
        ▼
_persist_bindings() → trainer_calibration.json
        │
        ▼
GUI: «Поточне» і «Бажане» оновлені
```

---

## Наступний документ

[10-PAMIYAT-TA-HUKY.md](10-PAMIYAT-TA-HUKY.md) — низькорівнева робота з пам'яттю
