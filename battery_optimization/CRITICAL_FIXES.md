# KRITISKE RETTELSER - Battery Optimization LP Model

## Oppdaget: 2025-11-03
## Status: ✅ IMPLEMENTERT - 2025-11-03

---

## 🔴 FEIL #1: Export Pricing i LP-optimalisering

**Fil:** `core/lp_monthly_optimizer.py`
**Linje:** 243

### Nåværende (FEIL):
```python
# Export revenue (feed-in tariff)
c_export[t] = 0.04  # Fixed feed-in tariff
```

### Korrekt:
```python
# Export revenue (feed-in tariff + spot price)
c_export[t] = spot_prices[t] + 0.04  # Spot price + innmatingstariff (4 øre)
```

### Forklaring:
- Innmatingstariff 0.04 kr/kWh kommer I TILLEGG til spotpris
- Total export inntekt = spotpris + 4 øre
- Nåværende kode gir KUN 4 øre, som gjør eksport ekstremt ulønnsomt
- Dette får batteriet til å ALDRI eksportere (kun curtail)

---

## 🔴 FEIL #2: Inkonsistent kostnadsberegning mellom referanse og LP

**Fil:** `calculate_breakeven_2024.py`
**Funksjon:** `calculate_reference_case()`
**Linjer:** 96-99

### Nåværende (FEIL):
```python
# Calculate costs
# Energy cost
import_cost = grid_import * data['spot_price']  # ❌ Mangler nettleie og avgifter!
export_revenue = grid_export * data['spot_price'] * 0.9  # ❌ Feil modell
energy_cost = np.sum(import_cost) - np.sum(export_revenue)
```

### Korrekt:
```python
# Calculate costs using SAMME metode som LP-optimalisering
from core.lp_monthly_optimizer import MonthlyLPOptimizer

# Create dummy optimizer to use same cost calculation
dummy_optimizer = MonthlyLPOptimizer(config, resolution='PT60M',
                                      battery_kwh=0, battery_kw=0)
c_import, c_export = dummy_optimizer.get_energy_costs(data.index,
                                                       data['spot_price'].values)

# Calculate costs with IDENTICAL pricing as LP
import_cost = grid_import * c_import
export_revenue = grid_export * c_export
energy_cost = np.sum(import_cost) - np.sum(export_revenue)
```

### Forklaring:
- Referansecase MÅ bruke IDENTISKE kostnader som LP-optimaliseringen
- Nåværende referanse mangler nettleie (0.296/0.176 kr/kWh) og forbruksavgift (0.15 kr/kWh)
- Export pricing er også forskjellig (90% av spot vs spot + 0.04)
- Dette gjør sammenligningen fullstendig ugyldig

---

## 🔴 FEIL #3: Manglende validering av syklusrate

**Fil:** `core/lp_monthly_optimizer.py`
**Etter linje:** 402

### Legg til validering:
```python
# Validate equivalent cycles and warn if excessive
if self.degradation_enabled:
    equivalent_cycles = np.sum(DOD_abs)
    cycles_per_year = equivalent_cycles * (8760.0 / T)  # Extrapolate to annual

    print(f"  Equivalent cycles (this period): {equivalent_cycles:.1f}")
    print(f"  Extrapolated annual rate: {cycles_per_year:.0f} cycles/year")

    # Warnings
    if cycles_per_year > 400:
        print(f"  ⚠️  WARNING: Very high cycle rate!")
        print(f"      Expected for peak shaving: 100-200 cycles/year")
        print(f"      Current rate suggests aggressive arbitrage trading")

    # Compare cyclic vs calendar
    cyclic_monthly = np.sum(DP_cyc)
    calendar_monthly = self.dp_cal_per_timestep * T

    if cyclic_monthly < calendar_monthly * 0.5:
        print(f"  ⚠️  Battery under-utilized (calendar degradation dominates)")
    elif cyclic_monthly > calendar_monthly * 5:
        print(f"  ⚠️  Battery over-utilized (cyclic degradation dominates)")
```

---

## 📊 FORVENTET EFFEKT AV RETTELSER

### Før rettelser:
```
Export inntekt (LP):     0.04 kr/kWh  ← Feil
Import kostnad (LP):     0.70 kr/kWh  ← Riktig
Import kostnad (ref):    0.30 kr/kWh  ← Feil (mangler nettleie/avgift)
Export inntekt (ref):    0.27 kr/kWh  ← Feil (90% av spot)

Arbitrage margin (LP):   0.70 - 0.04 = 0.66 kr/kWh  ← Ekstremt ulønnsomt å eksportere!
→ Batteriet velger ALDRI å eksportere
→ Kun curtailment når batteri fullt
→ Ekstremt høy syklusrate (843 cycles/år)
```

