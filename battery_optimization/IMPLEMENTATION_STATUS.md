# Battery Sizing Optimization Implementation Status

## 📅 Dato: 31. oktober 2025

## 🎯 Målsetting
Implementere Differential Evolution-basert optimering for å finne optimal batteristruktur (kW, kWh) som maksimerer break-even cost ved bruk av LP-optimering.

## ✅ Gjennomførte Oppgaver

### 1. Representative Dataset Generation ✓
**Fil**: `core/representative_dataset.py`

**Implementert**:
- `RepresentativeDatasetGenerator` klasse
- `select_representative_days()` - velger 12 typiske + 4 ekstreme dager
- `validate_compression()` - validerer <2% feil
- Hybrid stratified sampling strategi:
  - Typiske dager: 1 per måned (median PV/load/spot)
  - Ekstreme scenarioer:
    1. Høyest curtailment-risiko
    2. Høyest spotpris
    3. Lavest spotpris
    4. Høyest forbruk

**Kompresjon**: 8760 timer → 384 timer (95.6% reduksjon)

**Status**: Koden er ferdig men trenger små DataFrame-fikser for validering

### 2. Validation Script (Pågående)
**Fil**: `validate_compression.py`

**Implementert**:
- Henter oktober 2025 data
- Genererer PV og load-profiler
- Kjører LP-optimering på full måned
- Kjører LP-optimering på representative dataset
- Skalerer resultater til månedsbasis
- Sammenligner og validerer

**Problemer**:
- ✓ Import paths fikset (fra `data.` til `core.`)
- ✓ `fetch_prices` signatur fikset
- ✓ MonthlyLPResult object access fikset (`.attribute` ikke `['key']`)
- ⚠️ DataFrame index/column ambiguity i `representative_dataset.py` linje 88

**Forventet output** (når fungerende):
```
VALIDATION RESULTS:
  Average error: X.XX%
  Maximum error: Y.YY%
  ✓ VALIDATION PASSED: Average error <2%
```

## 📋 Gjenstående Oppgaver

### 3. Economic Analysis Module
**Fil**: `core/economic_analysis.py` (IKKE STARTET)

**Må implementere**:
```python
def calculate_breakeven_cost(
    annual_savings: float,
    battery_kwh: float,
    battery_kw: float,
    discount_rate: float = 0.05,
    lifetime: int = 15
) -> float:
    """
    Beregn break-even batterikostnad (NOK/kWh) ved NPV=0

    NPV = sum(savings_year_t / (1+r)^t) - investment

    Ved NPV=0:
        investment = sum(savings_year_t / (1+r)^t)
        breakeven_cost = investment / battery_kwh

    Returns:
        Break-even cost [NOK/kWh]
    """
    # PV of annual savings over lifetime
    pv_savings = sum(
        annual_savings / (1 + discount_rate)**t
        for t in range(1, lifetime + 1)
    )

    # Investment = Battery cost
    # At break-even: PV(savings) = Investment
    # breakeven_cost_per_kwh * battery_kwh = pv_savings

    breakeven_cost_per_kwh = pv_savings / battery_kwh

    return breakeven_cost_per_kwh
```

### 4. Battery Sizing Optimizer med DE
**Fil**: `optimize_battery_sizing.py` (IKKE STARTET)

