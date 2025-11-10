# Why Battery Arbitrage Shows Negative Value: A Complete Explanation

## Executive Summary

**Problem**: Battery "arbitrage" calculation shows **-804 kr/year** when it should be positive
**Root Cause**: Proportional allocation method incorrectly attributes value by mixing temporal relationships
**Solution**: Either (1) use temporal tracking (FIFO/LIFO), (2) eliminate "arbitrage" as a separate category, or (3) use price-based classification

---

## 1. Understanding the Proportional Allocation Method (Current)

### How It Works

```
Step 1: Classify ALL charging events by PV surplus availability
  - Egetforbruk charge: 6,911 kWh (29.2%) - when PV surplus > 0
  - Arbitrage charge:   16,778 kWh (70.8%) - when PV surplus ≤ 0

Step 2: Apply proportions to ALL discharging
  - Total discharge: 21,332 kWh
  - Arbitrage discharge (allocated): 70.8% × 21,332 = 15,109 kWh

Step 3: Calculate arbitrage value
  - Charge cost:  16,778 kWh × 1.134 kr/kWh = 19,030 kr
  - Discharge value: 15,109 kWh × 1.206 kr/kWh = 18,226 kr
  - Net arbitrage: -804 kr ❌
```

### Why This Fails: The Temporal Mixing Problem

**Example showing the flaw**:

```
Hour 10 (Sunny midday):
  PV production: 100 kW
  Load: 60 kW
  PV surplus: +40 kW
  → Battery charges 30 kW (from PV, classified as "egetforbruk")

Hour 19 (Evening peak):
  PV production: 0 kW
  Load: 80 kW
  Spot price: 1.20 kr/kWh (high)
  → Battery discharges 30 kW (to meet load)

Current method says:
  "70.8% of hour-19 discharge is arbitrage" (10.6 kW)

Reality:
  ALL of hour-19 discharge came from hour-10 PV charge!
  This is 100% egetforbruk (self-consumption optimization)
  It's NOT arbitrage (price trading)
```

**The fundamental error**: Proportional allocation assumes charging proportions apply uniformly to ALL discharge events, ignoring that batteries operate on temporal causality (charge THEN discharge).

---

## 2. Why Spot Price Spread is Positive But Net is Negative

### The Numbers

```
Spot prices:
  Charge (arbitrage hours):    0.736 kr/kWh
  Discharge (all hours):       0.773 kr/kWh
  Spread:                      +0.037 kr/kWh ✅

Tariffs:
  Charge (off-peak avg):       0.219 kr/kWh (mostly nights/weekends)
  Discharge (peak avg):        0.254 kr/kWh (mostly Mon-Fri 06-22)
  Difference:                  +0.035 kr/kWh ⚠️

Total cost/kWh:
  Charge:  0.736 + 0.219 + 0.179 = 1.134 kr/kWh
  Discharge: 0.773 + 0.254 + 0.179 = 1.206 kr/kWh
  Difference: +0.072 kr/kWh
```

### The Tariff Paradox

**Why higher discharge tariff hurts arbitrage but helps self-consumption**:

| Scenario | Charging | Discharging | Tariff Impact |
|----------|----------|-------------|---------------|
| **True arbitrage** (export) | Buy from grid (pay tariff) | Sell to grid (NO tariff revenue) | Tariff = pure cost ❌ |
| **Self-consumption** | Buy from grid (pay tariff) | Avoid import (save tariff) | Tariff = benefit ✅ |

**Current reality**:
- Battery charges during LOW tariff hours (0.219 kr/kWh)
- Battery discharges during HIGH tariff hours (0.254 kr/kWh)
- **If discharge goes to export**: You PAY 0.219 charging tariff but GET NOTHING on discharge → net loss
- **If discharge avoids import**: You PAY 0.219 but SAVE 0.254 → net gain +0.035 kr/kWh

**The problem**: Proportional method can't distinguish between:
1. Discharge → export (arbitrage, loses on tariff asymmetry)
2. Discharge → avoid import (self-consumption, gains on tariff asymmetry)

---

## 3. What "Arbitrage" Actually Means

### Traditional Definition (Pure Trading)

**Arbitrage = Buy low, sell high (export to grid)**

