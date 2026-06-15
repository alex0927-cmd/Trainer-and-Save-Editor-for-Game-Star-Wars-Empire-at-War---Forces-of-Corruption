# 03. Дослідження XML: як знайшли параметри HP, грошей і виробництва

## Метод пошуку

Використовувались два інструменти:

1. **Glob** — перелік файлів у `data2`.
2. **Grep (ripgrep)** — пошук ключових слів у `*.xml`.

Перші запити:

```
Build_Cost | Credit | Health | Shield | Max_Speed
Starting_Credits | Initial_Credits | Credit_Income
```

Результат: у розпакованій папці знайшлися лише кілька XML, але **`GAMECONSTANTS.XML`** містив глобальні множники.

---

## Файл `GAMECONSTANTS.XML`

Шлях: `data2\Data\XML\GAMECONSTANTS.XML`  
Розмір: **~4178 рядків**, ~298 КБ тексту.

Це **центральний** файл балансу рушія Petroglyph Alamo.

### Теги для здоров'я юнітів

Знайдено в рядках 37–39:

```xml
<!-- GameObjectType and Hard Point Max Health multiplier factors per mode -->
<Object_Max_Health_Multiplier_Space> 1.5 </Object_Max_Health_Multiplier_Space>
<Object_Max_Health_Multiplier_Land> 1.0 </Object_Max_Health_Multiplier_Land>
```

**Логіка рушія:**

- `1.0` = без змін;
- `2.0` = подвоєне HP;
- `0.5` = половина HP.

**Рішення для «безсмертя»:** встановити дуже велике значення, наприклад `99999.0`.  
Фактичне HP юніта = базове HP з `UNITS_*.XML` × цей множник.

**Обмеження:** множник **глобальний** — підсилює і гравця, і ШІ.

### Теги для економіки (галактика)

Рядки 85–93 (оригінал):

```xml
<Pay_As_You_Go>false</Pay_As_You_Go>
<Political_Income_Curve>0,0, 1,1, 5,1</Political_Income_Curve>
<Progressive_Taxation>1,0, 5,.2, 10,.5</Progressive_Taxation>
<Income_Redistribution>0.6</Income_Redistribution>
<Credit_Cap_Per_Planet> 40000.0 </Credit_Cap_Per_Planet>
```

| Тег | Оригінал | Що робить |
|-----|----------|-----------|
| `Political_Income_Curve` | крива доходу від рівня бази | скільки % доходу дає планета |
| `Progressive_Taxation` | податок при багатьох планетах | зменшує чистий дохід |
| `Income_Redistribution` | 0.6 | частина доходу «перерозподіляється» |
| `Credit_Cap_Per_Planet` | 40000 | **максимум** кредитів × кількість планет |

**Рішення для грошей:**

- `Credit_Cap_Per_Planet` → `999999999.0`
- `Political_Income_Curve` → `0,100, 1,100, 5,100` (максимальний множник)
- `Progressive_Taxation` → нульові податки
- `Income_Redistribution` → `0.0` (гравець тримає весь дохід)

### Швидкість виробництва

```xml
<Production_Speed_Factor>1.0</Production_Speed_Factor>
```

Змінено на `100.0` — будівництво/найм у **100 разів швидше**.

### Респавн героїв (тактичний режим)

```xml
<Default_Hero_Respawn_Time>360.0</Default_Hero_Respawn_Time>
```

360 секунд = 6 хвилин. Змінено на `1.0` сек.

**Увага:** у **галактичній кампанії** герой може загинути **назавжди** через Lua-сюжет — цей тег не скасовує сюжетну смерть.

### Щити

```xml
<ShieldRechargeIntervalInSecs>3.0</ShieldRechargeIntervalInSecs>
```

Змінено на `0.01` — майже миттєве відновлення щитів.

### Вразливість після висадки

```xml
<Elevated_Vulnerability_Factor>-2.0</Elevated_Vulnerability_Factor>
<Space_Elevated_Vulnerability_Factor>-3.0</Space_Elevated_Vulnerability_Factor>
```

Від'ємні значення = юніт **слабший** одразу після висадки.  
Змінено на `0.0` — без штрафу.

