# 12. Довідник змін: файли, теги, коди читів

## A. Файли на диску гри

| Шлях | Статус | Опис |
|------|--------|------|
| `data2\Data\XML\GAMECONSTANTS.XML` | змінено | глобальні константи |
| `data2\Data\XML\PLANETS.XML` | додано/змінено | 65 планет × 99999 кредитів |
| `data2\Data\XML\FACTIONS.XML` | додано/змінено | Імперія + Повстанці |
| `data2\Data\XML\EXPANSION_FACTIONS.XML` | додано/змінено | Underworld (FOC) |
| `data2\Data\XML\UNITS_HERO_UNDERWORLD_TYBER_ZANN.XML` | змінено | респавн Tyber Zann |
| `data2\Data\XML\GRAPHICDETAILS.XML` | без змін | був у папці |
| `data2\Data\Config.meg` | **не чіпали** | оригінальний архів |

---

## B. GAMECONSTANTS — швидкий довідник тегів

### Бойові

```xml
<Object_Max_Health_Multiplier_Space> 99999.0 </Object_Max_Health_Multiplier_Space>
<Object_Max_Health_Multiplier_Land> 99999.0 </Object_Max_Health_Multiplier_Land>
<Elevated_Vulnerability_Factor>0.0</Elevated_Vulnerability_Factor>
<Space_Elevated_Vulnerability_Factor>0.0</Space_Elevated_Vulnerability_Factor>
<ShieldRechargeIntervalInSecs>0.01</ShieldRechargeIntervalInSecs>
<Under_Construction_Damage_Multiplier> 0.01 </Under_Construction_Damage_Multiplier>
<Default_Hero_Respawn_Time>1.0</Default_Hero_Respawn_Time>
```

### Економіка

```xml
<Political_Income_Curve>0,100, 1,100, 5,100</Political_Income_Curve>
<Progressive_Taxation>1,0, 5,0, 10,0</Progressive_Taxation>
<Income_Redistribution>0.0</Income_Redistribution>
<Credit_Cap_Per_Planet> 999999999.0 </Credit_Cap_Per_Planet>
<Black_Market_Income_Mult_Max>9999.0</Black_Market_Income_Mult_Max>
<MaxCreditIncomeAlignmentBonus>99.0</MaxCreditIncomeAlignmentBonus>
<MaxCreditIncomeAlignmentPenalty>0.0</MaxCreditIncomeAlignmentPenalty>
```

### Виробництво

```xml
<Production_Speed_Factor>100.0</Production_Speed_Factor>
```

### Скірміш

```xml
<Skirmish_Buy_Credits>999999</Skirmish_Buy_Credits>
<Min_Skirmish_Credits>999999</Min_Skirmish_Credits>
<Max_Skirmish_Credits>999999</Max_Skirmish_Credits>
<MP_Default_Credits>999999</MP_Default_Credits>
```

---

## C. FACTIONS / EXPANSION — теги

```xml
<Credits_Accumulation_Factor> 100.0 </Credits_Accumulation_Factor>
<Maintenance_Cost>0.0</Maintenance_Cost>
<Space_Skirmish_Unit_Buy_Credits> 999999 </Space_Skirmish_Unit_Buy_Credits>
<Land_Skirmish_Unit_Buy_Credits> 999999 </Land_Skirmish_Unit_Buy_Credits>
```

---

## D. PLANETS — тег

```xml
<Planet_Credit_Value>99999</Planet_Credit_Value>
```

×65 планет.

---

## E. Коди читів трейнера (внутрішні імена)

| Код `set_cheat(name, …)` | UI |
|--------------------------|-----|
| `credits` | Безлімітні кредити |
| `tactical_credits` | Тактичні ресурси |
| `god_mode` | Безсмертя |
| `no_cooldown` | Без перезарядки |
| `unit_cap` | Ліміт юнітів |
| `instant_build` | Миттєве будівництво |
| `free_build` | 1 кредит |
| `map_reveal` | Maphack |
| `fast_speed` | Швидкість x3 |
| `weak_enemies` | Слабкі вороги |
| `super_damage` | Урон x10 |

---

## F. Вихідні коди проєкту

| Файл | Клас / функція |
|------|----------------|
| `editor/app.py` | `EditorApp` |
| `trainer/app.py` | `TrainerApp` |
| `trainer/cheats.py` | `PlayerTrainer` |
| `trainer/scanner.py` | `MemoryScanner`, `pattern_scan_module` |
| `shared/xml_store.py` | `read_tag`, `write_tag`, `set_planet_credits` |
| `shared/process.py` | `attach`, `list_game_processes` |
| `shared/paths.py` | `find_game_root`, `xml_dir` |

---

## G. Змінні середовища

| Змінна | Ефект |
|--------|-------|
| `EAW_FOC_ROOT` | шлях до `data2` для редактора |

---

## Наступний документ

[13-OBMEZHENNYA.md](13-OBMEZHENNYA.md)
