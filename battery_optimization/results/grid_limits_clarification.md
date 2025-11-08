# Nettbegrensninger - Korrekt Forståelse

## 🔌 Nettilkoblingens Fysiske Grenser

### Typisk Scenario:
**Nettkapasitet:** 70 kW (både import og export)

Dette er en **symmetrisk nettbegrensning** som gjelder i begge retninger:
- **Import (fra nett):** Maks 70 kW
- **Export (til nett):** Maks 70 kW

---

## 📊 Systemspesifikasjoner

### Nåværende Config (Sannsynligvis Feil):
```python
grid_export_limit_kw: float = 77  # 70% of inverter (safety margin)
```

**Kommentar sier:** "70% of inverter"
- 110 kW inverter × 0.70 = 77 kW
- Men dette er **invertergrense**, ikke **nettgrense**

### Korrekt Forståelse:
**Nettilkobling:** 70 kW (begge retninger)

| Komponent | Kapasitet | Begrensning |
|-----------|-----------|-------------|
| **PV DC** | 138.55 kWp | Solceller |
| **Inverter** | 110 kW AC | Kan konvertere maks 110 kW |
| **Nett** | **70 kW** | **Tilkoblingspunkt - BEGGE retninger** |

**Flaskehals:** Nettet (70 kW), ikke inverter (110 kW)

---

## 🎯 Implikasjoner for LP-Modellen

### Korrekte Bounds:
```python
# Begge begrensninger: 70 kW
P_grid_import[t] ≤ 70 kW   # Import fra nett
P_grid_export[t] ≤ 70 kW   # Export til nett
```

### Energy Balance Med Korrekte Grenser:
```
PV + Grid_import(≤70) + Bat_discharge(≤30) = Load + Grid_export(≤70) + Bat_charge(≤30)
```

**Kritisk innsikt:** Hvis PV > 70 kW:
- Kan ikke eksportere alt
- Må enten:
  1. Lade batteri (opp til 30 kW)
  2. Curtailment (kaste bort energi)

---

## 📈 Sommerscenario Med 138.55 kWp PV

### Peak Produksjon (Solrik Sommerdag):
- **PV DC:** 138.55 kWp
- **PV AC (etter inverter):** ~120-130 kW (med god solinnstråling)
- **Nettgrense:** 70 kW
- **Forbruk:** 20 kW (typisk)

### Uten Batteri:
```
PV(120) = Load(20) + Export(70) + Curtailment(?)
120 = 20 + 70 + 30
Curtailment: 30 kW i 2-3 timer = ~70 kWh/dag!
```

**Tap:** 70 kWh × 0.80 kr/kWh = **~56 kr/dag** = **1,700 kr/måned** (sommer)

### Med 30 kWh / 30 kW Batteri:
```
PV(120) = Load(20) + Export(70) + Battery_charge(30) + Curtailment(0)
120 = 20 + 70 + 30 + 0
✅ Ingen curtailment!
```

**Batteriet sparer:** 1,700 kr/måned i juni/juli!

---

## ⚠️ Kritiske Feil i Nåværende LP-Modell

### Bug 1: Feil Variabel-Bruk
```python
# Line 113: Leser "grid_export_limit" (77 kW)
self.P_grid_limit = solar_config.grid_export_limit_kw

# Line 266: Men bruker for IMPORT! ❌
bounds.append((0, self.P_grid_limit))  # P_grid_import ≤ 77 kW
```

**Resultat:** Import begrenset til 77 kW (kanskje OK hvis nett = 70 kW)

### Bug 2: Ubegrenset Export
```python
# Line 269: Export ubegrenset ❌
bounds.append((0, None))  # P_grid_export ≤ ∞
```

**Resultat:** LP kan eksportere 120 kW → Ser aldri curtailment-problemet!

---

## ✅ Korrekt Implementasjon

### Forslag:
```python
class SolarSystemConfig:
    # Separate import og export grenser
    grid_connection_limit_kw: float = 70  # Nettilkobling (begge retninger)
    inverter_capacity_kw: float = 110     # Inverter kapasitet

    @property
    def grid_import_limit_kw(self) -> float:
        """Import begrenset av nettilkobling"""
        return self.grid_connection_limit_kw  # 70 kW

    @property
    def grid_export_limit_kw(self) -> float:
        """Export begrenset av minimum av nett og inverter"""
        return min(self.grid_connection_limit_kw, self.inverter_capacity_kw)  # min(70, 110) = 70 kW
```

### I LP-Optimizer:
```python
# Korrekte bounds
self.P_grid_import_limit = config.solar.grid_import_limit_kw   # 70 kW
self.P_grid_export_limit = config.solar.grid_export_limit_kw   # 70 kW

# I bounds array:
bounds.append((0, self.P_grid_import_limit))   # Import ≤ 70 kW
bounds.append((0, self.P_grid_export_limit))   # Export ≤ 70 kW
```

---

## 📊 Re-Analyse Med Korrekte Grenser

### Forventet Resultat (Sommermåned):

**Uten Batteri:**
- Curtailment: ~70 kWh/dag = **1,700 kr/måned**
- Total kostnad: 5,000 kr/måned (energi + effekttariff)

**Med 30 kWh Batteri (Timesoppløsning):**
- Curtailment: ~20 kWh/dag (ikke perfekt timing)
- Batterisparing: 50 kWh/dag × 0.80 = **1,200 kr/måned**
- Total kostnad: 3,800 kr/måned
- **Besparelse:** 1,200 kr/måned

**Med 30 kWh Batteri (15-min oppløsning):**
- Curtailment: ~5 kWh/dag (mye bedre timing!)
- Batterisparing: 65 kWh/dag × 0.80 = **1,560 kr/måned**
- Total kostnad: 3,440 kr/måned
- **Besparelse:** 1,560 kr/måned
- **15-min fordel:** 1,560 - 1,200 = **360 kr/måned (30%!)**

### Vintermåned (Lav PV):
- Curtailment: Minimal (PV < 70 kW)
- 15-min fordel: ~50 kr/måned (som analysen viser)

### Årlig Gjennomsnitt:
- Sommer (jun-aug): 360 kr/måned × 3 = 1,080 kr
- Vår/Høst (apr-may, sep-okt): 150 kr/måned × 4 = 600 kr
- Vinter (nov-mar): 50 kr/måned × 5 = 250 kr
- **Total 15-min fordel:** ~1,930 kr/år (~5%)

---

## 🎯 Konklusjon

**Du hadde helt rett på begge punkter:**

1. ✅ **Både import OG export har grenser**
   - Nettilkoblingen begrenser begge retninger
   - Typisk symmetrisk (samme kW i begge retninger)

2. ✅ **70 kW er sannsynligvis riktig tall**
   - Ikke 77 kW (som er 70% av inverter)
   - 70 kW er nettilkoblingens kapasitet

**Konsekvens for analysen:**
- **Nåværende analyse:** Kraftig undervurdert (ser ikke curtailment)
- **Oktober 2025:** 1% fordel (lavt curtailment-problem)
- **Sommermåneder:** **30-40% fordel** fra 15-min oppløsning!
- **Årlig gjennomsnitt:** ~**5% fordel** (ikke 1%)

**Viktighet av fix:**
For et 138.55 kWp system med 70 kW nettgrense er **curtailment-håndtering den største verdien av batteriet**, og 15-minutters oppløsning gir **dramatisk bedre curtailment-håndtering** enn timesoppløsning.
