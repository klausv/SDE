# Sammenligning av Batterianalyse-Resultater

## Hvorfor forskjellige resultater?

### 1. **Tidlig analyse (analyze_exact_system.py)** - PVGIS data
- **Produksjon**: 114 MWh/år (PVGIS med 14% tap)
- **Maks effekt**: ~67 kW
- **Timer > 70 kW**: 0
- **Break-even**: ~2,500 kr/kWh
- **Årlig inntekt**: ~15,000 kr
- **NPV @ 3000**: Svakt negativt

**Problem**: PVGIS undervurderer produksjon og har for lave topper

### 2. **Med "riktige tap" (analyse_riktige_tap.py)** - Justert for PVSol tap
- **Produksjon**: 133 MWh/år (PVSol-nivå)
- **Maks effekt**: 95-100 kW (antatt)
- **Timer > 70 kW**: 600-1200 (estimert)
- **Break-even**: 3,600 kr/kWh
- **Årlig inntekt**: ~20,000 kr
- **NPV @ 3000**: Svakt positivt/nær null

**Problem**: Overestimerte timer over 70 kW

### 3. **Realistisk PVSol (realistisk_pvsol_analyse.py)**
- **Produksjon**: 133 MWh/år
- **Maks effekt**: 85-95 kW
- **Timer > 70 kW**: 200-400
- **Break-even**: 2,500-2,800 kr/kWh
- **Årlig inntekt**: ~10,000 kr
- **NPV @ 3000**: -50,000 til -100,000 kr

**Forbedring**: Mer realistisk produksjonsprofil

### 4. **Final analyse (inntekt_final_analyse.py)** - Detaljert inntektsfordeling
- **Produksjon**: 133 MWh/år
- **Maks effekt**: 95 kW
- **Timer > 70 kW**: 330
- **Break-even**: < 300 kr/kWh (!!)
- **Årlig inntekt**: 737 kr (!!)
- **NPV @ 3000**: -368,000 kr

**Nytt funn**: Arbitrasje gir NEGATIV inntekt (-302 kr/år)

## Hovedforskjeller:

### Inntektskilder (tidligere vs nå):

**Tidligere antakelser:**
- Effekttariff reduksjon: 10,000-12,000 kr/år
- Arbitrasje: 3,000-5,000 kr/år
- Unngått kutting: 5,000-10,000 kr/år

**Faktiske tall (final analyse):**
- Effekttariff reduksjon: 0 kr/år (!)
- Arbitrasje: -302 kr/år (NEGATIV!)
- Unngått kutting: 765 kr/år
- Total: 737 kr/år

## Hvorfor så store avvik?

### 1. **Effekttariff (0 kr i stedet for 10,000 kr)**
- **Tidligere**: Antok batteriet ville redusere døgnmaks betydelig
- **Nå**: Batteriet er for lite til å påvirke import-topper (55-75 kW)
- **Problem**: Last-toppene skjer når PV=0, batteriet tømmes fort

### 2. **Arbitrasje (NEGATIV i stedet for positiv)**
- **Tidligere**: Antok høy prisvolatilitet
- **Nå**: Reell NO2 volatilitet er lav (std 0.23 kr/kWh)
- **Problem**: 10% tap ved lading/utlading > prisforskjeller

### 3. **Kutting (765 kr i stedet for 5,000-10,000 kr)**
- **Tidligere**: Overestimerte timer > 70 kW (antok 1000+ timer)
- **Nå**: Realistisk 330 timer > 70 kW
- **Problem**: Mindre kutting å unngå enn antatt

## Konklusjon:

De tidlige analysene var **for optimistiske** fordi de:
1. Overestimerte effekttariff-reduksjon
2. Antok lønnsom arbitrasje (som faktisk er negativ)
3. Overestimerte kuttet produksjon

Den siste analysen viser at batteriet kun tjener ~700 kr/år, hovedsakelig fra unngått kutting. Dette er langt under avskrivningskostnaden på ~25,000 kr/år.

**Reell break-even: < 300 kr/kWh** (17x lavere enn markedspris!)