```
Night (cheap):
  Spot: 0.40 kr/kWh
  → Charge from grid: Pay 0.40 + 0.176 (tariff) + 0.179 (tax) = 0.755 kr/kWh

Day (expensive):
  Spot: 1.20 kr/kWh
  → Discharge to export: Receive 1.20 kr/kWh (NO tariff benefit!)

Net: 1.20 - 0.755 = +0.445 kr/kWh ✅

BUT: In reality, you DON'T export battery discharge!
     You discharge to AVOID IMPORT (different value!)
```

### Reality: "Arbitrage" is Self-Consumption Shifting

**What the battery actually does**:

```
Night (cheap import):
  Load: 80 kW, Spot: 0.40 kr/kWh
  Without battery: Import 80 kW @ (0.40 + 0.176 + 0.179) = 0.755 kr/kWh
  With battery: Charge 30 kW from grid @ 0.755 kr/kWh

Day (expensive import):
  Load: 80 kW, Spot: 1.20 kr/kWh
  Without battery: Import 80 kW @ (1.20 + 0.296 + 0.179) = 1.675 kr/kWh
  With battery: Discharge 30 kW, import only 50 kW

Value: Avoided 30 kWh @ 1.675 kr/kWh = 50.25 kr
Cost: Charged 30 kWh @ 0.755 kr/kWh = 22.65 kr (× 90% efficiency = 33 kWh charged)
Net savings: 50.25 - 24.92 = +25.33 kr ✅
```

**This is NOT traditional arbitrage** (export trading)
**This IS load shifting** (time-shift self-consumption to higher-value hours)

---

## 4. Why Alternative Methods Work Better

### Method 1: Price-Based Classification (Heuristic)

```
Define arbitrage as:
  - Charge when spot < median (0.665 kr/kWh)
  - Discharge when spot > median

Results:
  Charge low: 12,315 kWh @ 0.487 kr/kWh avg
  Discharge high: 12,512 kWh @ 0.987 kr/kWh avg
  Spread: +0.500 kr/kWh

Estimated arbitrage value: +6,152 kr/year ✅
```

**Why this works**:
- Captures ACTUAL temporal price arbitrage behavior
- Correctly pairs low-price charging with high-price discharging
- Doesn't mix with PV-based self-consumption

**Weakness**:
- Still doesn't distinguish discharge-to-export vs discharge-to-avoid-import
- Oversimplifies: assumes median is the right threshold

### Method 2: Temporal Tracking (FIFO/LIFO)

**FIFO (First-In-First-Out)**:
```
10:00 - Charge 30 kWh from PV → Tag as "PV energy"
12:00 - Charge 20 kWh from grid @ 0.60 kr/kWh → Tag as "Grid-0.60"
19:00 - Discharge 30 kWh → Consumes "PV energy" first (FIFO)
20:00 - Discharge 20 kWh → Consumes "Grid-0.60"

Value calculation:
  PV discharge (19:00): Avoided import @ 1.20 kr/kWh = "egetforbruk"
  Grid discharge (20:00): Avoided 1.20 kr/kWh, paid 0.60 kr/kWh = "arbitrage"
```

**LIFO (Last-In-First-Out)**:
```
Same charging as above
19:00 - Discharge 30 kWh → Consumes "Grid-0.60" first (LIFO)
20:00 - Discharge 20 kWh → Consumes "PV energy"

Different attribution, same total value
```

**Why this works**:
- Preserves temporal causality
- Each discharge traced to specific charge source
- Enables accurate separation of PV vs grid-sourced discharge

**Implementation complexity**:
- Requires tracking battery state-of-charge components
- Need queue data structure (FIFO) or stack (LIFO)
- More compute-intensive

### Method 3: Eliminate "Arbitrage" Category

**Simplest solution**: Don't separate arbitrage at all

**New category structure**:
1. **Peak shaving**: Curtailment prevention (PV > 77 kW grid limit)
2. **Avoided import**: ALL discharge that reduces grid import
   - Includes PV self-consumption shifting
   - Includes load-shifting from low-price to high-price hours
   - Includes tariff optimization (off-peak → peak)
3. **Power tariff reduction**: Monthly peak demand reduction

