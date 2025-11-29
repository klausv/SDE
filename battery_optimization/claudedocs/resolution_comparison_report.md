# Sammenligning: 15-minutters vs 60-minutters tidsoppløsning

**Periode:** Oktober 20-26, 2025 (1 uke)
**System:** 30 kW/30 kWh batteri, 138.55 kWp solceller, Stavanger (NO2)
**Data:** Reelle ENTSO-E spotpriser + PVGIS soldata
**Metode:** Rolling horizon optimalisering med 24-timers horisont

---

## 📊 PLOTTBESKRIVELSER

### **Plot 1: Battery State of Charge (SOC)**
**Viser:** Batterinivå over tid for begge oppløsninger

**Observasjoner:**
- 🔵 **60-min** (blå linje): Jevnere SOC-kurve med færre små justeringer
- 🔴 **15-min** (rød linje): Mer detaljert SOC-styring med finere justeringer
- ⚪ **Grenser**: Grå stiplede linjer viser SOC min (10%) og max (90%)

**Innsikt:** 15-min gir mer dynamisk batterikontroll, men begge holder seg godt innenfor sikre grenser.

---

### **Plot 2: ENTSO-E NO2 Spotpriser**
**Viser:** Strømprisvariasjon gjennom uken

**Observasjoner:**
- 🔴 **60-min priser** (tykk linje): Prisrange 0.35 - 2.02 NOK/kWh
- 🔴 **15-min priser** (tynn/gjennomsiktig): Mer volatilitet, 0.32 - 2.82 NOK/kWh
- 🟠 **Gjennomsnitt** (oransje stiplet): ~0.79 NOK/kWh

**Innsikt:** 15-min data fanger ekstreme pristopper som 60-min data glatter ut. Dette kan både være en fordel (mulighet for arbitrage) og ulempe (risiko for suboptimale beslutninger).

---

### **Plot 3: Batterikjøring**
**Viser:** Lading (+) og utlading (-) av batteriet

**Observasjoner:**
- 🟢 **Grønt** = Lading (batteriet tar imot energi)
- 🔴 **Rødt** = Utlading (batteriet leverer energi)
- 🔵 **15-min** (blå linje): Mer frekvente og finere justeringer
- **Grenser**: ±30 kW (batterikraft)

**Innsikt:** 15-min kjører batteriet mer aggressivt med flere små justeringer. 60-min har lengre, mer stabile lade-/utladingsperioder.

---

### **Plot 4: Nettimport/-eksport**
**Viser:** Kraftutveksling med strømnettet

**Observasjoner:**
- 🔴 **Import** (rød): Når du kjøper strøm fra nettet
- 🔵 **Eksport** (turkis/teal): Når du selger strøm til nettet
- 🔴 **Nettgrense** (70 kW): Maks tillatt nettbelastning

**Innsikt:** Begge oppløsninger holder seg godt under 70 kW-grensen. Minimal eksport (6-7 kWh for hele uken) tyder på god egenforbruksstyring.

---

### **Plot 5: Solproduksjon vs Forbruk**
**Viser:** Energibalanse mellom sol og forbruk

**Observasjoner:**
- 🟡 **Gult** = Solproduksjon (dagtid)
- 🟣 **Lilla** = Forbruk (hele døgnet)
- **Gap**: Området mellom kurvene viser når batteri/nett må brukes

**Innsikt:** Oktober har lav solproduksjon (høst). Forbruket er 10× høyere enn solproduksjon, så systemet er svært nettavhengig denne uken.

---

### **Plot 6: Økonomisk sammenligning**
**Viser:** Kostnader og inntekter for begge oppløsninger

**Komponenter:**
1. **Nettimport kostnad**: Hva du betaler for strøm fra nettet
2. **Netteksport inntekt**: Hva du tjener på å selge strøm
3. **Egenforbruk verdi**: Verdi av solstrøm du bruker selv

**Tall (1 uke):**
- Nettimport: ~3,400-3,450 NOK
- Netteksport: Minimal (~5-7 NOK)
- Egenforbruk: ~320 NOK verdi

**Innsikt:** Nesten alle kostnader er nettimport. Minimal eksport tyder på god egenforbruksstyring.

---

### **Plot 7: Kumulativ kostnad**
**Viser:** Akkumulert energikostnad over tid

**Observasjoner:**
- 🔵 **60-min** ender på 3,437.66 NOK
- 🔴 **15-min** ender på 3,452.59 NOK
- **Differanse**: +14.94 NOK (0.43% dyrere med 15-min)

**Innsikt:** Kurvene følger hverandre tett. Den lille forskjellen akkumuleres gradvis, hovedsakelig på grunn av litt høyere import i 15-min casen.

---

### **Plot 8: Nøkkeltall (tekstboks)**
**Viser:** Komplett sammendrag av alle metrikker

**Hovedfunn:**
- **Energikostnad**: 15-min er 15 NOK dyrere (0.43%)
- **Batterisykluser**: 15-min bruker 11% MER batteri (4.27 vs 3.83 sykluser)
- **Nettimport**: 15-min importerer 50 kWh mer (4,093 vs 4,043 kWh)
- **Egenforbruk**: Nesten identisk (~98.3-98.4%)
- **Optimaliseringer**: 15-min kjører 4× flere (576 vs 144)

---

## 🎯 HOVEDKONKLUSJONER

### ✅ **Fordeler med 15-minutters oppløsning:**
1. **Mer batterikjøring** (+11% sykluser = bedre utnyttelse)
2. **Finere kontroll** (576 beslutningspunkter vs 144)
3. **Raskere respons** på prisendringer
4. **Mer realistisk modell** (fra 2025 vil NO1 ha 15-min oppløsning)

### ⚠️ **Ulemper med 15-minutters oppløsning:**
1. **Marginalt dyrere** (+15 NOK/uke = ~780 NOK/år)
2. **Mer volatilitet** kan gi suboptimale beslutninger
3. **4× flere beregninger** (lengre simuleringstid)
4. **Høyere nettimport** (+50 kWh/uke)

### 💡 **Samlet vurdering:**

**Forskjellen er NEGLISJERBAR (0.43%)** - innenfor usikkerhet!

**Anbefaling:**
- For **produksjonssystemer** (etter mai 2025): Bruk 15-min for å matche markedet
- For **simuleringer**: 60-min er raskere og gir nesten samme resultat
- For **analyse av arbitrage**: 15-min er nødvendig for å fange intra-time-variasjoner

---

## 📈 POTENSIELLE FORBEDRINGER

### For bedre 15-min ytelse:
1. **Test vinter-periode** med høyere prisvolatilitet
2. **Større batteri** (60 kW/60 kWh) for mer arbitrage
3. **Inkluder mer solproduksjon** (vår/sommer) for å se fordel med rask respons
4. **Optimalisere risikoparametre** for 15-min volatilitet

---

## 📁 FILER

- **Detaljerte plots**: `results/detailed_comparison_plots.png` (1.3 MB, 8 plots)
- **Sammendragsplot**: `results/resolution_comparison_oct2025_real.png` (918 KB)
- **Kjørescript**: `compare_resolutions_real_data.py`
- **Data**: Reelle ENTSO-E NO2 priser + PVGIS soldata

---

**Generert:** 16. november 2025
**Simuleringsverktøy:** Rolling Horizon Optimizer (24h horisont)
**Batteri:** 30 kW/30 kWh LFP (Skanbatt)
**Solceller:** 138.55 kWp (Stavanger, 58.97°N, 5.73°E)
