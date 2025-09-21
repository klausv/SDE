# MILP Battery Optimization - Mathematical Formulation

## 📊 Problem Overview
**Objective:** Maximize NPV of battery investment for 150 kWp solar with 77 kW grid limit

---

## 🎯 Decision Variables

### Primary Variables (Sizing)
| Variable | Domain | Description |
|----------|--------|-------------|
| **x_cap** | [10, 200] | Battery capacity (kWh) |
| **x_pow** | [10, 100] | Battery power (kW) |

### Operational Variables (∀t ∈ T)
| Variable | Domain | Description |
|----------|--------|-------------|
| **c_t** | [0, 100] | Charging power at t (kW) |
| **d_t** | [0, 100] | Discharging power at t (kW) |
| **s_t** | [0, 200] | State of charge at t (kWh) |
| **g_imp_t** | ℝ⁺ | Grid import at t (kW) |
| **g_exp_t** | [0, 77] | Grid export at t (kW) |
| **ℓ_t** | ℝ⁺ | Curtailment at t (kW) |

### Binary Variables
- **δ_t ∈ {0,1}** - Charging indicator (1=charging, 0=discharging)
- **τ_{m,i} ∈ {0,1}** - Tariff tier m, level i selection

---

## 📈 Objective Function

### Maximize NPV:
```
MAX Z = Σ(y=1 to 15) [R_y · (1-0.02y) / (1+r)^y] - I
```

Where:
- **R_y** = Annual revenue year y
- **r** = 0.05 (discount rate)
- **I** = x_cap · 3000 NOK (investment)

### Revenue Components:
```
R_y = R_arbitrage + R_tariff + R_curtailment
```

---

## 🔒 Constraints

### 1️⃣ **C-rate Constraints**
```
0.25 · x_cap ≤ x_pow ≤ 1.0 · x_cap
```

### 2️⃣ **Power Limits**
```
c_t ≤ x_pow    ∀t ∈ T
d_t ≤ x_pow    ∀t ∈ T
```

### 3️⃣ **SOC Bounds**
```
0.1 · x_cap ≤ s_t ≤ 0.9 · x_cap    ∀t ∈ T
```

### 4️⃣ **Mutual Exclusion (Big-M)**
```
c_t ≤ M · δ_t           ∀t ∈ T
d_t ≤ M · (1 - δ_t)     ∀t ∈ T
```
Where M = 1000

### 5️⃣ **Energy Balance**
```
PV_t - L_t + g_imp_t - g_exp_t - ℓ_t = c_t - d_t    ∀t ∈ T
```

### 6️⃣ **SOC Dynamics**
```
s_t = s_{t-1} + η·c_t - d_t/η    ∀t > 1
s_1 = 0.5 · x_cap                 (initial)
```
Where η = √0.9 (efficiency)

### 7️⃣ **Cyclic SOC**
```
s_{end_day} ≤ s_{start_day}    ∀ days
```

### 8️⃣ **Minimum Utilization**
```
Σ d_t ≥ 0.5 · x_cap · n_days
```

### 9️⃣ **Max Daily DOD**
```
Σ(day) d_t ≤ 0.8 · x_cap    ∀ days
```

### 🔟 **Peak Power Tracking**
```
P_peak_m ≥ g_imp_t    ∀t in month m
```

### 1️⃣1️⃣ **Tariff Selection**
```
Σ τ_{m,i} = 1    ∀m ∈ M
```

### 1️⃣2️⃣ **Tariff-Peak Linkage**
```
If τ_{m,i} = 1:
    B_{i-1} ≤ P_peak_m ≤ B_i
```
Tariff boundaries B = {2, 5, 10, 15, 20, 25, 50, 75, 100, 200} kW

---

## 🧮 Problem Classification

### **Mixed-Integer Linear Program (MILP)**

| Property | Value |
|----------|-------|
| **Variables** | ~3,500 (continuous + binary) |
| **Constraints** | ~4,000 |
| **Complexity** | NP-hard |
| **Solver** | CBC (Branch & Bound) |
| **Optimality** | Global (within linear model) |

---

## 🔧 Key Modeling Techniques

### **Big-M Method**
- Avoids bilinear terms in charge/discharge mutual exclusion
- M = 1000 (sufficiently large constant)

### **Piecewise Linear Tariffs**
- Binary variables select active tariff tier
- Linear constraints link peak to tier

### **Time Discretization**
- 288 timesteps (12 typical days × 24 hours)
- Scales to full year via factors

### **Efficiency Model**
- Round-trip: η² = 0.9
- One-way: η = √0.9 ≈ 0.949

---

## 💻 Implementation

### Solver Hierarchy:
1. **OR-Tools CBC** (Google)
2. **PuLP CBC** (Python)
3. **HiGHS** (scipy)

### Typical Solution:
- **Capacity:** 80-100 kWh
- **Power:** 40-60 kW
- **C-rate:** 0.5-0.6C
- **Computation:** 30-60 seconds
- **Gap:** < 0.1% (near-optimal)