**Value calculation**:
```
Avoided import value = Σ(discharge × avoided_import_price)
  where avoided_import_price = spot + tariff + tax at discharge time

Cost of import for charging = Σ(charge_from_grid × import_price)
  where import_price = spot + tariff + tax at charge time

Net battery value = Avoided import - Charging cost - Peak shaving + Power tariff reduction
```

**Why this works**:
- Reflects actual economic benefit (avoided import vs export)
- No need to distinguish "why" battery charged (PV vs arbitrage)
- Simpler stakeholder communication
- Aligns with Norwegian tariff structure (no export compensation)

---

## 5. Recommended Solution

### For Stakeholder Communication

**Use 3-category model** (eliminate arbitrage):

```
1. Peak Shaving (Curtailment Prevention)
   - Value: Avoided curtailment of PV production
   - Metric: kWh of PV saved from grid limit
   - Annual value: ~X kr/year

2. Self-Consumption Optimization (Avoided Import)
   - Value: Import reduction through PV time-shifting + load-shifting
   - Metric: kWh of import avoided × (spot + tariff + tax)
   - Annual value: ~Y kr/year

3. Power Tariff Reduction
   - Value: Lower monthly peak demand charges
   - Metric: Reduction in monthly kW peak
   - Annual value: ~Z kr/year

Total battery value: X + Y + Z
```

**Rationale**:
- Clear, non-overlapping categories
- Matches actual battery operation in Norwegian market
- Avoids confusing "arbitrage" term (implies export trading)
- Aligns with tariff structure (import vs export asymmetry)

### For Technical Analysis

**Use price-based classification** as intermediate step:

```python
# Quick approximation for sensitivity analysis
median_price = spot_prices.median()

low_price_charge = charge_hours[spot < median_price]
high_price_discharge = discharge_hours[spot > median_price]

arbitrage_value_estimate = (
    high_price_discharge.sum() * avg_high_price
    - low_price_charge.sum() * avg_low_price
)
```

**Use temporal tracking (FIFO)** for accurate attribution:

```python
# Production-grade implementation
battery_content = []  # Queue: [(energy_kwh, source, price, timestamp), ...]

# Charging
if pv_surplus > 0:
    battery_content.append((charge_kw, 'PV', pv_value, t))
else:
    battery_content.append((charge_kw, 'Grid', import_price, t))

# Discharging (FIFO)
while discharge_remaining > 0 and battery_content:
    energy, source, charge_price, charge_time = battery_content.pop(0)
    discharge_value = avoided_import_price[t]

    if source == 'PV':
        category = 'egetforbruk'
    else:
        category = 'arbitrage'

    value = discharge_value - charge_price
```

---

## 6. Answers to Specific Questions

### Q1: Why does the proportional method fail?

**Answer**: It assumes annual charging proportions apply uniformly to all discharge events, ignoring temporal causality. Battery operation is inherently sequential (charge → store → discharge), but proportional allocation treats it as a simultaneous blend.

Example: If 70% of annual charging is from grid, proportional method assumes 70% of EVERY discharge came from grid. In reality, a specific discharge at hour 19 came from a specific charge at hour 10 (which might have been 100% PV).

### Q2: Why is tariff asymmetry hurting us?

**Answer**: Tariff asymmetry only "hurts" if you interpret discharge as export (arbitrage). Since you discharge during high-tariff hours (0.254 kr/kWh) but only export at spot price (NO tariff), you "lose" the tariff difference.

**BUT**: If discharge avoids import (reality), high discharge tariff is GOOD! You save 0.254 kr/kWh while only paying 0.219 kr/kWh charging tariff → net gain +0.035 kr/kWh.

The proportional method can't distinguish these two scenarios, so it incorrectly treats all discharge as if some portion goes to export.

### Q3: What's the correct way to separate "egetforbruk" from "arbitrage"?

**Options ranked by accuracy**:

1. **Temporal tracking (FIFO/LIFO)**: Most accurate, preserves causality
   - Implementation: Queue or stack data structure tracking battery content
   - Complexity: Moderate (need state tracking across timesteps)

2. **Price-based classification**: Good approximation, simpler
   - Implementation: Classify by spot price vs median/threshold
   - Complexity: Low (single pass through data)
   - Weakness: Doesn't distinguish discharge destination

3. **Discharge destination tracking**: Best for Norwegian market
   - Implementation: Track if discharge reduces import or increases export
   - Complexity: Moderate (need net flow calculation)
   - Advantage: Matches actual economic benefit

