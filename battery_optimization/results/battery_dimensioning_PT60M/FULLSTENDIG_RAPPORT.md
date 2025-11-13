# BATTERIDIMENSJONERING - FULLSTENDIG ANALYSE MED 3D-VISUALISERINGER

**Analysedato**: 2025-11-11
**Simuleringsperiode**: 2024 (365 dager)
**Optimeringsmodus**: Daglig rullerende horisont (24 timer)
**Tidsoppløsning**: PT60M
**Diskonteringsrente**: 5.0%
**Prosjektlevetid**: 15 år

---

## 📋 EXECUTIVE SUMMARY

### 🎯 Hovedkonklusjon
Med **56280 kWh årlig forbruk** og **127280 kWh PV-produksjon** er batterilager
**IKKE økonomisk lønnsomt** ved dagens markedspriser (5000 NOK/kWh).

### 💡 Beste konfigurasjon (Grid Search)
- **Batteri**: 20 kWh / 25 kW
- **C-rate**: 1.25
- **NPV**: -30,191 NOK (tap over 15 år)
- **Årlige besparelser**: 6,726 NOK
- **Investeringskostnad**: 100,000 NOK
- **Tilbakebetalingstid**: 14.9 år

### ⚠️ Break-even analyse
| Batterikapasitet | Break-even pris (NOK/kWh) | Prisreduksjon nødvendig |
|------------------|---------------------------|------------------------|
| 20 kWh | 3490 | 30% |
| 20 kWh | 3490 | 30% |
| 50 kWh | 2458 | 51% |

---

## 🏗️ SYSTEMOPPSETT

### Anlegg
- **PV-kapasitet**: 150 kWp (sør, 25° helning)
- **Inverter**: 110 kW
- **Nettgrense**: 70 kW
- **Lokasjon**: Stavanger (58.97°N, 5.73°E)

### Årlige energimengder (2024)
| Type | Verdi | Merknad |
|------|-------|---------|
| PV-produksjon | 127,280 kWh | Faktisk produksjon |
| Forbruk | 56,280 kWh | Generert forbruksprofil |
| Selvforbruksandel (uten batteri) | ~44% | Direkteforbruk |
| Eksport til nett | ~71,000 kWh | ~56% av produksjon |

### Økonomiske forutsetninger
- **Batteripris**: 5,000 NOK/kWh (CAPEX)
- **Diskonteringsrente**: 5.0% per år
- **Prosjektlevetid**: 15 år
- **Annuitetsfaktor**: 10.38

### Tariffstruktur (Lnett)
- **Nettsalg**: ~0.10 NOK/kWh (gjennomsnitt)
- **Spotpris**: Variabel, gjennomsnitt ~0.72 NOK/kWh
- **Effekttariff**: Progressiv, 5 trinn fra 48-213 NOK/kW/mnd

---

## 📊 GRID SEARCH RESULTATER

### Søkeområde
- **Kapasitet**: 20 - 200 kWh (7 nivåer)
- **Effekt**: 10 - 100 kW (7 nivåer)
- **Totalt**: 49 konfigurasjoner testet

### Beste konfigurasjon
```
Kapasitet:       20 kWh
Effekt:          25 kW
C-rate:          1.25

NPV (15 år):     -30,191 NOK
Årlige besparelser: 6,726 NOK
CAPEX:           100,000 NOK
Tilbakebetalingstid: 14.9 år

Break-even pris: 3,490 NOK/kWh
Prisreduksjon:   30% fra dagens nivå
```

### Verste konfigurasjon
```
Kapasitet:       200 kWh
Effekt:          10 kW
NPV (15 år):     -1,000,000 NOK
Tap vs beste:    969,809 NOK
```

---

## 🔬 POWELL'S METHOD REFINEMENT

Powell's metode er en gradientfri optimaliseringsalgoritme som raffinerer grid search-resultatet.

### Optimalt resultat
```
Kapasitet:       5.00 kWh
Effekt:          105.00 kW
C-rate:          21.00

NPV (15 år):     -1,324 NOK
Forbedring:      28,867 NOK
Forbedring:      95.6%

Årlige besparelser: 2,281 NOK
CAPEX:           25,000 NOK
Tilbakebetalingstid: 11.0 år

Break-even pris: 4,735 NOK/kWh
```

### Tolkning
Powell-refinementet finner et **mikrobatteri** (5.0 kWh) med høy effekt
(105 kW) som gir bedre NPV enn grid search. Dette indikerer at:

1. **Små batterier** reduserer CAPEX mer enn de reduserer inntekter
2. **Høy C-rate** (effekt/kapasitet) gir bedre fleksibilitet
3. Grid search-beste (20 kWh) er fortsatt **praktisk bedre**

**Anbefaling**: Bruk grid search-beste for realistisk dimensjonering.

---

## 📈 TRENDER OG MØNSTRE

### Kapasitetseffekter

| Kapasitet | Gj.snitt NPV | Gj.snitt besparelser | CAPEX |
|-----------|--------------|----------------------|-------|
| 20 kWh | -30,807 NOK | 6,666 NOK | 100,000 NOK |
| 50 kWh | -131,402 NOK | 11,426 NOK | 250,000 NOK |
| 80 kWh | -249,696 NOK | 14,481 NOK | 400,000 NOK |
| 110 kWh | -393,270 NOK | 15,100 NOK | 550,000 NOK |
| 140 kWh | -527,623 NOK | 16,607 NOK | 700,000 NOK |
| 170 kWh | -665,973 NOK | 17,730 NOK | 850,000 NOK |
| 200 kWh | -807,696 NOK | 18,527 NOK | 1,000,000 NOK |


