# HVORDAN KJØRE BATTERIANALYSEN

## RASK START - Kjør dette:

```bash
# 1. KOMPLETT ANALYSE (anbefalt!)
python complete_battery_analysis.py

# 2. KUN AVKORTNING
python calculate_curtailment.py

# 3. DEMONSTRASJON
python run_analysis_demo.py
```

## RESULTATER DU FÅR:

### Fra `complete_battery_analysis.py`:
- **Avkortning**: 13,973 kWh/år (verdi: 6,288 NOK/år)
- **Energiarbitrasje**: 20,365 NOK/år
- **Effekttariff-besparelse**: 32,947 NOK/år
- **Selvforsyning**: 14,737 NOK/år
- **TOTAL ÅRLIG BESPARELSE**: 74,337 NOK/år
- **Break-even batterikostnad**: 5,000 NOK/kWh
- **NPV ved 3,000 NOK/kWh**: 370,984 NOK

### Fra `calculate_curtailment.py`:
- **Total avkortet energi**: 8,124 kWh/år
- **Økonomisk tap**: 3,656 NOK/år
- **Timer med avkortning**: 479 (5.5% av året)
- **Månedlig fordeling** (mest i juni/juli)

## HVIS DU VIL JUSTERE PARAMETERE:

### Endre batterikostnad:
Rediger linje 307 i `complete_battery_analysis.py`:
```python
battery_costs = [2000, 2500, 3000, 3500, 4000, 4500, 5000]  # Endre disse
```

### Endre batteristørrelse:
Rediger linje 308:
```python
battery_size = 100  # kWh - prøv 50, 80, 150, 200
```

### Endre strømpriser:
Rediger linje 129:
```python
base_price = 0.50  # NOK/kWh - juster opp/ned
```

## FILER OG DERES FORMÅL:

| Fil | Hva den gjør | Når bruke |
|-----|--------------|-----------|
| `complete_battery_analysis.py` | Full analyse med ALLE beregninger | **START HER** |
| `calculate_curtailment.py` | Kun avkortningsberegning | For detaljer om avkortning |
| `run_analysis_demo.py` | Demo med hardkodede verdier | Rask oversikt |
| `run_real_analysis.py` | Bruker refaktorert kode | Hvis du vil teste ny arkitektur |
| `main.py` | Original optimalisering | For sammenligning |
| `main_refactored.py` | Ny arkitektur | Avansert bruk |

## TOLKE RESULTATENE:

### Hvis NPV > 0:
✅ **INVESTER** - Batteriet er lønnsomt

### Hvis NPV < 0:
❌ **VENT** - Batterikostnadene må ned

### Break-even kostnad:
Dette er maksimal batterikostnad hvor NPV = 0

## EKSEMPEL OUTPUT:

```
============================================================
KOMPLETT BATTERIANALYSE - ALLE BEREGNINGER
============================================================

📊 VERDIDRIVERE FOR BATTERI:
============================================================

1️⃣ UNNGÅTT AVKORTNING:
   • Avkortet energi: 13,973 kWh/år
   • Verdi: 6,288 NOK/år

2️⃣ ENERGIARBITRASJE:
   • Prisdifferanse: 0.77 NOK/kWh
   • Verdi: 20,365 NOK/år

3️⃣ REDUSERT EFFEKTTARIFF:
   • Besparelse: 32,947 NOK/år

4️⃣ ØKT SELVFORSYNING:
   • Verdi: 14,737 NOK/år

💰 TOTAL: 74,337 NOK/år

📈 NPV ved 3000 NOK/kWh: 370,984 NOK
🎯 Break-even: 5,000 NOK/kWh

ANBEFALING: ✅ INVESTER - batteriet er lønnsomt!
```