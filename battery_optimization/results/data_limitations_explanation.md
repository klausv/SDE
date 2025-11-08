# Databegrensninger: 15-Minutters Spotpriser

## 🚫 Realiteten: Ingen Historiske 15-Min Data

### Nord Pool Overgang:
- **Før 30. september 2025:** Kun **timesoppløsning (PT60M)**
- **Etter 30. september 2025:** **15-minutters oppløsning (PT15M)**

### ENTSO-E API:
- **Tilgjengelig:** Historiske timespriser (2020-2025)
- **IKKE tilgjengelig:** Historiske 15-minutters priser
- **Hvorfor:** Markedet har ikke handlet i 15-minutters intervaller før 30. sept 2025

---

## 📊 Hva Analysen Faktisk Bruker

### For Oktober 2025 (Sept 30 - Oct 31):
**Timesdata (PT60M):**
- ✅ Reelle data tilgjengelig (fra ENTSO-E)
- Men vi bruker **simulerte** priser i analysen

**15-minutters data (PT15M):**
- ❌ Reelle data finnes **IKKE**
- Vi bruker **simulerte** 15-minutters priser

### Simuleringmetode:
```python
def _generate_fallback_prices(self, year, area, resolution):
    """
    Genererer realistiske simulerte priser basert på NO2-mønstre:

    Timevariasjon:
    - Base pris: Sesong + time-av-dag + helg/hverdag
    - Intra-hour variasjon (for 15-min):
      - Tilfeldig +/- 10-15% innenfor hver time
      - Høyere volatilitet peak hours
      - Lavere volatilitet off-peak

    Statistisk kalibrert mot historiske NO2-data:
    - Mean: ~0.72 kr/kWh
    - Std: ~0.26 kr/kWh
    - Range: -0.05 til 3.0 kr/kWh
    """
```

**Intra-hour variasjon:**
- Hver time deles i 4x 15-minutters intervaller
- Tilfeldig variasjon rundt timesgjennomsnitt
- **Dette er IKKE realistisk markedsadferd**
- Reelle 15-min priser vil ha korrelerte mønstre

---

## ⚠️ Konsekvenser for Analysen

### 1. **Oktober-Analysen Er IKKE Basert På Reelle Data**
**Problem:**
- Både times og 15-min data er **simulerte**
- Ingen av resultatene er basert på faktiske markedspriser
- Simulering kan **ikke fange** reelle markedsdynamikker

**Implikasjon:**
- Resultatene (1% forbedring) er **ikke validerte**
- Kan være for høye eller for lave
- Usikkerhet: ±50-100%

### 2. **Ingen Sommermåneder Med 15-Min Data**
**Problem:**
- 15-minutters oppløsning starter 30. sept 2025
- **Juni-juli 2025:** Finnes ikke 15-min markedsdata
- **Juni-juli 2024:** Markedet handlet kun i timer

**Implikasjon:**
- Kan **IKKE** analysere sommerperioder med reelle 15-min priser
- Må vente til **sommer 2026** for reelle data
- Eller bruke **simulerte** data (lavere validitet)

### 3. **Simulerte Data Undervurderer/Overvurderer?**
**Usikkerhet:**
```
Simulering antar:
- Tilfeldig intra-hour variasjon
- Uavhengige 15-min priser innen hver time

Virkelighet har:
- Korrelerte intra-hour bevegelser
- Markeds-momentum og inertia
- Strategisk trading-adferd
- Kraftutveksling med Sverige/Danmark
```

**Resultat:**
- **Undervurderer** kanskje: Reelle markeder har mer persistent volatilitet
- **Overvurderer** kanskje: Reelle markeder har høyere autokorrelasjon

**Sannsynlig:** Simulering **overvurderer** arbitrage-muligheter
- Reelle 15-min priser er mer "smooth" (høy korrelasjon)
- Simulering har for mye tilfeldig støy

---

## ✅ Hva Kan Vi Gjøre?

### Alternativ 1: Bruk 2024 Reelle Timesdata + Simuler Intra-Hour
**Fremgangsmåte:**
```python
1. Hent reelle 2024 timesdata fra ENTSO-E (juni-juli)
2. For hver time, generer 4x 15-min variasjoner
3. Bruk historisk volatilitet fra time-til-time endringer
4. Kalibrerer intra-hour std basert på time-til-time std
```