### Скірміш / мультиплеєр (кредити)

Знайдено ближче до кінця файлу:

```xml
<Skirmish_Buy_Credits>2000</Skirmish_Buy_Credits>
<Min_Skirmish_Credits>2000</Min_Skirmish_Credits>
<Max_Skirmish_Credits>8000</Max_Skirmish_Credits>
<MP_Default_Credits>6000</MP_Default_Credits>
```

Усі змінено на `999999`.

---

## Файл `PLANETS.XML`

Спочатку файлу **не було** на диску — його **витягнули** з `Config.meg` (див. документ 04).

Тег доходу планети:

```xml
<Planet_Credit_Value>70</Planet_Credit_Value>
```

**Механіка:** кожна планета має базовий щоденний/циклічний дохід. Значення різняться (20–160 у ванілі).

**Рішення:** regex-заміна всіх входжень:

```python
re.subn(r'(<Planet_Credit_Value>)\d+(</Planet_Credit_Value>)', r'\g<1>99999\2', text)
```

Результат: **65 замін** на `99999`.

---

## Файли `FACTIONS.XML` та `EXPANSION_FACTIONS.XML`

### FACTIONS.XML

Містить блоки `<Faction Name="Rebel">`, `<Faction Name="Empire">`.

Ключові теги:

```xml
<Credits_Accumulation_Factor> 0.95 </Credits_Accumulation_Factor>
<Maintenance_Cost>0.25</Maintenance_Cost>
<Space_Skirmish_Unit_Buy_Credits> 100000 </Space_Skirmish_Unit_Buy_Credits>
<Land_Skirmish_Unit_Buy_Credits> 50000 </Land_Skirmish_Unit_Buy_Credits>
```

| Тег | Ефект |
|-----|-------|
| `Credits_Accumulation_Factor` | множник накопичення (0.95 = −5%) |
| `Maintenance_Cost` | вартість утримання флоту за цикл |
| `Space/Land_Skirmish_Unit_Buy_Credits` | кредити при покупці юніта в скірміші |

**Зміни:**

- `Credits_Accumulation_Factor` → `100.0`
- `Maintenance_Cost` → `0.0`
- Skirmish credits → `999999`

### EXPANSION_FACTIONS.XML

Аналогічна структура для **Underworld** та інших фракцій FOC.  
Файл **витягнуто** з `Config.meg` за маркером `Faction Name="Underworld"`.

---

## Файл `UNITS_HERO_UNDERWORLD_TYBER_ZANN.XML`

Приклад юніта-героя. Окремі теги:

```xml
<Tactical_Health>600</Tactical_Health>
<Shield_Points>0</Shield_Points>
<Min_Respawn_Times>90.0, 90.0, ...</Min_Respawn_Times>
<Death_Persistence_Duration>0.0</Death_Persistence_Duration>
```

Глобальний множник з `GAMECONSTANTS` уже дає величезне HP; додатково змінено респавн на `1.0` сек.

**Повний rebalance усіх `UNITS_*.XML`** (598 тегів `Build_Cost_Credits` у MEG) **не виконувався** — занадто багато файлів без надійного MEG-екстрактора.

---

## Порівняння `data1` vs `data2` GAMECONSTANTS

У колекції є дві копії:

- `data1\Data\XML\GAMECONSTANTS.XML` — базова гра
- `data2\Data\XML\GAMECONSTANTS.XML` — FOC (інші значення, більше тегів)

FOC-версія має додаткові механіки (корупція, Underworld). Зміни вносились **тільки в data2**.

---

## Джерела знань (спільнота моддерів)

Підтверджено підходи з:

- **Petrolution / ModTools** — MEG Editor, структура `Data\XML\`
- **Steam Community** — зміна `Max_Ground_Forces_On_Planet`, `Space_Tactical_Unit_Cap`
- **Cheat Happens / FearLess CE** — XML-редагування для кредитів планет, `Production_Speed_Factor`

---

## Наступний документ

[04-DOSLIDZHENNYA-MEG.md](04-DOSLIDZHENNYA-MEG.md) — спроби розпакувати `Config.meg`.
