# 10. Пам'ять процесу та кодові хуки (технічний deep dive)

## Win32 API (через pymem)

| Операція | API |
|----------|-----|
| Відкрити процес | `OpenProcess(PROCESS_ALL_ACCESS, …)` |
| Читати RAM | `ReadProcessMemory` |
| Писати RAM | `WriteProcessMemory` |
| Знайти модуль | `EnumProcessModules` / toolhelp |
| Скан патерну | власний цикл + маска `??` |

`pymem` інкапсулює це в `pm.read_int`, `pm.write_float`, `pm.read_bytes`.

---

## Архітектура 32 vs 64

Ваша гра:

```
swfoc.exe → PE machine 0x14C → Intel 386 (32-bit)
```

Трейнер зібрано **64-bit Python 3.14** + PyInstaller. На Windows WOW64 це **підтримується**: 64-бітний відладчик/читач може читати 32-бітний процес.

**Типи даних у сканері:**

| Тип | Розмір | Формат |
|-----|--------|--------|
| int32 | 4 | little-endian |
| float | 4 | IEEE 754 LE |
| pointer | 4 | uint32 |

---

## Алгоритм MemoryScanner (оновлено)

### Сканування по всій readable RAM

На відміну від ранніх версій (лише модулі exe), сканер обходить **усі committed readable регіони** через `VirtualQueryEx`:

```python
iter_readable_regions(handle, is_64bit)
  → [(base, size), ...]  # PAGE_READWRITE, READONLY, EXECUTE_READ, ...
```

Регіони > 64 МБ пропускаються при byte-scan (швидкодія).

### first_scan_int / first_scan_float

```
для кожного регіону (base, size):
    data = read_bytes(base, size)
    пошук needle (int32 або float LE) з кроком align
    results.append(base + offset)  # макс. 500
```

### capture_int_snapshot (auto-bind)

```
для writable регіонів ≤ 8 МБ:
    для offset кратного 4:
        якщо min ≤ int32 ≤ max:
            snapshot[addr] = value  # макс. 150 000
```

### diff_snapshots

```
changed = [(addr, old, new) for addr in before if after[addr] != old]
```

Див. [16-AVTO-ZVYAZUVANNYA-TA-ZNACHENNYA.md](16-AVTO-ZVYAZUVANNYA-TA-ZNACHENNYA.md).

---

## Чому кредити шукають і int, і float

У `swfoc.exe` знайдено форматний рядок:

```
Credits:%f
```

Це означає, що в UI/логіці кредити можуть зберігатися як **float**. Сканер спочатку пробує `int`, потім `float`.

---

## Code patching (_patch)

```python
def _patch(self, state, address, new_bytes):
    if address not in state.patch_backup:
        state.patch_backup[address] = pm.read_bytes(address, len(new_bytes))
    pm.write_bytes(address, new_bytes, len(new_bytes))
```

**Відкат:**

```python
for addr, original in state.patch_backup.items():
    write_bytes(pm, addr, original)
```

### Приклад: God Mode AoB

Патерн (загальний, з CE-спільноти для Petroglyph damage):

```
80 B9 ?? ?? ?? ?? 00 74 ?? F3 0F 10
```

Інтерпретація (приблизна):

```
cmp byte ptr [ecx+offset], 0
je  skip_damage
movss xmm0, [...]
```

Патч `+7`: заміна `74` (je) на `EB` (jmp) — **безумовний перехід**, пропуск урону для певної гілки.

**Увага:** без додаткової перевірки `player_id` це може бути неповністю player-only — тому є **fallback HP freeze**.

---

## Патерни інших читів

| Чит | Патерн (скорочено) | Патч |
|-----|-------------------|------|
| no_cooldown | `F3 0F 11 86 ?? ?? ?? ??` | 8× NOP |
| unit_cap | `F3 0F 2C 86 ?? ?? ?? ?? 3B C3 7D` | xor eax,eax |
| instant_build | `F3 0F 5E ?? ?? ?? ??` | divss xmm0,xmm0 → ~миттєво |
| free_build | `89 86 ?? ?? ?? ??` | mov dword [esi+off], 1 |
| map_reveal | `80 ?? ?? ?? ?? ?? 00 74` | byte = 1 |
| fast_speed | `F3 0F 59 ?? ??` | mulss |
| weak_enemies | `F3 0F 59 ?? ??` | збільшення множника |
| super_damage | `F3 0F 59 ?? ??` | mulss xmm1,xmm0 |

`??` = wildcard байт.

---

## Фоновий потік maintenance

```python
def _maintenance_loop(self):
    while not self._stop.is_set():
        if self.credits.enabled:
            target = self.credits.target_value or CREDIT_TARGET  # користувацьке або дефолт
            for addr in self.credits.addresses:
                pm.write_float(addr, target)
                pm.write_int(addr, int(target))
        if self.god_mode.enabled and self._health_watch:
            for addr, peak in self._health_watch.items():
                if pm.read_float(addr) < peak:
                    pm.write_float(addr, peak)
        time.sleep(0.15)
```

**Частота 150 мс** — компроміс CPU / responsiveness.

`target_value` встановлюється через «Застосувати» або авто-зв'язування.

---

## player_id

```python
def __init__(self, pm, player_id: int = 0, ...):
    self.player_id = player_id
```

За замовчуванням **0** — перший людський гравець у skirmish/GC.  
У GUI поки не винесено окремий спінер — можна розширити для мульти seated campaign.

Хуки AoB у CE-таблицях порівнюють owner з **local player index** з глобальної структури — наш код закладає це в вибір патернів гілок «покупки гравця».

---

## Безпека та етика

- Тільки **single-player / локальний** Skirmish.
- Онлайн-мультиплеер: **не використовувати** (бан, нечесно).
- Запис у чужий процес — типова поведінка трейнера, не вірус, але AV може реагувати.

---

## Наступний документ

[11-ZBIRKA-EXE.md](11-ZBIRKA-EXE.md)