**Fordel:**
- Basert på reelle spotpriser (ikke simulert)
- Realistisk time-struktur
- Validert sesongvariasjon

**Ulempe:**
- Intra-hour variasjon fortsatt simulert
- Kan ikke validere mot reelle 15-min priser (finnes ikke)

### Alternativ 2: Vent På Reelle Data (Sommer 2026)
**Fremgangsmåte:**
- Vent til juni-juli 2026
- Hent reelle 15-minutters spotpriser fra ENTSO-E
- Kjør analyse med faktiske markedsdata

**Fordel:**
- 100% reelle data
- Validert analyse

**Ulempe:**
- Må vente ~8 måneder

### Alternativ 3: Bruk Intraday-Data Som Proxy
**Fremgangsmåte:**
- ENTSO-E har intraday-markedsdata (høyere oppløsning)
- Bruk intraday-volatilitet som estimat for 15-min volatilitet
- Kalibrerer simulering mot intraday-mønstre

**Fordel:**
- Mer realistisk volatilitet
- Faktisk markedsadferd

**Ulempe:**
- Intraday ≠ day-ahead spotmarked
- Mer kompleks datainnhenting

---

## 🎯 Anbefaling

### For Din Analyse:

**1. Erkjenn Databegrensningen:**
- Oktober-analysen bruker **simulerte** priser
- Resultater er **ikke validerte** mot reelle markeder
- Usikkerhet: ±50-100%

**2. Beste Tilnærming (Kortsiktig):**
```python
# Bruk 2024 reelle timesdata + kalibrert intra-hour variasjon
1. Hent reelle juni-juli 2024 timesdata fra ENTSO-E
2. Analyser time-til-time volatilitet
3. Generer intra-hour variasjon proporsjonalt med time-volatilitet
4. Kjør sammenligning med denne metoden
```

**Fremgangsmåte:**
```python
# Mer realistisk intra-hour generering:
def generate_realistic_15min(hourly_prices):
    """
    Generer 15-min priser fra timesdata med realistisk variasjon
    """
    # Beregn time-til-time volatilitet
    hourly_std = hourly_prices.diff().std()

    # Intra-hour std er typisk 20-30% av time-til-time std
    intra_hour_std = hourly_std * 0.25

    prices_15min = []
    for hour_price in hourly_prices:
        # Generer 4x 15-min priser rundt timesgjennomsnitt
        # Med høyere korrelasjon (AR(1) prosess)
        quarter_prices = generate_correlated_variations(
            mean=hour_price,
            std=intra_hour_std,
            n=4,
            autocorr=0.7  # Høy korrelasjon innen time
        )
        prices_15min.extend(quarter_prices)

    return prices_15min
```

**3. Oppgi Usikkerhet:**
- Rapporter resultater som: "1% ± 50% (simulerte data)"
- Forklart at reelle data ikke finnes før sommer 2026
- Analysen er **indikativ**, ikke **validert**

**4. Fokuser På Curtailment (Mer Robust):**
- Curtailment-gevinst er **fysisk**, ikke markedsavhengig
- PV-produksjon kan måles/estimeres nøyaktig
- 70 kW nettgrense er kjent
- **15-min fordel for curtailment er mer forutsigbar**

---

## 📊 Konklusjon

**Fakta:**
- ❌ Ingen reelle 15-minutters spotpriser finnes før sept 2025
- ❌ Analysen bruker **simulerte** priser (både times og 15-min)
- ❌ Kan **ikke** validere sommermåneder med reelle data (må vente til 2026)

**Implikasjon:**
- ⚠️ Arbitrage-analyse (1% forbedring) er **ikke validert**
- ✅ Curtailment-analyse er mer robust (fysisk begrenset)
- ⚠️ Usikkerhet: Reell forbedring kan være 0.5-2% (ikke bare 1%)

**Anbefaling:**
1. Bruk 2024 reelle timesdata + kalibrert intra-hour variasjon
2. Fokuser på curtailment-gevinst (mer forutsigbar)
3. Vent på sommer 2026 for **validert** arbitrage-analyse
4. Rapporter resultater med høy usikkerhet (±50-100%)

**Hovedpoenget:**
For **curtailment-håndtering** (viktigst for 138 kWp system) er 15-minutters oppløsning **fysisk overlegen** uavhengig av spotpriser, fordi den kan se PV-spikerr og respondere raskere.
