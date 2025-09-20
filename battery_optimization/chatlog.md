# Battery Optimization Analysis - Chat Log
**Date**: 2025-01-20
**Project**: Snødevegen 122, Tananger - 138.55 kWp Solar Installation
**Location**: 58.929644°N, 5.623052°E

## Conversation Summary

This conversation focused on battery optimization for a 138.55 kWp solar installation with the following constraints:
- 100 kW inverter limit
- 70 kW grid export limit
- 133 MWh/year production (959.78 kWh/kWp per PVSol)
- NO2 spot prices and Lnett tariffs

### Key Findings

1. **Optimal Battery Configuration**: 30 kWh / 30 kW (or 30 kWh / 15 kW with realistic losses)
2. **Break-even Battery Cost**: 2,500-3,600 kr/kWh depending on loss assumptions
3. **Current Market Price**: 5,000-6,000 kr/kWh (1.4-2.4x above break-even)
4. **Conclusion**: Batteries not economically viable at current prices

### Important Technical Points

- PVSol (by Ares) provides more accurate estimates than PVGIS
- Actual system losses ~7% (not 14% PVGIS default)
- PVSol shows 959.78 kWh/kWp vs PVGIS 826 kWh/kWp
- Minimal curtailment with 70 kW grid limit

## Full Conversation Log

### Initial Request
User requested battery optimization analysis for their solar installation at Snødevegen 122, Tananger.

### System Specifications Provided
- PV System: 138.55 kWp
- Inverter: 100 kW limit
- Grid Connection: 70 kW export limit
- Annual Production: 133,017 kWh (from PVSol)
- Location: 58.929644°N, 5.623052°E
- Tilt: 15°, Azimuth: 171° (South)

### Analysis Scripts Created

1. **analyze_exact_system.py** - Main comprehensive analysis
2. **pvgis_exact_location.py** - PVGIS data fetching with exact coordinates
3. **analyse_riktige_tap.py** - Analysis with corrected (lower) system losses
4. **realistisk_pvsol_analyse.py** - Realistic analysis based on PVSol data
5. **endelig_analyse_pvsol.py** - Final analysis with PVSol production values
6. **sammenlign_pvgis_pvsol.py** - Comparison between PVGIS and PVSol
7. **test_pvgis_direkte.py** - Direct PVGIS API testing

### Key User Feedback Points

1. **On PVSol accuracy**: "pvgis har sjablongmessige tap, mens pvsol som er laget av Are har en track record på at estimatene er svært så samsvarende med målte verdier"

2. **On production validation**: User pointed out discrepancy - "jeg tror du har lavere produksjon (ref dc-siden) enn de har?"

3. **On system losses**: "har du tatt høyde for at tapene ikke er så store som de sjablongmessige tapene pvgis bruker"

4. **Request for battery pricing**: "kan du lete gjennom /mnt/c/Users/klaus/NorskSolkraft AS/Gruppeområde - Documents/10 Prosjekter/2025 Tilbud for å se om vi har tilbudt batteripakker"

5. **Language preference**: "fortsett samtalen på norsk er du snill"

6. **Documentation request**: "kan du logge hele denne chatten i chatlog.md?"

### Economic Analysis Results

#### With PVGIS Data (14% losses, 826 kWh/kWp):
- NPV @ 3000 kr/kWh: **-222,000 kr** (negative)
- Break-even: ~2,500 kr/kWh
- Best config: 30 kWh / 30 kW

#### With Corrected Losses (7%, ~960 kWh/kWp):
- NPV @ 3000 kr/kWh: **-50,000 to -100,000 kr** (still negative)
- Break-even: ~2,800-3,600 kr/kWh
- Higher curtailment value due to more hours >70 kW

### Revenue Streams Analyzed

1. **Effekttariff Reduction**: 800-1,000 kr/month savings
2. **Spot Market Arbitrage**: Limited due to low price volatility
3. **Curtailment Avoidance**: Minimal with 70 kW limit

### Battery Price Research

Searched project folders for battery quotes:
- Found FENECON system (167.7 kWh, 92 kW) in Setesdal Bilruter project
- No pricing information found in accessible PDF documents
- Market estimates: 5,000-6,000 kr/kWh based on industry knowledge

### Technical Validations

1. **PVSol PDF Review**: Confirmed 959.78 kWh/kWp, 133,017 kWh annual
2. **Performance Ratio**: 92.62% in PVSol (very good)
3. **Clipping**: Only 0.78% at 100 kW inverter limit
4. **Peak Production**: Typically 85-95 kW (rarely exceeds 70 kW limit)

### Conclusions

