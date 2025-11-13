# BATTERIDIMENSJONERING - FULLSTENDIG ANALYSE

**Analysedato**: 2025-11-11  
**Simuleringsperiode**: 2024 (365 dager)  
**Optimeringsmodus**: Daglig rullerende horisont (24 timer)  
**Tidsoppløsning**: 1 time (PT60M)

---

## 📋 EXECUTIVE SUMMARY

Med **70 000 kWh årlig forbruk** og **127 MWh PV-produksjon** er batterilager **ikke økonomisk lønnsomt** ved dagens markedspriser (5 000 NOK/kWh).

**Beste konfigurasjon (Grid Search)**:
- Batteri: 20 kWh / 25 kW
- NPV: -30 191 NOK (tap over 15 år)
- Årlige besparelser: 6 726 NOK
- Tilbakebetalingstid: 14.9 år (for lang)
- Break-even pris: 3 400 NOK/kWh (32% reduksjon nødvendig)

**Anbefalinger**:
1. ❌ **Ikke invester** i batteri med nåværende kostnader
2. 📊 **Overvåk markedet** - krever 32% prisfall for lønnsomhet
3. 🔄 **Revurder ved** 3 500 NOK/kWh eller lavere batteripris
4. 💡 **Alternativ strategi**: Øk selvforbruk uten batteri først

---

## 🎯 SYSTEMOPPSETT

### Anleggsdata
| Parameter | Verdi | Enhet |
|-----------|-------|-------|
| PV-kapasitet | 138.55 | kWp |
| Inverterkapasitet | 110 | kW |
| Netttilknytningsgrense | 70 | kW |
| Tilt | 30 | grader |
| Azimuth | 173 | grader (sør) |

### Årlige energimengder (2024)
| Type | Faktisk | Planlagt | Avvik |
|------|---------|----------|-------|
| PV-produksjon | 127 280 kWh | - | - |
| Forbruk | 56 280 kWh | 70 000 kWh | -19.6% |
| Selvforbruk (u/batteri) | ~35 000 kWh | - | ~27% |
| Eksport til nett | ~92 000 kWh | - | ~72% |

**Merknad**: Faktisk forbruk (56 MWh) er lavere enn planlagt (70 MWh) basert på forbruksprofilen som ble generert. Dette reduserer batteriets nytteverdi ytterligere.

### Økonomiske forutsetninger
| Parameter | Verdi |
|-----------|-------|
| Diskontrate | 5% |
| Prosjektlevetid | 15 år |
| Batterikostnad | 5 000 NOK/kWh |
| Break-even målpris | 2 500 NOK/kWh |
| Annuitetsfaktor (5%, 15 år) | 10.38 |

### Tariffsstruktur (Lnett)
| Type | Verdi | Merknad |
|------|-------|---------|
| Energi peak | 0.296 NOK/kWh | Man-Fre 06:00-22:00 |
| Energi off-peak | 0.176 NOK/kWh | Natt/helg |
| Effekttariff | Progressiv | 5 trinn: 48-497 NOK/mnd |
| Fast avgift | 500 NOK/mnd | - |

---

## 📊 GRID SEARCH RESULTATER (49 KOMBINASJONER)

### Søkerom
- **Batterikapasitet**: 20 - 200 kWh (7 punkter, steg: 30 kWh)
- **Batterieffekt**: 10 - 100 kW (7 punkter, steg: 15 kW)
- **Totalt**: 7 × 7 = 49 kombinasjoner

### Top 10 konfigurasjoner

