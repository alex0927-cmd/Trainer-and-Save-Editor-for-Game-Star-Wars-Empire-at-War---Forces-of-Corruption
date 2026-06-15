# Star Wars: Empire at War — Forces of Corruption Tools

Трейнер (+10 читів лише для гравця) та GUI-редактор XML для Windows.

<img width="1003" height="849" alt="image" src="https://github.com/user-attachments/assets/45c358fa-74af-4aee-91f9-fe9517edc98a" />


[![Release](https://img.shields.io/github/v/release/alex0927-cmd/Trainer-and-Save-Editor-for-Game-Star-Wars-Empire-at-War---Forces-of-Corruption)](https://github.com/alex0927-cmd/Trainer-and-Save-Editor-for-Game-Star-Wars-Empire-at-War---Forces-of-Corruption/releases)

## Завантаження (готові exe)

**[Releases → EAW_FOC_Tools_v1.0.0_Windows.zip](https://github.com/alex0927-cmd/Trainer-and-Save-Editor-for-Game-Star-Wars-Empire-at-War---Forces-of-Corruption/releases/latest)**

Розпакуйте → запустіть `Запуск_Трейнера.bat` **від адміністратора**. Детально: [INSTALL.md](INSTALL.md).

## Що всередині

| Файл | Опис |
|------|------|
| **EAW_FOC_Editor.exe** | Графічний редактор XML (економіка, HP, планети, фракції) |
| **EAW_FOC_Trainer.exe** | Трейнер +10 у реальному часі — **лише для гравця** |

## Повна документація

**[docs/README.md](docs/README.md)** — зміст із 16 розділами (XML, трейнер, hotkey, лог, auto-bind, збірка).

### Ключові розділи трейнера

| Документ | Зміст |
|----------|-------|
| [09-TRAINER-DETALNO.md](docs/09-TRAINER-DETALNO.md) | Повний посібник: UI, чити, запуск |
| [14-HARIACHI-KLAVISHI.md](docs/14-HARIACHI-KLAVISHI.md) | 20 гарячих клавіш, глобально в грі |
| [15-FAYLOVE-LOGUVANNYA.md](docs/15-FAYLOVE-LOGUVANNYA.md) | Запис у `trainer.log` |
| [16-AVTO-ZVYAZUVANNYA-TA-ZNACHENNYA.md](docs/16-AVTO-ZVYAZUVANNYA-TA-ZNACHENNYA.md) | Auto-bind, live-значення, JSON |

## Запуск (рекомендовано)

| Інструмент | Команда |
|------------|---------|
| Трейнер | `Запуск_Трейнера.bat` — **від адміністратора** |
| Редактор | `Запуск_Редактора.bat` |

Bat-файли обходять блокування Windows Security для непідписаних exe.

## Збірка

```bat
build.bat
```

Потрібні: Python 3.10+, `pymem`, `keyboard`, `pyinstaller`.

## Трейнер — можливості

### Значення з гри

- **Поточне** — автооновлення кожну 1 с з RAM
- **Бажане** — ваше число → **Застосувати**
- **Зчитати** — копіювати з гри
- **Авто-зв'язати** — знайти адресу в пам'яті (2 кроки)

### Чити (+10)

1. Безлімітні кредити (галактика)
2. Безлімітні тактичні ресурси
3. Безсмертя юнітів (тільки ваші)
4. Здібності без перезарядки
5. Нескінченний ліміт юнітів
6. Миттєве будівництво
7. Будівництво за 1 кредит
8. Відкрита карта
9. Швидкість гри x3
10. Слабкі вороги (x5 урон по них)
+ Бонус: ваш урон x10

### Гарячі клавіші

Кнопка **⌨** біля будь-якої дії — призначити клавішу (Ctrl/Alt/Shift + будь-яка клавіша). Працює в грі.

Зберігається в `trainer_hotkeys.json`.

### Файловий лог

Галочка **«Записувати все у файл»** у журналі (вимкнена за замовчуванням) → `trainer.log`.

### Runtime-файли

| Файл | Опис |
|------|------|
| `trainer_calibration.json` | Збережені адреси RAM |
| `trainer_hotkeys.json` | Гарячі клавіші |
| `trainer.log` | Повний лог сесії |

## Редактор

1. Запустити `Запуск_Редактора.bat`
2. Перевірити шлях до `data2`
3. Змінити параметри або **Чит-пресет (макс.)**
4. **Зберегти** → перезапустити гру

> XML-моди глобальні. Для читів лише для себе — трейнер.

## Важливо

- Трейнер: **single-player**, запуск **від адміна**
- Після **перезапуску гри** — повторне авто-зв'язування кредитів
- Противник **не отримує** бонусів трейнера
- Антивірус може блокувати exe — використовуйте bat