### Q4: Is "arbitrage" even a separate category?

**Answer**: No, it shouldn't be in the Norwegian context.

**Why**:
- Norwegian "plusskunder" don't receive meaningful export compensation
- Tariff structure penalizes export (pay import tariff, no export tariff revenue)
- Battery strategy is optimized for import reduction, NOT export
- Mixing "arbitrage" (export trading) with "load shifting" (import reduction) creates confusion

**Better framing**: All battery discharge is "avoided import" with different timing strategies:
- PV time-shifting: Store midday PV for evening use
- Load-shifting: Import during cheap hours for expensive hours
- Curtailment prevention: Store excess PV that would be curtailed

All three achieve the same economic outcome: **reduced grid import cost**

### Q5: The tariff paradox - how to value discharge correctly?

**Answer**: Discharge value depends on what it AVOIDS, not what it produces.

**Incorrect (export arbitrage framing)**:
```
Discharge value = spot_price_at_discharge
  → Ignores that you don't get tariff revenue on export
  → Makes high-tariff discharge look worse
```

**Correct (avoided import framing)**:
```
Discharge value = avoided_import_cost_at_discharge
                = spot + tariff + tax at discharge time
  → Captures full benefit of NOT importing
  → Makes high-tariff discharge look better (correct!)
```

**Example**:
```
Hour 19 discharge (30 kWh):
  Spot: 1.20 kr/kWh
  Tariff: 0.296 kr/kWh (peak)
  Tax: 0.179 kr/kWh

Export value: 30 × 1.20 = 36 kr ❌ (wrong framing)
Avoided import value: 30 × (1.20 + 0.296 + 0.179) = 50.25 kr ✅ (correct)
```

---

## 7. Implementation Recommendations

### Immediate Fix (Reports)

**Replace proportional allocation with price-based classification**:

```python
# reports/analyze_arbitrage.py
median_price = data["price_nok"].median()

# Arbitrage = charge low, discharge high
arbitrage_charge = data[
    (data["P_charge_kw"] > 0) &
    (data["price_nok"] < median_price) &
    (data["pv_surplus_kw"] <= 0)  # From grid, not PV
]["P_charge_kw"].sum()

arbitrage_discharge = data[
    (data["P_discharge_kw"] > 0) &
    (data["price_nok"] > median_price)
]["P_discharge_kw"].sum()

arbitrage_value = (
    arbitrage_discharge * avg_high_price
    - arbitrage_charge * avg_low_price
)
```

### Medium-term (Optimizer)

**Add discharge destination tracking**:

```python
# core/lp_monthly_optimizer.py
for t in range(T):
    # Track where discharge goes
    discharge_to_load = min(P_discharge[t], load[t] - pv_production[t])
    discharge_to_export = P_discharge[t] - discharge_to_load

    # Value discharge correctly
    avoided_import_value = discharge_to_load * (spot[t] + tariff[t] + tax)
    export_value = discharge_to_export * spot[t]  # No tariff benefit
```

### Long-term (Refactor)

**Eliminate arbitrage category, use 3-category model**:

```python
value_drivers = {
    'peak_shaving': curtailment_prevented_kwh * avg_pv_value,
    'avoided_import': discharge_to_load_kwh * avg_avoided_import_price - grid_charging_cost,
    'power_tariff_reduction': monthly_peak_reduction_kw * power_tariff_rate * 12
}

total_value = sum(value_drivers.values())
```

---

## Conclusion

**The negative arbitrage result is NOT a bug** - it's revealing a conceptual flaw in how we define "arbitrage" for batteries in the Norwegian market context.

**Root cause**: Proportional allocation method mixes temporal relationships, incorrectly attributing PV-charged energy as "arbitrage" discharge.

**Real issue**: "Arbitrage" as export trading doesn't exist in Norwegian plusskunde context. Battery value comes from avoided import, not export revenue.

**Solution**: Either implement temporal tracking (FIFO) for accurate attribution, or simplify to "avoided import" as single category, or use price-based classification for quick estimates.

**For stakeholders**: Frame battery value as (1) Peak shaving, (2) Avoided import (PV + load shifting), (3) Power tariff reduction. This aligns with actual operation and Norwegian tariff structure.
