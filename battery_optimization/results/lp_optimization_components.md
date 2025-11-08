# LP-Modellens Optimaliserings-Komponenter

## Hva Optimaliseres? (Objektiv-Funksjon)

LP-modellen minimerer **total månedlig kostnad**:

```
minimize: Σ(c_import[t] * P_grid_import[t] * Δt)    [Energikostnad import]
        - Σ(c_export[t] * P_grid_export[t] * Δt)    [Energi-inntekt eksport]
        + Σ(c_trinn[i] * z[i])                       [Effekttariff]
```

### ✅ Inkluderte Effekter:

#### 1. **Energikostnader (Spothandel)**
- **Import-kostnad**: `c_import[t]` = spotpris[t] + energiledd (0.296 eller 0.176 kr/kWh)
- **Eksport-inntekt**: `c_export[t]` = spotpris[t] - 0.01 kr/kWh (grid fee)
- **Tidsavhengig**: Peak hours (06:00-22:00) har høyere energiledd enn off-peak

**Resultat:** LP-modellen velger å:
- Importere når c_import er lavest (lave spotpriser + off-peak energiledd)
- Eksportere når c_export er høyest (høye spotpriser)
- Batteriet brukes til å flytte energi fra billige til dyre perioder

#### 2. **Effekttariffer (Power Tariff)**
- **Progressive brackets**: 10 trinn fra 2-100 kW med stigende kostnad
- **Månedsavhengig**: Høyeste time-import i måneden bestemmer kostnad
- **Modellering**: Binary variables `z[i]` aktiverer tariff-trinn inkrementelt

**Eksempel brackets:**
```
p_trinn: [2, 3, 5, 5, 5, 5, 25, 25, 25, 100] kW
c_trinn: [136, 96, 140, 200, 200, 200, 800, 800, 800, 2228] kr/mnd
```

**Resultat:** LP-modellen prøver å:
- Redusere månedlig peak import (bruke batteri til peak shaving)
- Unngå høye effekt-brackets (spesielt >50 kW som er veldig dyre)

#### 3. **Egetforbruk (Implisitt Optimert)**

Energy balance ligning:
```
PV + Grid_import + Battery_discharge = Load + Grid_export + Battery_charge
```

**Optimalisering:**
- Når PV > Load → Overskudd kan:
  - Lades i batteri (gratis, senere bruk)
  - Eksporteres til nett (spotpris - 0.01 kr/kWh)
- Når PV < Load → Underskudd dekkes av:
  - Batteri-utlading (tidligere lagret energi)
  - Grid-import (spotpris + energiledd)

**Resultat:** Egetforbruk optimaliseres automatisk fordi:
- Å bruke PV direkte = 0 kr/kWh
- Å eksportere og re-importere = taper på energiledd (0.296-0.176 kr/kWh) + grid fee (0.01 kr/kWh)
- Derfor vil LP alltid maksimere direkteforbruk

---

## ❌ IKKE Inkluderte Effekter

### 1. **Curtailment (Avskjæring)**

**Status:** ⚠️ IKKE modellert i nåværende versjon

**Hvorfor:**
- Grid export har **ubegrenset** bound: `(0, None)`
- Ingen penalty for overproduksjon
- Antar at nettet kan ta imot all eksport

**Implikasjon:**
- Med 150 kWp solceller kan produksjon være >100 kW
- I virkeligheten har mange nett eksportgrenser (f.eks. 77 kW)
- Overskytende produksjon må **curtailes** (kastes bort)

**Manglende optimalisering:**
- Batteriet burde lade mer aggressivt når curtailment truer
- Men LP-modellen ser ikke dette problemet

**Hvordan fikse:**
```python
# I bounds:
for _ in range(T):
    bounds.append((0, self.P_grid_export_limit))  # Legg til eksportgrense
```

### 2. **Grid Frequency Services / Regulerkraft**

Ikke modellert:
- FCR (Frequency Containment Reserve)
- FFR (Fast Frequency Response)
- mFRR/aFRR (manual/automatic Frequency Restoration Reserve)

### 3. **Battery Degradation Costs**

**Status:** ⚠️ IKKE inkludert i objektiv-funksjon

Battery cycling øker i 15-min oppløsning:
- Hourly: 44.5 cycles/month
- 15-minute: 48.0 cycles/month (+7.9%)