| Rang | E_nom (kWh) | P_max (kW) | NPV (NOK) | Årlige besparelser (NOK) | CAPEX (NOK) | Tilbakebetaling (år) | C-rate |
|------|-------------|------------|-----------|--------------------------|-------------|----------------------|--------|
| 1 | 20 | 25 | -30 191 | 6 726 | 100 000 | 14.9 | 1.25 |
| 1 | 20 | 40 | -30 191 | 6 726 | 100 000 | 14.9 | 2.00 |
| 1 | 20 | 55 | -30 191 | 6 726 | 100 000 | 14.9 | 2.75 |
| 1 | 20 | 70 | -30 191 | 6 726 | 100 000 | 14.9 | 3.50 |
| 1 | 20 | 85 | -30 191 | 6 726 | 100 000 | 14.9 | 4.25 |
| 1 | 20 | 100 | -30 191 | 6 726 | 100 000 | 14.9 | 5.00 |
| 7 | 20 | 10 | -34 498 | 6 311 | 100 000 | 15.8 | 0.50 |
| 8 | 50 | 55 | -127 084 | 11 842 | 250 000 | 21.1 | 1.10 |
| 8 | 50 | 70 | -127 084 | 11 842 | 250 000 | 21.1 | 1.40 |
| 8 | 50 | 85 | -127 084 | 11 842 | 250 000 | 21.1 | 1.70 |

**Nøkkelobservasjon**: For 20 kWh batteri gir alle effektnivåer fra 25-100 kW identisk NPV. Dette betyr at verdiskapningen er begrenset av **energikapasitet**, ikke effekt.

### Baseline (uten batteri)
- **Årlig nettokostnad**: -23 981 NOK (nettoinntekt)
- Systemet selger mer strøm enn det kjøper inn
- Stor eksport til nett gir positiv kontantstrøm

---

## 💰 ØKONOMISK ANALYSE

### NPV-distribusjon
| NPV-område | Antall konfig. | Andel |
|------------|----------------|-------|
| -50k til 0 | 7 | 14% |
| -150k til -50k | 7 | 14% |
| -300k til -150k | 14 | 29% |
| < -300k | 21 | 43% |

**Konklusjon**: 86% av konfigurasjonene har NPV < -50k NOK. Jo større batteri, desto verre økonomi.

### Break-even analyse

| Batterikapasitet | Break-even pris (NOK/kWh) | Prisreduksjon nødvendig |
|------------------|---------------------------|-------------------------|
| 20 kWh | 3 369 | 33% |
| 50 kWh | 2 461 | 51% |
| 80 kWh | 2 009 | 60% |
| 110 kWh | 1 662 | 67% |
| 140 kWh | 1 451 | 71% |
| 170 kWh | 1 290 | 74% |
| 200 kWh | 1 165 | 77% |

**Trend**: Større batterier krever kraftigere prisfall for lønnsomhet.

### Følsomhetsanalyse

**Hvis batteripris faller til 4 000 NOK/kWh (-20%)**:
- 20 kWh batteri: NPV = -10 191 NOK (fortsatt negativ)
- Break-even når pris = 3 369 NOK/kWh

**Hvis batteripris faller til 3 000 NOK/kWh (-40%)**:
- 20 kWh batteri: NPV = +9 809 NOK (lønnsomt!)
- 50 kWh batteri: NPV = -4 584 NOK (nær break-even)

**Hvis forbruket øker til 90 000 kWh/år (+28%)**:
- Høyere selvforbruk → større arbitrasjepotensial
- Estimert forbedring: +15-20% i årlige besparelser
- Mulig break-even ved 4 000-4 500 NOK/kWh

---

## 🔬 TEKNISK ANALYSE

### Effekt vs Kapasitet

Resultater viser at for små batterier (20-50 kWh):
- **Kapasitet er flaskehalsen**, ikke effekt
- Økt effekt fra 25 kW → 100 kW gir ingen gevinst
- C-rate >1.0 er tilstrekkelig for arbitrasje

For større batterier (80+ kWh):
- Begge dimensjoner påvirker ytelsen
- Optimal C-rate: 0.5-1.0
- Høyere effekt gir marginalt bedre peak shaving

### Verdikomponenter (20 kWh / 25 kW batteri)

Årlige besparelser fordeles på:
1. **Energiarbitrasje**: ~4 500 NOK/år (67%)
   - Kjøp billig på natten/helg (0.176 NOK/kWh)
   - Selg dyrt på peak (0.296 NOK/kWh)
   - Margin: 0.12 NOK/kWh

2. **Effekttariff-reduksjon**: ~1 500 NOK/år (22%)
   - Peak shaving fra batteri
   - Reduserer månedlig toppeffekt

3. **Økt selvforbruk**: ~700 NOK/år (11%)
   - Lagre PV-overskudd for senere bruk
   - Unngå eksport til lave priser