### Etter rettelser:
```
Export inntekt (LP):     spot + 0.04 ≈ 0.34 kr/kWh  ← Riktig
Import kostnad (LP):     spot + tariff + tax ≈ 0.70 kr/kWh  ← Riktig
Import kostnad (ref):    spot + tariff + tax ≈ 0.70 kr/kWh  ← Riktig
Export inntekt (ref):    spot + 0.04 ≈ 0.34 kr/kWh  ← Riktig

Arbitrage margin:        0.70 - 0.34 = 0.36 kr/kWh (peak import)
                         0.50 - 0.34 = 0.16 kr/kWh (offpeak import)
→ Mer balansert økonomi
→ Mindre aggressiv arbitrage
→ Forventet syklusrate: 150-250 cycles/år
→ Degraderingskostnad: 600-1,000 NOK/år
```

---

## 🔧 IMPLEMENTERINGSPLAN

### 1. Rett export pricing i LP (KRITISK)
**Fil:** `core/lp_monthly_optimizer.py`
**Linje:** 243

```python
# GAMMELT:
c_export[t] = 0.04  # Fixed feed-in tariff

# NYTT:
c_export[t] = spot_prices[t] + 0.04  # Spot price + innmatingstariff
```

### 2. Rett referansecase-beregning
**Fil:** `calculate_breakeven_2024.py`
**Linjer:** 79-145

Erstatt `calculate_reference_case()` funksjon med ny implementering som:
- Bruker `MonthlyLPOptimizer.get_energy_costs()`
- Sikrer identiske kostnader som LP-case
- Samme export pricing

### 3. Legg til validering
**Fil:** `core/lp_monthly_optimizer.py`
**Etter linje:** 402

Legg til cycle rate warnings og degradation balance checks.

---

## ⚠️ VIKTIG MERKNAD

Disse rettelsene vil **DRASTISK** endre resultatene:

1. **Batteriet vil eksportere** når det er økonomisk lønnsomt
2. **Syklusraten vil reduseres** betydelig (fra 843 til ~200 cycles/år)
3. **Degraderingskostnaden vil falle** (fra 3,286 til ~800 NOK/år)
4. **Referansecasen vil bli dyrere** (fra 103k til ~150k+ NOK)
5. **Batteriet vil trolig bli lønnsomt** (positiv NPV)

---

## 📋 TESTING ETTER RETTELSER

Kjør disse testene:

```bash
# 1. Test med rettelser
cd battery_optimization
python calculate_breakeven_2024.py

# Forventet output:
# - Reference case: ~150,000-180,000 NOK
# - Battery case: ~140,000-160,000 NOK
# - Annual savings: 10,000-20,000 NOK (POSITIVT!)
# - Degradation: ~800-1,200 NOK/år
# - Equivalent cycles: 150-250 cycles/år

# 2. Valider syklusrate
grep "Equivalent cycles" <output>
# Skal vise ~150-250 cycles/år (ikke 843!)

# 3. Sjekk export
# LP skal nå eksportere når lønnsomt
# Ikke bare curtail
```

---

## 📖 REFERANSER

### Energiprising i Norge:
- Spotpris: Nordpool day-ahead
- Nettleie: Lnett tariff (peak 0.296, offpeak 0.176 kr/kWh)
- Forbruksavgift: 0.15 kr/kWh (sesongavhengig)
- Innmatingstariff: 0.04 kr/kWh (fast)
- Total import: spot + nettleie + avgift
- Total export: spot + innmatingstariff

### Kilder:
- Korpås et al. (2019) - Degradation model
- ENTSO-E Transparency Platform - Spot prices
- Lnett - Nettleietariffer

---

## ✅ IMPLEMENTERINGSSTATUS

### Alle rettelser implementert 2025-11-03

**Feil #1: Export Pricing i LP** - ✅ RETTET
- **Fil:** `core/lp_monthly_optimizer.py`
- **Linjer:** 242-244
- **Endring:** `c_export[t] = spot_prices[t] + 0.04` (fra bare 0.04)

**Feil #2: Inkonsistent Referansecase** - ✅ RETTET
- **Fil:** `calculate_breakeven_2024.py`
- **Linjer:** 95-113
- **Endring:** Bruker nå `MonthlyLPOptimizer.get_energy_costs()` for identiske kostnader

**Feil #3: Manglende Validering** - ✅ LAGT TIL
- **Fil:** `core/lp_monthly_optimizer.py`
- **Linjer:** 404-424
- **Endring:** Advarsler for ekstremt høy syklusrate og degraderingsbalanse

### Neste steg
```bash
cd battery_optimization
python calculate_breakeven_2024.py
```

**Forventet resultat:**
- Reference case: ~150,000-180,000 NOK (økning fra 103k)
- Battery case: ~140,000-160,000 NOK (reduksjon fra 177k)
- Annual savings: 10,000-20,000 NOK (POSITIVT!)
- Degradation: ~800-1,200 NOK/år (reduksjon fra 3,286)
- Equivalent cycles: 150-250 cycles/år (reduksjon fra 843)