**Manglende kostnad:**
- Typisk degradation: 0.02-0.05 kr/kWh throughput
- Ekstra 3.5 cycles/month = ~100 kWh ekstra throughput
- Degradation cost: ~5-10 kr/måned

**Resultat:** 15-minute oppløsning kan være **overvurdert** med ~5-10 kr/måned hvis degradasjon inkluderes.

### 4. **Rampekostnader (Inverter Stress)**

Ikke modellert:
- Hyppige omslag mellom lading/utlading
- Inverter slitasje ved raske endringer
- Termisk stress på batteriet

---

## 🎯 Hva 15-Minutters Oppløsning Påvirker

### Direkte Effekter (Modellert):

| Komponent | Hvordan 15-min Påvirker |
|-----------|-------------------------|
| **Energikostnader** | Kan kjøpe/selge på intra-hour pris-spikerr |
| **Effekttariffer** | Kan redusere peak import gjennom raskere respons |
| **Egetforbruk** | Mer presis tilpasning til PV-produksjon |

### Indirekte Effekter (Ikke Modellert):

| Komponent | Hvordan 15-min Påvirker |
|-----------|-------------------------|
| **Curtailment** | Kunne redusere tap ved å lade før curtailment-grense |
| **Battery degradation** | Øker med flere sykluser (+7.9%) |
| **Inverter stress** | Øker med hyppigere omslag |

---

## 📊 Resultat-Analyse Med Denne Kunnskapen

### Oktober 2025 (30 kWh / 30 kW):

| Metric | Hourly | 15-min | Diff |
|--------|--------|--------|------|
| **Energikostnad** | 3,827 kr | 3,761 kr | **-66 kr** ✅ |
| **Effektkostnad** | 536 kr | 550 kr | **+14 kr** ⚠️ |
| **Total** | 4,363 kr | 4,310 kr | **-53 kr** |
| **Battery cycles** | 44.5 | 48.0 | **+3.5** ⚠️ |

### Tolkninger:

**1. Energikostnad Reduksjon (-66 kr):**
- 15-min kan fange intra-hour arbitrage
- Men trade-off: Mer import under peak hours gir høyere energiledd
- Netto gevinst: 66 kr/måned

**2. Effektkostnad Økning (+14 kr):**
- 15-min gir mer granulær peak shaving
- Men: Kan også skape høyere peaks ved aggressiv lading
- **Peak øker fra 19.14 kW → 19.63 kW**
- Dette betyr høyere tariff-bracket

**3. Battery Cycling (+7.9%):**
- Ikke reflektert i LP-objektiv
- **Skjult kostnad:** ~5-10 kr/måned degradation
- **Justert besparelse:** 53 kr - 7 kr = **~46 kr/måned**

**4. Curtailment (Ikke Relevant Her):**
- 150 kWp PV med 30 kW batteri
- Max PV produksjon i oktober: ~100 kW
- Hvis grid export limit = 77 kW:
  - Potential curtailment: 100 - 77 = 23 kW i peak hours
  - Batteriet kunne lagret 30 kW × 0.25h = 7.5 kWh per 15-min
  - **15-min kunne redusert curtailment betydelig**

---

## 🔍 Konklusjon

### LP-Modellen Optimaliserer:
✅ **Spot-arbitrage** (lave/høye priser)
✅ **Effekttariff-reduksjon** (peak shaving)
✅ **Egetforbruk** (implisitt gjennom energy balance)

### LP-Modellen Ignorerer:
❌ **Curtailment** (bør legges til for realistisk system)
❌ **Battery degradation** (cycling costs)
❌ **Inverter stress** (ramping costs)

### 15-Minutters Oppløsning Gir:
- ✅ **+66 kr/måned** fra bedre energi-arbitrage
- ⚠️ **-14 kr/måned** fra høyere peak import
- ⚠️ **~-7 kr/måned** fra økt battery degradation (ikke modellert)
- **Netto:** ~**46 kr/måned (1.1%)** realistisk gevinst

### Anbefaling:
For **små batterier (≤50 kWh)** med **moderat PV-system (≤150 kWp)**:
- **Timesoppløsning** er tilstrekkelig for planlegging
- **15-minutters oppløsning** gir <2% forbedring
- **Unntaket:** System med høy curtailment-risiko (PV >> grid limit)
  - Her kan 15-min redusere curtailment-tap betydelig
  - Bør modelleres eksplisitt med eksportgrense