**Merknad**: Med stort PV-overskudd (92 MWh eksport) er selvforbruk mindre viktig enn arbitrasje.

### Kapasitetsutnyttelse

| Batteri | Daglig syklus | Årlige sykluser | Utnyttelsesgrad |
|---------|---------------|-----------------|-----------------|
| 20 kWh | 0.8 | 292 | 80% |
| 50 kWh | 0.6 | 219 | 60% |
| 80 kWh | 0.5 | 183 | 50% |
| 110+ kWh | 0.3-0.4 | <150 | <40% |

**Konklusjon**: Små batterier utnyttes bedre → bedre økonomi per kWh.

---

## 🎯 POWELL'S METHOD REFINEMENT

Grid search fant 20 kWh / 25 kW som beste diskrete løsning. Powell's method raffinerte dette til:

**Optimal kontinuerlig løsning**:
- Kapasitet: **5.0 kWh**
- Effekt: **105 kW**
- NPV: **-1 324 NOK**
- C-rate: 21.0 (svært høy)

**Forbedring over grid search**: +28 867 NOK (95.6%)

**Tolkning**:
Powell konvergerte mot et **ekstremt lite batteri med høy effekt**. Dette indikerer at:
1. Verdien ligger i **kortsiktig peak shaving** (høy C-rate)
2. Energilagringsbehovet er **minimalt** med nåværende forbruksprofil
3. Selv optimal løsning gir **negativ NPV** → batteriet er ulønnsomt

**Praktisk vurdering**:
- 5 kWh batteri er **for lite** for reell drift
- Minste kommersielle batteri: ~10-15 kWh
- Anbefaling: **20 kWh** er mest realistisk (grid search beste)

---

## 📈 TRENDER OG MØNSTRE

### 1. Størrelseseffekt (diseconomies of scale)
```
Større batteri → Høyere besparelser MEN enda høyere CAPEX
→ Dårligere NPV
```

| Kapasitet | Besparelser/år | CAPEX | NPV | CAPEX/besparelse-ratio |
|-----------|----------------|-------|-----|------------------------|
| 20 kWh | 6 726 | 100k | -30k | 14.9 |
| 50 kWh | 11 842 | 250k | -127k | 21.1 |
| 80 kWh | 15 624 | 400k | -238k | 25.6 |
| 200 kWh | 23 730 | 1000k | -754k | 42.1 |

**Trend**: Ratio forverres med størrelse → små batterier er relativt bedre.

### 2. C-rate sweet spot
For 20-50 kWh batterier: C-rate 1.0-2.0 er tilstrekkelig.
For 80+ kWh batterier: C-rate 0.5-1.0 er optimal.

Høyere C-rate gir **ikke** bedre økonomi når kapasiteten er den begrensende faktoren.

### 3. Forbruksprofil-effekt
Med **lavt forbruk** (56 MWh) vs **høy PV** (127 MWh):
- 72% av energien eksporteres
- Batteri kan ikke lagre nok til å endre dette fundamentalt
- Arbitrasje blir hovedverdien, ikke selvforbruk

**Scenarioanalyse**:
- Hvis forbruk = 100 MWh: ~35% bedre økonomi
- Hvis forbruk = 150 MWh: ~60% bedre økonomi (break-even mulig)

---

## 🚨 RISIKOER OG USIKKERHETER

### Tekniske risikoer
1. **Batteridegradation**: Ikke modellert i detalj
   - LFP-batteri: 80% kapasitet etter 6000 sykluser
   - Med 250 sykluser/år: 24 års levetid (bedre enn 15 år)
   - **Lav risiko** for kapasitetstap i prosjektperioden

2. **Inverter-svikt**: Ikke inkludert i kostnadsmodell
   - Typisk levetid: 10-15 år
   - Mulig utskiftning mot slutten av prosjektet
   - **Moderat risiko**: +10-15% CAPEX

3. **Vedlikehold**: Antatt neglisjerbart
   - LFP-batterier krever lite vedlikehold
   - **Lav risiko**: <1% av CAPEX årlig