**Må implementere**:
```python
from scipy.optimize import differential_evolution
from core.lp_monthly_optimizer import MonthlyLPOptimizer
from core.representative_dataset import RepresentativeDatasetGenerator
from core.economic_analysis import calculate_breakeven_cost

class BatterySizingOptimizer:
    def __init__(self, config, year_data):
        self.config = config
        self.year_data = year_data
        self.dataset_gen = RepresentativeDatasetGenerator()

        # Create representative dataset once
        self.repr_data = self.dataset_gen.select_representative_days(...)

    def objective_function(self, x):
        """
        Maksimer break-even cost
        Input: x = [battery_kw, battery_kwh]
        Output: -breakeven_cost (negativ for maximering)
        """
        battery_kw, battery_kwh = x

        # E/P ratio constraint
        e_p_ratio = battery_kwh / battery_kw
        if not (0.5 <= e_p_ratio <= 6.0):
            return 1e6  # Penalty (stor positiv verdi = dårlig)

        # Run LP optimization on representative dataset
        optimizer = MonthlyLPOptimizer(
            self.config,
            resolution='PT60M',
            battery_kwh=battery_kwh,
            battery_kw=battery_kw
        )

        result = optimizer.optimize_month(
            month_idx=10,  # Or full year with representative dataset
            pv_production=self.repr_data['pv'],
            load_consumption=self.repr_data['load'],
            spot_prices=self.repr_data['spot'],
            timestamps=self.repr_data['timestamps'],
            E_initial=battery_kwh * 0.5
        )

        # Scale to annual
        annual_savings = result.objective_value * (365 / 31)  # Rough scaling

        # Calculate break-even cost
        breakeven = calculate_breakeven_cost(
            annual_savings,
            battery_kwh,
            battery_kw
        )

        return -breakeven  # Negative for maximization

    def optimize(self):
        """Run Differential Evolution"""
        bounds = [
            (10, 100),  # kW
            (20, 300)   # kWh
        ]

        result = differential_evolution(
            self.objective_function,
            bounds,
            strategy='best1bin',
            maxiter=100,
            popsize=15,
            workers=-1,  # Parallel
            seed=42,
            polish=True,
            updating='deferred'
        )

        optimal_kw, optimal_kwh = result.x
        max_breakeven = -result.fun  # Negate back

        return {
            'optimal_kw': optimal_kw,
            'optimal_kwh': optimal_kwh,
            'ep_ratio': optimal_kwh / optimal_kw,
            'breakeven_cost': max_breakeven,
            'iterations': result.nit,
            'evaluations': result.nfev
        }
```

### 5. Visualization
**Fil**: `visualize_sizing_optimization.py` (IKKE STARTET)

**Må implementere**:
- Konvergensplott: Break-even cost vs iterasjon
- Heatmap: Break-even cost over (kW, kWh) parameter-rom
- E/P ratio analyse
- Final validering mot full-år

## 🔧 Umiddelbare Fikser Nødvendig

### Fix i `core/representative_dataset.py` linje 88:

**Problem**: DataFrame har 'timestamp' både som index og column
```python
# Nåværende (FEIL):
representative_df = representative_df.reset_index(drop=False).sort_values('timestamp').set_index('timestamp', drop=False)

# Foreslått fix:
representative_df = representative_df.reset_index(drop=True).sort_values('timestamp')
```

Eller enklere:
```python
# Bare sorter på eksisterende index/kolonne uten duplikering
representative_df = representative_df.sort_values(by=[representative_df.columns[0]])
```

## 📊 Forventet Ytelse

| Metode | Evalueringer | Tid/eval | Total Tid | Speedup |
|--------|--------------|----------|-----------|---------|
| Grid Search 50×50 | 2,500 | 10 sek | ~7 timer | 1x |
| DE (compressed) | 300-500 | 10 sek | ~1 time | 5-10x |
| DE (compressed, parallel 8 cores) | 300-500 | 1.25 sek | ~10 min | 40-50x |

## 🎯 Forventet Resultat

```
Optimal Battery Sizing Results:
================================
  Capacity: XX kWh
  Power: YY kW
  E/P ratio: Z.Z timer
  Break-even cost: XXXX NOK/kWh

  Optimization:
    Total iterations: ~100
    Total evaluations: ~400
    Convergence: ~60 iterations

  Validation (full year):
    Compressed dataset: XXXX NOK/kWh
    Full year: XXXX NOK/kWh
    Error: <2%
```

## 🚀 Neste Steg

1. **Fix DataFrame issue** i `representative_dataset.py` linje 88
2. **Valider kompresjon** - kjør `python validate_compression.py`
3. **Implementer `economic_analysis.py`** - break-even beregning
4. **Implementer `optimize_battery_sizing.py`** - DE-based optimizer
5. **Test optimering** på komprimert datasett
6. **Valider optimal størrelse** mot full-år
7. **Lag visualisering** med resultater

## 💡 Nøkkelinnsikter

1. **Kompresjon er kritisk**: 95.6% reduksjon i datapoints → 40-50x speedup
2. **Representative dager**: 12 typiske + 4 ekstreme = god balanse
3. **DE er overlegen grid search**: Globalt optimum med 10x færre evalueringer
4. **E/P ratio constraint**: Viktig for realistiske batterikonfigurasjoner
5. **Break-even cost**: Bedre metrikk enn NPV for å evaluere batteriinvesteringer

## 📚 Referanser

- Existing DE implementation: `archive/original_src/src/optimization/optimizer.py`
- LP optimizer: `core/lp_monthly_optimizer.py`
- Price fetcher: `core/price_fetcher.py`
- Config: `config.py`

---

**Siste oppdatering**: 31. oktober 2025
**Status**: 50% fullført - representative dataset klar, mangler economic analysis og DE optimizer
