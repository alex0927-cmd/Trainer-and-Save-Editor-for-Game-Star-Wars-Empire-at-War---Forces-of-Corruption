# 05. Перші XML-модифікації (етап 1): повний перелік змін

Цей документ описує **перший етап** — ручні зміни у `data2\Data\XML\` до створення `EAW_FOC_Tools`.

---

## Загальний принцип

Кожна зміна — заміна значення між XML-тегами. Гра при наступному запуску читає файл з диска замість копії з `Config.meg`.

**Потрібен перезапуск гри** після змін.

---

## GAMECONSTANTS.XML

### Бойова система

| Тег | Було | Стало | Ефект |
|-----|------|-------|-------|
| `Object_Max_Health_Multiplier_Space` | 1.5 | **99999.0** | HP у космосі ×99999 |
| `Object_Max_Health_Multiplier_Land` | 1.0 | **99999.0** | HP на землі ×99999 |
| `Elevated_Vulnerability_Factor` | -2.0 | **0.0** | без штрафу після висадки (суша) |
| `Space_Elevated_Vulnerability_Factor` | -3.0 | **0.0** | без штрафу (космос) |
| `ShieldRechargeIntervalInSecs` | 3.0 | **0.01** | швидке відновлення щитів |
| `Under_Construction_Damage_Multiplier` | 2.0 | **0.01** | майже без урону під час будівництва |
| `Default_Hero_Respawn_Time` | 360.0 | **1.0** | респавн героя 1 сек (тактика) |

### Економіка (галактика)

| Тег | Було | Стало |
|-----|------|-------|
| `Political_Income_Curve` | `0,0, 1,1, 5,1` | `0,100, 1,100, 5,100` |
| `Progressive_Taxation` | `1,0, 5,.2, 10,.5` | `1,0, 5,0, 10,0` |
| `Income_Redistribution` | 0.6 | **0.0** |
| `Credit_Cap_Per_Planet` | 40000.0 | **999999999.0** |
| `Black_Market_Income_Mult_Max` | 3.0 | **9999.0** |
| `MaxCreditIncomeAlignmentBonus` | 0.50 | **99.0** |
| `MaxCreditIncomeAlignmentPenalty` | 0.50 | **0.0** |

### Виробництво

| Тег | Було | Стало |
|-----|------|-------|
| `Production_Speed_Factor` | 1.0 | **100.0** |

### Скірміш / MP

| Тег | Було | Стало |
|-----|------|-------|
| `Skirmish_Buy_Credits` | 2000 | **999999** |
| `Min_Skirmish_Credits` | 2000 | **999999** |
| `Max_Skirmish_Credits` | 8000 | **999999** |
| `MP_Default_Credits` | 6000 | **999999** |

---

## PLANETS.XML

Скрипт Python:

```python
re.subn(r'(<Planet_Credit_Value>)\d+(</Planet_Credit_Value>)', r'\g<1>99999\2', text)
```

**Результат:** 65 планет, кожна з `<Planet_Credit_Value>99999</Planet_Credit_Value>`.

Приклад:

```xml
<!-- Було -->
<Planet_Credit_Value>160</Planet_Credit_Value>

<!-- Стало -->
<Planet_Credit_Value>99999</Planet_Credit_Value>
```

---

## FACTIONS.XML

| Тег | Було (Rebel/Empire) | Стало |
|-----|---------------------|-------|
| `Credits_Accumulation_Factor` | 0.95 / 0.85 | **100.0** |
| `Maintenance_Cost` | 0.25 | **0.0** |
| `Space_Skirmish_Unit_Buy_Credits` | 100000 | **999999** |
| `Land_Skirmish_Unit_Buy_Credits` | 50000 | **999999** |

Нейтральні/службові фракції з `Maintenance_Cost>0.0` також отримали `Credits_Accumulation_Factor` = 100.0.

---

## EXPANSION_FACTIONS.XML

Аналогічні зміни для **Underworld** та суміжних фракцій FOC:

- `Credits_Accumulation_Factor` → 100.0  
- `Maintenance_Cost` → 0.0 (де було 0.25)  
- Skirmish credits → 999999  

---

## UNITS_HERO_UNDERWORLD_TYBER_ZANN.XML

```xml
<!-- Було -->
<Min_Respawn_Times>90.0, 90.0, 90.0, 90.0, 90.0</Min_Respawn_Times>
<Max_Respawn_Times>90.0, 90.0, 90.0, 90.0, 90.0</Max_Respawn_Times>

<!-- Стало -->
<Min_Respawn_Times>1.0, 1.0, 1.0, 1.0, 1.0</Min_Respawn_Times>
<Max_Respawn_Times>1.0, 1.0, 1.0, 1.0, 1.0</Max_Respawn_Times>
```

---

## Чого НЕ змінювали (свідомо)

| Що | Чому |
|----|------|
| 598× `Build_Cost_Credits` у MEG | потрібна масова розпаковка |
| `Damage_To_Armor_Mod` (тисячі рядків) | занадто тонкий rebalance |
| Lua сюжетні скрипти | сюжетна смерть героїв |
| `Config.meg` бінарно | ризик зламу архіву |

---

## Як відкотити зміни

1. Видалити або перейменувати `data2\Data\XML\` → гра візьме ваніль з MEG.
2. Або використати редактор: **«Відновити ваніль»** → **«Зберегти»**.
3. Або відновити файли `.bak_YYYYMMDD_HHMMSS`, якщо зберігали через редактор.

---

## Наступний документ

[06-PROBLEMA-PLAYER-ONLY.md](06-PROBLEMA-PLAYER-ONLY.md)