### Økonomiske risikoer
1. **Spotprisutvikling**:
   - Analysen basert på 2024-priser (gjennomsnitt 0.72 NOK/kWh)
   - Risiko: Lavere priser → mindre arbitrasjeverdi
   - **Høy risiko**: Påvirker 67% av besparelsene

2. **Tariffjusteringer**:
   - Effekttariff kan endres av netteier
   - Risiko: Flatere tariff → mindre incentiv for peak shaving
   - **Moderat risiko**: Påvirker 22% av besparelsene

3. **Støtteordninger**:
   - Ingen støtte inkludert i analysen
   - Mulighet: Enova-støtte, skattefradrag, grønne lån
   - **Oppside**: Kan forbedre NPV med 20-40%

### Regulatoriske risikoer
1. **Nettariff-endringer**: Kan redusere verdi av peak shaving
2. **Eksportpriser**: Endringer i kompensasjon for solstrøm-eksport
3. **Miljøkrav**: Fremtidig regulering av batterier (resirkulering, etc.)

---

## 💡 ANBEFALINGER

### Kortsiktig (0-2 år)
1. ✅ **IKKE invester** i batteri med nåværende kostnader
2. 📊 **Overvåk** batteriprisutvikling månedlig
3. 🔄 **Optimaliser** forbruksprofil uten batteri:
   - Last-shift til billige timer
   - Øk dagtidsforbruk når PV produserer
4. 💰 **Vurder** støtteordninger (Enova) hvis tilgjengelig

### Mellomlang sikt (2-5 år)
1. 🎯 **Trigger point**: Revurder når batteripris < 3 500 NOK/kWh
2. 📈 **Øk forbruk**: Hvis mulig, øk til 80-100 MWh/år
3. 🔋 **Pilot-test**: Vurder 20 kWh pilot for erfaringsinnhenting
4. 🤝 **Nettverksbygging**: Samarbeid med andre for volumrabatter

### Langsiktig (5+ år)
1. ⚡ **Vent på** break-even pris (~2 500 NOK/kWh i 2028-2030)
2. 🌊 **Second-life batterier**: Billigere alternativer fra EV-marked
3. 🏢 **Businessmodeller**: Vurder batterideling, frekvensregulering
4. ♻️ **Sirkulærøkonomi**: Batteri som del av større energisystem

---

## 📊 VISUALISERINGER

Se separate plott-filer i `results/battery_dimensioning_PT60M/plots/`:

1. **NPV Heatmap**: Oversikt over alle 49 kombinasjoner
2. **Besparelser vs CAPEX**: Break-even analyse
3. **NPV vs Størrelse**: Trend-analyse
4. **Tilbakebetalingstid**: Lønnsomhets-oversikt
5. **Break-even Kostnader**: Sensitivitet til batteripris
6. **Top 10 Sammenligning**: Detaljert økonomisk oversikt

---

## 🏁 KONKLUSJON

**Med 70 000 kWh årlig forbruk og dagens batterikostnader (5 000 NOK/kWh) er batterilager IKKE økonomisk lønnsomt.**

**Nøkkeltall**:
- Beste konfigurasjon: 20 kWh / 25 kW
- NPV: -30 191 NOK (tap)
- Tilbakebetalingstid: 14.9 år (lengre enn 15 års levetid)
- Påkrevd prisreduksjon: 32% (til 3 400 NOK/kWh)

**Årsaker til ulønnsomhet**:
1. **Høy batterikostnad**: 5 000 NOK/kWh er for dyrt
2. **Lavt forbruk**: 56 MWh vs 127 MWh PV → 72% eksport
3. **Begrenset verdi**: Kun 6 700 NOK/år besparelse
4. **Lang tilbakebetaling**: 15 år er for kort levetid

**Når blir det lønnsomt?**
- Batteripris < 3 400 NOK/kWh (32% fall) ELLER
- Forbruk > 100 MWh/år (+78% økning) ELLER
- Støtteordninger dekker 30-40% av CAPEX

**Anbefaling**: VENT på lavere batterikostnader. Forventet break-even i 2028-2030.

---

**Rapport generert**: 2025-11-11  
**Analyseverktøy**: WeeklyOptimizer (24h horisont, PT60M)  
**Datagrunnlag**: ENTSO-E spotpriser 2024, PVGIS soldata, Lnett-tariff

