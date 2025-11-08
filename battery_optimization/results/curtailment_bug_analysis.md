# Curtailment Bug i LP-Modellen

## 🐛 Funnet Bug

### Koden Sier:
```python
# Line 113: Les inn grid export limit
self.P_grid_limit = solar_config.grid_export_limit_kw  # 77 kW

# Line 266: Men bruker den for IMPORT!
bounds.append((0, self.P_grid_limit))  # P_grid_import ≤ 77 kW ❌ FEIL

# Line 269: Og export er ubegrenset!
bounds.append((0, None))  # P_grid_export ≤ ∞ ❌ FEIL
```

### Config Sier:
```python
grid_export_limit_kw: float = 77  # 70% of inverter (safety margin)
```

**Problemet:** Variabelen heter `grid_EXPORT_limit` men brukes til å begrense IMPORT!

---

## ✅ Hva Burde Skje

### Korrekt Implementasjon:
```python
# Import: Begrenset av nettkapasitet (typisk høy, f.eks. 100+ kW)
bounds.append((0, self.P_grid_import_limit))  # Kanskje 100 kW

# Export: Begrenset av inverter/grid agreement (77 kW)
bounds.append((0, self.P_grid_export_limit))  # 77 kW
```

### Hvorfor Dette Håndterer Curtailment Implisitt:

**Energy Balance Constraint:**
```
PV + Grid_import + Battery_discharge = Load + Grid_export + Battery_charge
```

**Scenario med Curtailment-Risiko:**
- PV produksjon: 100 kW
- Forbruk: 20 kW
- Overskudd: 80 kW

**Med Eksportgrense (77 kW):**
```
100 + 0 + 0 = 20 + Grid_export + Battery_charge
80 = Grid_export + Battery_charge
```

**LP-modellen kan:**
1. Export = 77 kW, Battery_charge = 3 kW → ✅ Ingen curtailment
2. Export = 50 kW, Battery_charge = 30 kW → ✅ Ingen curtailment (hvis batteri har plass)
3. **Hvis** Export ≤ 77 og Battery_charge ≤ 30:
   - Maks høyre side: 77 + 30 = 107 kW
   - Venstre overskudd: 80 kW
   - ✅ Kan alltid løses uten curtailment

**Med Ubegrenset Export (Nåværende Bug):**
- LP eksporterer 80 kW uten problemer
- Ser aldri curtailment-problemet
- Undervurderer batteriets verdi for curtailment-reduksjon

---

## 📊 Implikasjon for Analysen

### Scenario: Sommerdag
- PV peak: 120 kW (150 kWp system)
- Forbruk: 20 kW
- Overskudd: 100 kW
- Export limit: 77 kW
- **Curtailment:** 100 - 77 = 23 kW!

### Med 30 kWh / 30 kW Batteri:

**Uten Batteri:**
- Curtailment: 23 kW i 2-3 timer = ~50 kWh/dag tapt
- Tap: 50 kWh × 0.80 kr/kWh (spotpris) = **40 kr/dag**
- **Månedlig tap:** ~600-800 kr i sommermåneder

**Med Batteri (Korrekt Modellert):**
- Batteri lader 30 kW før curtailment
- Curtailment redusert til: 23 - 30 = 0 kW (helt eliminert hvis timing perfekt)
- **Batteriet sparer:** Opp til 600-800 kr/måned i sommer!

**Med Batteri (Nåværende Bug-versjon):**
- LP ser ikke curtailment-problemet
- Undervurderer batteriets verdi betydelig
- **Analysen mangler kanskje 500-1000 kr/måned** i sommersesong

---

## 🔧 Fix

### Option 1: Korrekt Bounds (Anbefalt)
```python
# In __init__:
self.P_grid_import_limit = 100.0  # Typisk høy nettkapasitet
self.P_grid_export_limit = solar_config.grid_export_limit_kw  # 77 kW

# In bounds:
bounds.append((0, self.P_grid_import_limit))  # Import
bounds.append((0, self.P_grid_export_limit))  # Export - NÅ BEGRENSET
```

### Option 2: Eksplisitt Curtailment-Variabel
```python
# Legg til ny variabel: P_curtail[t]
# Energy balance: PV - P_curtail + Import + Bat_discharge = Load + Export + Bat_charge
# Objektiv: Penaliser curtailment med høy kostnad
```

---

## 📈 Re-Run Analyse Med Fix

**Forventet endring:**
- **Timesoppløsning:** Vil se curtailment-problem, bruke batteri mer
- **15-minutters oppløsning:** Vil se curtailment MYE bedre, optimalisere timing
- **Forbedring fra 15-min:** Kanskje **5-10% i sommermåneder** (ikke 1%)

### Hvorfor 15-Min Hjelper Mer Med Curtailment:

**Timesoppløsning:**
- Ser curtailment-risiko i time 12:00-13:00
- Lader batteri i hele timen
- Men PV kan spike til 120 kW i 15-minutters perioder innenfor timen

**15-Minutters Oppløsning:**
- Ser at PV spikerr til 120 kW kl 12:15-12:30
- Kan lade batteri **akkurat før** peak
- Kan utlade **rett etter** peak for å maksimere eksport
- **Mye mer presis** curtailment-håndtering

---

## 🎯 Konklusjon

**Du hadde helt rett:**
- LP-modellen **burde** håndtere curtailment implisitt
- Men det er en **bug** i bounds-implementeringen
- Export er ubegrenset (feil)
- Grid limit brukes for import istedenfor export (feil)

**Når fikset:**
- Batteriverdien vil øke betydelig (spesielt sommer)
- 15-minutters oppløsning vil gi **mye større fordel** (5-10% vs 1%)
- Curtailment-reduksjon blir hoveddriveren, ikke spotpris-arbitrage

**Implikasjon:**
Med 150 kWp PV-system og 77 kW eksportgrense:
- **Nåværende analyse undervurderer batteriets verdi**
- **15-minutters fordel er sannsynligvis 5-10x større enn målt**
- **Curtailment-tap kan være 500-1000 kr/måned i sommer**

**Anbefaling:** Fiks export-bounds og kjør analysen på nytt, spesielt for sommermåneder!