1. **Battery Economics**: Not viable at current market prices (5,000-6,000 kr/kWh)
2. **Break-even Point**: Need battery costs to drop to 2,500-3,600 kr/kWh
3. **Optimal Sizing**: Small battery (30-50 kWh) with 0.5-1.0 C-rate
4. **Primary Value**: Effekttariff reduction, not energy arbitrage
5. **Curtailment**: Minimal issue with realistic production profiles

### Files Generated

- Multiple Python analysis scripts in `/mnt/c/Users/klaus/klauspython/offgrid2/battery_optimization/`
- This chatlog.md documentation file
- Comprehensive NPV calculations and sensitivity analyses

### Final Recommendation

Wait for battery prices to decrease before investing. Current market prices are 40-140% above economic break-even point. Focus on maximizing self-consumption and consider revisiting battery investment when prices drop below 3,000 kr/kWh.

## Fortsettelse av samtalen

### Varighetskurve-analyse
Laget varighetskurve basert på PVGIS-data som viser:
- 263 timer > 70 kW (nettgrense)
- 62 timer > 80 kW
- 9 timer > 90 kW
- Makseffekt: 96.4 kW AC

### Tap ifølge Are's PVSol-analyse
Detaljerte tap fra PVSol (Are's erfaring):
- Forurensning: -2.25%
- Temperatur: -0.21%
- Mismatch: -0.53%
- DC/AC konvertering: -1.78%
- Kabler: -0.70%
- **TOTALT: ~7% reelle tap** (ikke 14% PVGIS-standard)

### Kritisk funn: Inntektsfordeling
Detaljert analyse viser at batterinntektene fordeler seg helt annerledes enn antatt:

**Faktiske inntekter (100 kWh / 75 kW batteri):**
1. **Unngått kutting (>70kW)**: 765 kr/år (104%)
2. **Spotmarked arbitrasje**: -302 kr/år (-41%) - NEGATIVT!
3. **Tidsforskyvning**: 274 kr/år (37%)
4. **Effekttariff reduksjon**: 0 kr/år (0%)
- **TOTAL: 737 kr/år**

### Hvorfor så store avvik fra tidligere analyser?

**Tidligere antakelser (for optimistiske):**
- Effekttariff reduksjon: 10,000-12,000 kr/år
- Arbitrasje: 3,000-5,000 kr/år
- Unngått kutting: 5,000-10,000 kr/år
- Total: 18,000-27,000 kr/år

**Faktiske tall viser:**
- Effekttariff: 0 kr (batteriet påvirker ikke import-topper)
- Arbitrasje: NEGATIV (10% tap > prisforskjeller i NO2)
- Kutting: Kun 765 kr (færre timer >70 kW enn antatt)
- Total: 737 kr/år

### Kritisk mangel: Forbruksprofil
Analysen avdekket at forbruksprofilen bak måleren er kritisk for batterilønnsomhet:

**Test av ulike forbruksprofiler:**
- Ingen forbruk: 2,855 kr/år
- Kontorbygg (200 MWh): 3,070 kr/år
- Industri (500 MWh): 1,271 kr/år
- Boligområde (150 MWh): 3,391 kr/år

MEN: Fortsatt ingen effekttariff-reduksjon i noen scenario!

### Hovedkonklusjon

**Batteri er IKKE lønnsomt** ved dagens priser:
- Årlig inntekt: 737-3,400 kr (avhengig av forbruksprofil)
- Årlig kostnad: ~25,000 kr (avskrivning)
- NPV @ 3000 kr/kWh: -250,000 til -370,000 kr
- Break-even batterikostnad: < 300 kr/kWh
- Markedspris: 5,000-6,000 kr/kWh (17-20x for høy!)

### Læringspunkter

1. **PVGIS vs PVSol**: PVSol (Are) har mer nøyaktige tap (7% vs 14%)
2. **Arbitrasje fungerer ikke** i NO2 pga lav prisvolatilitet
3. **Effekttariff-reduksjon** krever riktig forbruksprofil og større batteri
4. **Forbruksprofil er kritisk** for batterilønnsomhet
5. **Kuttet produksjon** er mindre problem enn antatt (kun 330-470 timer >70 kW)

### Veien videre

For mer nøyaktig analyse trengs:
- Faktisk forbruksprofil (årlig kWh, døgnvariasjoner)
- Dagens døgnmaks og effekttariff-nivå
- Type virksomhet og lastprofil

Uten betydelig prisfall på batterier eller endringer i rammebetingelser (høyere nettleie, større prisvolatilitet, strengere eksportgrenser) er batterier ikke økonomisk lønnsomme for dette anlegget.

---
*Chatlog oppdatert 2025-01-20 kveld*
*End of chat log*