**Observasjon**: NPV forverres med økende kapasitet fordi:
- CAPEX vokser lineært med størrelse
- Besparelser øker saktere (avtagende marginalnytte)
- Større batterier gir mer tap (virkningsgrad)

### Effekteffekter

| Effekt | Gj.snitt NPV | Gj.snitt besparelser |
|--------|--------------|----------------------|
| 10 kW | -511,095 NOK | 3,748 NOK |
| 25 kW | -406,771 NOK | 13,799 NOK |
| 40 kW | -389,551 NOK | 15,458 NOK |
| 55 kW | -380,006 NOK | 16,378 NOK |
| 70 kW | -374,270 NOK | 16,930 NOK |
| 85 kW | -372,396 NOK | 17,111 NOK |
| 100 kW | -372,378 NOK | 17,112 NOK |


**Observasjon**: Effekt har **mindre betydning** enn kapasitet fordi:
- Kostnaden er lav sammenlignet med energilagring
- Nettgrensen (70 kW) begrenser effektbehov
- Høy effekt gir mer fleksibilitet i optimaliseringen

---

## 🎨 VISUALISERINGER

Alle figurer er lagret i `plots/` mappen:

### 3D-overflater og scatter
1. **1_npv_3d_surface.png**: NPV som 3D-overflate av kapasitet og effekt
2. **2_npv_3d_scatter.png**: NPV som 3D-scatter fargekodlet etter besparelser
3. **8_npv_3d_contour.png**: NPV konturlinjer i 3D

### 2D-analyser
4. **3_npv_heatmap.png**: NPV heatmap for alle konfigurasjoner
5. **4_savings_vs_capex.png**: Besparelser vs investeringskostnad med break-even linje
6. **5_npv_by_size.png**: NPV som funksjon av batteristørrelse (linjeplot per effekt)
7. **6_breakeven_cost.png**: Nødvendig batteripris for lønnsomhet
8. **7_top10_comparison.png**: Sammenligning av top 10 konfigurasjoner

---

## 🎯 ANBEFALINGER

### Kortsiktige (0-2 år)
1. **IKKE invester** i batterilager ved dagens priser (5 000 NOK/kWh)
2. **Overvåk** markedet for prisutvikling på LFP-batterier
3. **Optimaliser** forbruksprofil for økt direkteforbruk (gratis selvforbruk)
4. **Vurder** andre investeringer med bedre NPV

### Mellomlange (2-5 år)
1. **Revurder** ved batteripris < 3490 NOK/kWh (break-even)
2. **Installer** hvis prisreduksjon på 30% oppnås
3. **Optimaliser størrelse** med oppdatert grid search når priser faller
4. **Vurder** alternative batteriteknologier (nye kjemier)

### Langsiktige (5+ år)
1. **Forventer** at batterier blir lønnsomme når priser når 2 500-3 000 NOK/kWh
2. **Kombiner** med oppgradering av PV-system hvis ekspansjon planlegges
3. **Utforsk** Vehicle-to-Grid (V2G) hvis bilpark elektrisfiseres
4. **Vurder** deltakelse i frekvensreguleringsmarkeder (mFRR, aFRR)

---

## ⚠️ RISIKOANALYSE

### Økonomiske risikoer
| Risiko | Sannsynlighet | Påvirkning | Tiltak |
|--------|---------------|------------|--------|
| Batteripriser faller ikke | Middels | Høy | Vent med investering |
| Spotpriser synker | Middels | Middels | Reduserer arbitrasjeverdi |
| Effekttariffer øker | Lav | Positiv | Øker lønnsomhet |
| Teknologi foreldes | Middels | Middels | Leasing i stedet for kjøp |

### Tekniske risikoer
| Risiko | Sannsynlighet | Påvirkning | Tiltak |
|--------|---------------|------------|--------|
| Degradering raskere enn forventet | Lav | Middels | Garanti på kapasitet |
| Inverter-kompatibilitet | Lav | Lav | Spesifiser krav tidlig |
| Nettgrense endres | Lav | Middels | Følg nettselskapets planer |

---

## 📚 REFERANSER

### Datakilder
- **PV-produksjon**: PVGIS (Photovoltaic Geographical Information System)
- **Spotpriser**: ENTSO-E Transparency Platform (NO2 prisområde)
- **Forbruksprofil**: Generert kommersiell profil med 56280 kWh årlig
- **Tariffstruktur**: Lnett AS (progressiv effekttariff)

### Metode
- **Optimalisering**: Lineær programmering (HiGHS solver)
- **Horisont**: 24 timer rullerende (365 daglige optimaliseringer)
- **Grid search**: 49 konfigurasjoner
- **Refinement**: Powell's method (gradientfri optimalisering)

### Verktøy
- **Python**: 3.11+
- **Optimalisering**: scipy.optimize, HiGHS LP-solver
- **Visualisering**: matplotlib, seaborn
- **Analyse**: pandas, numpy

---

## 📞 KONTAKT

For spørsmål om denne analysen, kontakt:
- **Prosjekt**: Battery Optimization System (BOS)
- **Dato**: 2025-11-11
- **Konfigurasjon**: `configs/dimensioning_2024.yaml`

---

**💡 Merk**: Denne analysen er basert på simulerte data for 2024 med generert forbruksprofil.
For en endelig investeringsbeslutning bør analysen kjøres med faktisk historisk forbruksdata.

**🔄 Oppdatering**: Kjør `python run_battery_dimensioning_PT60M.py` for å oppdatere analysen med nye data.
