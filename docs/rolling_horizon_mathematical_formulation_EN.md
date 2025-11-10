# Mathematical Formulation: 24-Hour Rolling Horizon Optimization Model

**Documentation for battery optimization rolling horizon optimizer**

Based on the implementation in `battery_optimization/core/rolling_horizon_optimizer.py`

---

## SCQA INTRODUCTION

**Situation**: Rolling horizon optimization is a strategic approach for battery management where the system continuously re-optimizes over a 24-hour horizon based on spot price forecasts, solar production, and consumption patterns.

**Complication**: Battery management under uncertainty requires simultaneous optimization of three conflicting objectives: minimize energy costs (arbitrage), reduce power tariffs (peak shaving), and limit battery degradation (lifetime). Incorrect balancing leads to either suboptimal revenues or accelerated battery wear.

**Question**: How is the mathematical optimization problem formulated to balance economic gain and degradation over a 24-hour horizon with 15-minute resolution?

**Answer (MAIN MESSAGE)**:

A linear program (LP) with 1067 variables minimizes total cost $J = J_{\text{energy}} + J_{\text{degradation}} + J_{\text{tariff}}$ through optimization of battery charging/discharging $P_{\text{charge},t}, P_{\text{discharge},t}$ over 96 timesteps ($T = 96$, $\Delta t = 0.25$ hours), subject to energy balance, battery dynamics, degradation conditions (LFP dual-mode: cyclic vs calendar), and progressive power tariff structure with 10 Lnett brackets. The solver (HiGHS) solves the problem in 0.5-2 seconds and returns optimal control action $P_{\text{battery}}^{\text{setpoint}}$ for the next timestep.

---

## MAIN MESSAGE: THE COMPLETE OPTIMIZATION PROBLEM

Minimizes total cost over 24-hour horizon ($T = 96$ timesteps, $\Delta t = 0.25$ hours):

$$
\boxed{
\begin{aligned}
\min_{P, E, DP, z} \quad J = &\sum_{t=0}^{T-1} \Bigg[ c_{\text{import},t} P_{\text{grid},t}^{\text{import}} \Delta t - c_{\text{export},t} P_{\text{grid},t}^{\text{export}} \Delta t \\
&\quad + c_{\text{deg}}^{\text{percent}} DP_{\text{total},t} + 0.01 P_{\text{curtail},t} \Bigg] \\
&+ \sum_{i=0}^{N_{\text{trinn}}-1} c_{\text{trinn},i} z_i - c_{\text{baseline}}^{\text{tariff}}
\end{aligned}
}
$$

Subject to the following constraints:

**Energy Balance** ($T$ constraints):
$$
P_{\text{grid},t}^{\text{import}} - P_{\text{grid},t}^{\text{export}} - P_{\text{charge},t} + P_{\text{discharge},t} - P_{\text{curtail},t} = \text{Load}_t - \text{PV}_t
$$

**Battery Dynamics** ($T$ constraints):
$$
E_{\text{battery},t} = E_{\text{battery},t-1} + \left( \eta_{\text{charge}} P_{\text{charge},t-1} - \frac{P_{\text{discharge},t-1}}{\eta_{\text{discharge}}} \right) \Delta t, \quad E_{\text{battery},0} = E_{\text{initial}}
$$

**Degradation - Dual-Mode LFP** ($5T$ constraints):
$$
\begin{aligned}
DP_{\text{cyc},t} &= \rho_{\text{constant}} \cdot \text{DOD}_{\text{abs},t}, \quad \text{DOD}_{\text{abs},t} = \frac{E_{\Delta,t}^{+} + E_{\Delta,t}^{-}}{E_{\text{nom}}} \\
DP_{\text{total},t} &\geq \max\left(DP_{\text{cyc},t}, dp_{\text{cal}}^{\text{timestep}}\right)
\end{aligned}
$$

**Progressive Power Tariff** ($1 + N_{\text{trinn}}$ constraints):
$$
P_{\text{peak}}^{\text{new}} = \sum_{i=0}^{N_{\text{trinn}}-1} p_{\text{trinn},i} z_i, \quad P_{\text{grid},t}^{\text{import}} \leq P_{\text{peak}}^{\text{new}}, \quad z_i \leq z_{i-1}
$$

**Variable Constraints**:
- $P_{\text{charge},t}, P_{\text{discharge},t} \in [0, P_{\text{max}}]$
- $P_{\text{grid},t}^{\text{import}}, P_{\text{grid},t}^{\text{export}} \in [0, 70 \text{ kW}]$
- $E_{\text{battery},t} \in [\text{SOC}_{\min} E_{\text{nom}}, \text{SOC}_{\max} E_{\text{nom}}]$
- $z_i \in [0, 1]$

**Interpretation**: This LP problem with 1067 variables and 778 constraints balances three cost components: energy cost (arbitrage through import/export optimization), degradation cost (LFP dual-mode: maximum of cyclic and calendar wear), and power tariff (progressive 10-bracket Lnett structure). The HiGHS solver solves the problem in 0.5-2 seconds and returns optimal battery control for the next timestep: $P_{\text{battery}}^{\text{setpoint}} = P_{\text{charge},0} - P_{\text{discharge},0}$ [kW].

---

## DETAILED ANALYSIS

### Chapter 1: Objective Function - Three Cost Components

The objective function minimizes total cost over the 24-hour horizon through three components:

$$
\boxed{
J = J_{\text{energy}} + J_{\text{degradation}} + J_{\text{tariff}} + J_{\text{curtailment}}
}
$$

#### 1.1 Energy Cost - Import/Export Arbitrage

**Energy cost** represents net cost for grid import minus revenue from grid export:

$$
J_{\text{energy}} = \sum_{t=0}^{T-1} \left[ c_{\text{import},t} P_{\text{grid},t}^{\text{import}} \Delta t - c_{\text{export},t} P_{\text{grid},t}^{\text{export}} \Delta t \right]
$$

**Import cost** consists of three components:

$$
c_{\text{import},t} = p_{\text{spot},t} + c_{\text{energy},t} + c_{\text{tax},t}
$$

where:
- $p_{\text{spot},t}$: Nordpool spot price [NOK/kWh]
- $c_{\text{energy},t}$: Energy tariff, 0.296 NOK/kWh peak hours (Mon-Fri 06:00-22:00), 0.176 NOK/kWh off-peak
- $c_{\text{tax},t} = 0.15$ NOK/kWh: Consumption tax

**Export revenue**:

$$
c_{\text{export},t} = p_{\text{spot},t} + 0.04 \text{ NOK/kWh}
$$

The export premium of 0.04 NOK/kWh compensates for grid tariff asymmetry.

#### 1.2 Degradation Cost - Battery Wear

**Degradation cost** measures the value reduction of the battery due to wear:

$$
J_{\text{degradation}} = \sum_{t=0}^{T-1} c_{\text{deg}}^{\text{percent}} DP_{\text{total},t}
$$

**Degradation cost per percentage point**:

$$
c_{\text{deg}}^{\text{percent}} = \frac{c_{\text{battery}} \times E_{\text{nom}}}{\text{EOL}_{\text{deg}}}
$$

With standard values:
- $c_{\text{battery}} = 3054$ NOK/kWh (battery cost)
- $E_{\text{nom}} = 80$ kWh (battery capacity)
- $\text{EOL}_{\text{deg}} = 20\%$ (end-of-life degradation)

gives $c_{\text{deg}}^{\text{percent}} = (3054 \times 80) / 20 = 12{,}216$ NOK/%.

**Economic interpretation**: Each percentage point of degradation costs 12,216 NOK. At 0.01% degradation per day (typical at low activity): 122 NOK/day degradation cost. Annual degradation with calendar aging only: $0.714\% \times 12{,}216 = 8{,}722$ NOK/year.

#### 1.3 Power Tariff Cost - Progressive Bracket Structure

**Power tariff cost** uses progressive LP approach (analogous to tax models):

$$
J_{\text{tariff}} = \sum_{i=0}^{N_{\text{trinn}}-1} c_{\text{trinn},i} z_i - c_{\text{baseline}}^{\text{tariff}}
$$

where:
- $c_{\text{trinn},i}$: Incremental cost per bracket [NOK/kWh/month]
- $z_i \in [0, 1]$: Fill level for bracket $i$ ($z_i = 0$: empty, $z_i = 1$: full)
- $c_{\text{baseline}}^{\text{tariff}}$: Current tariff cost (baseline)

The objective function minimizes **marginal increase** in power tariff beyond baseline.

**Lnett commercial tariff structure**:

| Bracket $i$ | From [kW] | To [kW] | Width $p_{\text{trinn},i}$ [kW] | Cumulative [NOK/month] | Incr. $c_{\text{trinn},i}$ [NOK/month] |
|-------------|-----------|----------|--------------------------------|------------------------|----------------------------------------|
| 0 | 0 | 2 | 2 | 136 | 136 |
| 1 | 2 | 5 | 3 | 232 | 96 |
| 2 | 5 | 10 | 5 | 372 | 140 |
| 3 | 10 | 15 | 5 | 572 | 200 |
| 4 | 15 | 20 | 5 | 772 | 200 |
| 5 | 20 | 25 | 5 | 972 | 200 |
| 6 | 25 | 50 | 25 | 1772 | 800 |
| 7 | 50 | 75 | 25 | 2572 | 800 |
| 8 | 75 | 100 | 25 | 3372 | 800 |
| 9 | 100+ | ∞ | - | 5600 (@ 100 kW) | 2228 |

**Example**: At power peak 12 kW ($z_0 = 1.0$, $z_1 = 1.0$, $z_2 = 1.0$, $z_3 = 0.4$, rest $= 0$):
- Bracket 0: $2 \text{ kW} \times 1.0 = 2 \text{ kW}$ contributes $136$ NOK/month
- Bracket 1: $3 \text{ kW} \times 1.0 = 3 \text{ kW}$ contributes $96$ NOK/month
- Bracket 2: $5 \text{ kW} \times 1.0 = 5 \text{ kW}$ contributes $140$ NOK/month
- Bracket 3: $5 \text{ kW} \times 0.4 = 2 \text{ kW}$ contributes $200 \times 0.4 = 80$ NOK/month
- **Total**: $P_{\text{peak}}^{\text{new}} = 12$ kW, cost $452$ NOK/month

#### 1.4 Curtailment Penalty - Avoid Unnecessary Curtailment

**Curtailment penalty** ($0.01$ NOK/kW) avoids unnecessary solar curtailment:

$$
J_{\text{curtailment}} = 0.01 \sum_{t=0}^{T-1} P_{\text{curtail},t}
$$

The penalty term ensures that the LP solver only uses curtailment when absolutely necessary (e.g., battery full, grid export maximal). The low penalty (0.01 NOK/kW) does not significantly affect economic optimization, but gives preference to avoid curtailment when alternatives exist.

---

### Chapter 2: Physical Constraints - Energy and Battery

#### 2.1 Energy Balance - Kirchhoff's First Law

For each timestep $t \in \{0, 1, \ldots, T-1\}$ the energy balance must hold:

$$
\boxed{
P_{\text{grid},t}^{\text{import}} - P_{\text{grid},t}^{\text{export}} - P_{\text{charge},t} + P_{\text{discharge},t} - P_{\text{curtail},t} = \text{Load}_t - \text{PV}_t
}
$$

**Physical interpretation**:
- **Left side**: Available energy (grid import - grid export - battery charging + battery discharging - curtailment)
- **Right side**: Net load (consumption - solar production)

**Variable roles**:
- $P_{\text{grid},t}^{\text{import}} \in [0, 70]$ kW: Import from grid
- $P_{\text{grid},t}^{\text{export}} \in [0, 70]$ kW: Export to grid
- $P_{\text{charge},t} \in [0, P_{\text{max}}^{\text{charge}}]$ kW: Battery charging (typically 60 kW)
- $P_{\text{discharge},t} \in [0, P_{\text{max}}^{\text{discharge}}]$ kW: Battery discharging (typically 60 kW)
- $P_{\text{curtail},t} \geq 0$ kW: Solar curtailment (only when necessary)

**Input data**:
- $\text{PV}_t$: Solar production [kW] (PVGIS/PVLib)
- $\text{Load}_t$: Consumption [kW] (measured/forecasted)

#### 2.2 Battery Dynamics - State Equation

Battery energy at the next timestep equals previous energy plus charging energy (with charging losses) minus discharging energy (with discharging losses).

**Dynamic equation** ($T-1$ constraints) for $t \in \{1, 2, \ldots, T-1\}$:

$$
\boxed{
E_{\text{battery},t} = E_{\text{battery},t-1} + \left( \eta_{\text{charge}} P_{\text{charge},t-1} - \frac{P_{\text{discharge},t-1}}{\eta_{\text{discharge}}} \right) \Delta t
}
$$

**Initial condition** (1 constraint):

$$
\boxed{
E_{\text{battery},0} = E_{\text{initial}}
}
$$

**Parameter values**:
- $\eta_{\text{charge}} = \eta_{\text{discharge}} = 0.95$ (95% roundtrip efficiency per direction)
- $E_{\text{nom}} = 80$ kWh (nominal battery capacity)
- $\text{SOC}_{\min} = 0.1$, $\text{SOC}_{\max} = 0.9$ (operational SOC limits)
- $E_{\text{battery},t} \in [0.1 \times 80, 0.9 \times 80] = [8, 72]$ kWh

**Energy loss example**:
- Charging: When $P_{\text{charge},t} = 60$ kW, only $0.95 \times 60 = 57$ kW is stored in the battery (5% loss)
- Discharging: To deliver $P_{\text{discharge},t} = 60$ kW, the battery must provide $(60 / 0.95) = 63.16$ kW (5% loss)

#### 2.3 Grid Constraints - Grid Limits

The grid limits import and export to maximum values:

$$
\boxed{
P_{\text{grid}}^{\text{import}} \leq 70 \text{ kW}, \quad P_{\text{grid}}^{\text{export}} \leq 70 \text{ kW}
}
$$

The 70 kW limit reflects inverter capacity (110 kW) × 70% rule (Norwegian grid standard for PV installations). Full PV production (150 kWp) can generate 150+ kW under optimal conditions, but grid export is limited to 70 kW. Excess production must be stored in battery or curtailed.

---

### Chapter 3: Degradation Model - LFP Dual-Mode

LFP batteries degrade primarily by the **dominant mechanism** at each time: at high cyclic activity, cyclic degradation dominates, at low/no activity, calendar degradation dominates.

#### 3.1 Cyclic Degradation - Activity-Based Wear

Cyclic degradation uses **absolute DOD** (Depth of Discharge) as a proxy for rainflow cycle counting:

$$
\boxed{
DP_{\text{cyc},t} = \rho_{\text{constant}} \cdot \text{DOD}_{\text{abs},t}
}
$$

where:

$$
\text{DOD}_{\text{abs},t} = \frac{E_{\Delta,t}^{+} + E_{\Delta,t}^{-}}{E_{\text{nom}}}
$$

**Degradation constant**:

$$
\rho_{\text{constant}} = \frac{\text{EOL}_{\text{deg}}}{\text{cycle}_{\text{life}}^{\text{full DOD}}} = \frac{20\%}{5000} = 0.004 \text{ \%/cycle}
$$

**Parameter values**:
- $\text{cycle}_{\text{life}}^{\text{full DOD}} = 5000$ cycles (100% DOD, LFP standard)
- $\text{EOL}_{\text{deg}} = 20\%$ (end-of-life degradation)
- $\rho_{\text{constant}} = 0.004$ %/cycle

**Absolute energy change** is implemented using LP decomposition:

**Energy-delta balance** for $t = 0$:

$$
E_{\Delta,0}^{+} - E_{\Delta,0}^{-} - E_{\text{battery},0} = -E_{\text{initial}}
$$

For $t \in \{1, 2, \ldots, T-1\}$:

$$
E_{\Delta,t}^{+} - E_{\Delta,t}^{-} - E_{\text{battery},t} + E_{\text{battery},t-1} = 0
$$

The relationship $E_{\Delta,t}^{+} - E_{\Delta,t}^{-} = \Delta E_t$ decomposes as:
- **Charging** ($\Delta E_t > 0$): $E_{\Delta,t}^{+} = \Delta E_t$, $E_{\Delta,t}^{-} = 0$
- **Discharging** ($\Delta E_t < 0$): $E_{\Delta,t}^{+} = 0$, $E_{\Delta,t}^{-} = |\Delta E_t|$

**DOD definition** ($T$ constraints):

$$
\boxed{
\text{DOD}_{\text{abs},t} = \frac{E_{\Delta,t}^{+} + E_{\Delta,t}^{-}}{E_{\text{nom}}}
}
$$

**Equivalent full cycles over 24 hours**:

$$
\text{Cycles}_{\text{eq}}^{24h} = \sum_{t=0}^{T-1} \text{DOD}_{\text{abs},t}
$$

**Example**: At 0.5 equivalent cycles per day (typical with active arbitrage):
- Cyclic degradation: $0.5 \times 0.004\% = 0.002\%$ per day
- Annual degradation: $0.002\% \times 365 = 0.73\%$ per year
- Lifetime: $20\% / 0.73\% = 27.4$ years

#### 3.2 Calendar Degradation - Time-Based Wear

Calendar degradation per timestep:

$$
\boxed{
dp_{\text{cal}}^{\text{timestep}} = \frac{\text{EOL}_{\text{deg}}}{\text{cal}_{\text{life}} \times 365 \times 24} \times \Delta t
}
$$

**Parameter values**:
- $\text{cal}_{\text{life}} = 28$ years (calendar life, LFP standard)
- $\text{EOL}_{\text{deg}} = 20\%$ (end-of-life degradation)
- $\Delta t = 0.25$ hours (15-minute timestep)

$$
dp_{\text{cal}}^{\text{timestep}} = \frac{20\%}{28 \times 365 \times 24} \times 0.25 = 0.000204 \text{ \%/timestep}
$$

**Annual calendar degradation**: $20\% / 28 \text{ years} = 0.714\%$ per year.

**Calendar cost per day** (with no activity):
- Degradation: $0.000204\% \times 96 \text{ timesteps} = 0.0196\%$ per day
- Cost: $0.0196\% \times 12{,}216 \text{ NOK/\%} = 239$ NOK/day
- Annual: $239 \text{ NOK/day} \times 365 = 87{,}235$ NOK/year

#### 3.3 Total Degradation - Maximum Function

Total degradation is the **maximum** of cyclic and calendar degradation at each timestep:

$$
\boxed{
DP_{\text{total},t} = \max\left(DP_{\text{cyc},t}, dp_{\text{cal}}^{\text{timestep}}\right)
}
$$

**LP implementation** uses two inequality constraints:

**Constraint 1**: Total ≥ Cyclic ($T$ constraints):

$$
DP_{\text{total},t} \geq DP_{\text{cyc},t}
$$

**Constraint 2**: Total ≥ Calendar ($T$ constraints):

$$
DP_{\text{total},t} \geq dp_{\text{cal}}^{\text{timestep}}
$$

The LP solver will automatically set $DP_{\text{total},t}$ to the **minimum value** that satisfies both constraints, i.e., the **maximum value** of the two.

**Degradation cost**:

$$
C_{\text{degradation}} = \sum_{t=0}^{T-1} c_{\text{deg}}^{\text{percent}} \cdot DP_{\text{total},t}
$$

With $c_{\text{deg}}^{\text{percent}} = 12{,}216$ NOK/%.

**Physical interpretation**: At high activity (e.g., $\text{DOD}_{\text{abs},t} = 0.1$, i.e., 10% DOD):
- Cyclic: $DP_{\text{cyc},t} = 0.004\% \times 0.1 = 0.0004\%$ (0.04% per timestep)
- Calendar: $dp_{\text{cal}}^{\text{timestep}} = 0.000204\%$
- Total: $DP_{\text{total},t} = \max(0.0004\%, 0.000204\%) = 0.0004\%$ (cyclic dominates)

At no activity ($\text{DOD}_{\text{abs},t} = 0$):
- Cyclic: $DP_{\text{cyc},t} = 0\%$
- Calendar: $dp_{\text{cal}}^{\text{timestep}} = 0.000204\%$
- Total: $DP_{\text{total},t} = \max(0\%, 0.000204\%) = 0.000204\%$ (calendar dominates)

---

### Chapter 4: Economic Model - Progressive Power Tariff

The power tariff is implemented as a **progressive bracket structure** (analogous to tax models). Continuous variables $z_i \in [0, 1]$ represent the fill level for bracket $i$, with progressive activation $z_i \leq z_{i-1}$ ensuring that lower brackets are filled first.

#### 4.1 Power Peak Definition

The new monthly power peak is defined as the sum of filled bracket widths:

$$
\boxed{
P_{\text{peak}}^{\text{new}} = \sum_{i=0}^{N_{\text{trinn}}-1} p_{\text{trinn},i} z_i
}
$$

**Lnett commercial tariff structure**:

| Bracket $i$ | From [kW] | To [kW] | Width $p_{\text{trinn},i}$ [kW] | Cumulative [NOK/month] | Incr. $c_{\text{trinn},i}$ [NOK/month] |
|-------------|-----------|----------|--------------------------------|------------------------|----------------------------------------|
| 0 | 0 | 2 | 2 | 136 | 136 |
| 1 | 2 | 5 | 3 | 232 | 96 |
| 2 | 5 | 10 | 5 | 372 | 140 |
| 3 | 10 | 15 | 5 | 572 | 200 |
| 4 | 15 | 20 | 5 | 772 | 200 |
| 5 | 20 | 25 | 5 | 972 | 200 |
| 6 | 25 | 50 | 25 | 1772 | 800 |
| 7 | 50 | 75 | 25 | 2572 | 800 |
| 8 | 75 | 100 | 25 | 3372 | 800 |
| 9 | 100+ | ∞ | - | 5600 (@ 100 kW) | 2228 |

**Example 1**: Power peak 12 kW
- Bracket 0: $z_0 = 1.0$ (full), contributes $2 \times 1.0 = 2$ kW, cost $136$ NOK/month
- Bracket 1: $z_1 = 1.0$ (full), contributes $3 \times 1.0 = 3$ kW, cost $96$ NOK/month
- Bracket 2: $z_2 = 1.0$ (full), contributes $5 \times 1.0 = 5$ kW, cost $140$ NOK/month
- Bracket 3: $z_3 = 0.4$ (partial), contributes $5 \times 0.4 = 2$ kW, cost $200 \times 0.4 = 80$ NOK/month
- **Total**: $P_{\text{peak}}^{\text{new}} = 2 + 3 + 5 + 2 = 12$ kW, cost $452$ NOK/month

**Example 2**: Power peak 75 kW
- Brackets 0-6: Fully filled ($z_0$ through $z_6 = 1.0$), contribute $2+3+5+5+5+5+25 = 50$ kW
- Bracket 7: Fully filled ($z_7 = 1.0$), contributes $25$ kW, cost $800$ NOK/month
- Brackets 8-9: Empty ($z_8 = z_9 = 0$)
- **Total**: $P_{\text{peak}}^{\text{new}} = 75$ kW, cost $2{,}572$ NOK/month

#### 4.2 Power Peak Tracking

For each timestep $t$, the new power peak must be at least equal to the grid import:

$$
\boxed{
P_{\text{grid},t}^{\text{import}} \leq P_{\text{peak}}^{\text{new}}
}
$$

This ensures that the LP variable $P_{\text{peak}}^{\text{new}}$ is automatically set to:

$$
P_{\text{peak}}^{\text{new}} = \max\left(P_{\text{peak}}^{\text{current}}, \max_{t} P_{\text{grid},t}^{\text{import}}\right)
$$

**Interpretation**: The power peak is the maximum of the current baseline ($P_{\text{peak}}^{\text{current}}$) and the maximum grid import in the 24-hour window. The LP solver automatically finds the optimal balance between reducing power peak (via battery charging/discharging) and accepting higher power peak when the costs of peak shaving exceed the tariff cost.

#### 4.3 Ordered Bracket Activation

For $i \in \{1, 2, \ldots, N_{\text{trinn}}-1\}$:

$$
\boxed{
z_i \leq z_{i-1}
}
$$

Higher brackets can only be filled if lower brackets are filled (progressive tax structure).

**Valid solution**: $z_0 = 1.0$, $z_1 = 0.8$, $z_2 = 0.3$ (satisfies $1.0 \geq 0.8 \geq 0.3$)

**Invalid solution**: $z_0 = 0.5$, $z_1 = 1.0$ (violates $z_1 \leq z_0$)

#### 4.4 Progressive Tariff Cost

$$
\boxed{
C_{\text{tariff}}^{\text{progressive}} = \sum_{i=0}^{N_{\text{trinn}}-1} c_{\text{trinn},i} z_i
}
$$

**Why progressive LP approach instead of MILP?**

1. **Fast solution time**: LP solves in ~1 second vs potentially minutes with MILP (Mixed-Integer Linear Programming)
2. **Correct optimization direction**: Progressive approach gives correct incentive to reduce power peak
3. **Sufficient accuracy**: For operational control with frequent re-optimization (every 15-60 min), accuracy is sufficient
4. **Conservative underestimation**: Progressive < step-function, but corrected in post-processing for reporting
5. **Robustness**: Rolling horizon re-optimizes continuously, so inaccuracies are quickly corrected

**Objective function**: Minimizes **marginal increase** in tariff cost:

$$
J_{\text{tariff}} = \sum_{i=0}^{N_{\text{trinn}}-1} c_{\text{trinn},i} z_i - c_{\text{baseline}}^{\text{tariff}}
$$

where $c_{\text{baseline}}^{\text{tariff}} = f_{\text{tariff}}(P_{\text{peak}}^{\text{current}})$ is the current tariff cost. This minimizes the **marginal increase** in power tariff beyond baseline.

---

## EVIDENCE (Appendices)

### Appendix A: Complete Parameters and Variables

#### A.1 Indices and Timesteps

The optimization problem operates over a 24-hour horizon with $T = 96$ timesteps (15-minute resolution) where $t \in \{0, 1, \ldots, 95\}$ and timestep size $\Delta t = 0.25$ hours.

#### A.2 Battery Parameters

| Parameter | Symbol | Value | Unit |
|-----------|--------|-------|-------|
| Nominal capacity | $E_{\text{nom}}$ | 80 | kWh |
| Max charging power | $P_{\text{max}}^{\text{charge}}$ | 60 | kW |
| Max discharging power | $P_{\text{max}}^{\text{discharge}}$ | 60 | kW |
| Charging efficiency | $\eta_{\text{charge}}$ | 0.95 | - |
| Discharging efficiency | $\eta_{\text{discharge}}$ | 0.95 | - |
| Roundtrip efficiency | $\eta_{\text{charge}} \times \eta_{\text{discharge}}$ | 0.9025 | - |
| Min SOC | $\text{SOC}_{\min}$ | 0.1 | - |
| Max SOC | $\text{SOC}_{\max}$ | 0.9 | - |

#### A.3 Grid and Tariff Parameters

| Parameter | Symbol | Value | Unit |
|-----------|--------|-------|-------|
| Max grid import | $P_{\text{grid}}^{\text{import,max}}$ | 70 | kW |
| Max grid export | $P_{\text{grid}}^{\text{export,max}}$ | 70 | kW |
| Energy tariff peak | $c_{\text{energy}}^{\text{peak}}$ | 0.296 | NOK/kWh |
| Energy tariff off-peak | $c_{\text{energy}}^{\text{off-peak}}$ | 0.176 | NOK/kWh |
| Consumption tax | $c_{\text{tax}}$ | 0.15 | NOK/kWh |
| Export premium | - | 0.04 | NOK/kWh |
| Number of power tariff brackets | $N_{\text{trinn}}$ | 10 | - |
| Bracket widths | $p_{\text{trinn},i}$ | 2, 3, 5, 5, 5, 5, 25, 25, 25, ∞ | kW |
| Incremental costs | $c_{\text{trinn},i}$ | 136, 96, 140, 200, 200, 200, 800, 800, 800, 2228 | NOK/month |

#### A.4 Degradation Parameters (LFP Battery)

| Parameter | Symbol | Value | Unit |
|-----------|--------|-------|-------|
| Cyclic lifetime (100% DOD) | $\text{cycle}_{\text{life}}^{\text{full DOD}}$ | 5000 | cycles |
| Calendar lifetime | $\text{cal}_{\text{life}}$ | 28 | years |
| End-of-life degradation | $\text{EOL}_{\text{deg}}$ | 20 | % |
| Cyclic degradation constant | $\rho_{\text{constant}}$ | 0.004 | %/cycle |
| Calendar degradation per timestep | $dp_{\text{cal}}^{\text{timestep}}$ | 0.000204 | %/timestep |
| Battery cost | $c_{\text{battery}}$ | 3054 | NOK/kWh |
| Degradation cost per % | $c_{\text{deg}}^{\text{percent}}$ | 12,216 | NOK/% |

#### A.5 State-Dependent Parameters

| Parameter | Symbol | Unit | Description |
|-----------|--------|-------|-------------|
| Initial battery energy | $E_{\text{initial}}$ | kWh | Current battery energy state |
| Current power peak | $P_{\text{peak}}^{\text{current}}$ | kW | Monthly power peak (baseline) |

#### A.6 Time Series Inputs

| Parameter | Symbol | Unit | Source |
|-----------|--------|-------|-------|
| Solar production | $\text{PV}_t$ | kW | PVGIS/PVLib |
| Consumption | $\text{Load}_t$ | kW | Measured/forecasted |
| Spot price | $p_{\text{spot},t}$ | NOK/kWh | Nordpool |

#### A.7 Decision Variables - Complete List

The problem has a total of $11T + 1 + N_{\text{trinn}} = 1057 + N_{\text{trinn}} = 1067$ continuous variables.

**Physical variables** ($6T = 576$ variables):

| Variable | Symbol | Bounds | Unit | Description |
|----------|--------|---------|-------|-------------|
| Charging power | $P_{\text{charge},t}$ | $[0, 60]$ | kW | Battery charging |
| Discharging power | $P_{\text{discharge},t}$ | $[0, 60]$ | kW | Battery discharging |
| Grid import | $P_{\text{grid},t}^{\text{import}}$ | $[0, 70]$ | kW | Import from grid |
| Grid export | $P_{\text{grid},t}^{\text{export}}$ | $[0, 70]$ | kW | Export to grid |
| Battery energy | $E_{\text{battery},t}$ | $[8, 72]$ | kWh | Energy state |
| Solar curtailment | $P_{\text{curtail},t}$ | $[0, \infty)$ | kW | Curtailment |

**Degradation variables** ($5T = 480$ variables):

| Variable | Symbol | Bounds | Unit | Description |
|----------|--------|---------|-------|-------------|
| Positive energy change | $E_{\Delta,t}^{+}$ | $[0, 80]$ | kWh | Charging (absolute) |
| Negative energy change | $E_{\Delta,t}^{-}$ | $[0, 80]$ | kWh | Discharging (absolute) |
| Absolute DOD | $\text{DOD}_{\text{abs},t}$ | $[0, 1]$ | - | Depth of discharge (normalized) |
| Cyclic degradation | $DP_{\text{cyc},t}$ | $[0, 20]$ | % | Activity-based wear |
| Total degradation | $DP_{\text{total},t}$ | $[0, 20]$ | % | Maximum (cyclic, calendar) |

**Power tariff variables** ($1 + N_{\text{trinn}} = 11$ variables):

| Variable | Symbol | Bounds | Unit | Description |
|----------|--------|---------|-------|-------------|
| New power peak | $P_{\text{peak}}^{\text{new}}$ | $[\geq P_{\text{peak}}^{\text{current}}]$ | kW | Monthly maximum |
| Bracket fill level | $z_i$ | $[0, 1]$ | - | Fill level for bracket $i$ |

---

### Appendix B: LP Standard Form and Implementation Details

#### B.1 LP Standard Form

Standard LP problem formulation:

$$
\begin{aligned}
\min_{x} \quad & c^T x \\
\text{subject to} \quad & A_{\text{eq}} x = b_{\text{eq}} \\
& A_{\text{ub}} x \leq b_{\text{ub}} \\
& l \leq x \leq u
\end{aligned}
$$

where:
- $x \in \mathbb{R}^{1067}$: Vector of all decision variables
- $c \in \mathbb{R}^{1067}$: Objective function coefficients
- $A_{\text{eq}} \in \mathbb{R}^{481 \times 1067}$: Equality constraint matrix
- $b_{\text{eq}} \in \mathbb{R}^{481}$: Equality constraint vector
- $A_{\text{ub}} \in \mathbb{R}^{297 \times 1067}$: Inequality constraint matrix
- $b_{\text{ub}} \in \mathbb{R}^{297}$: Inequality constraint vector
- $l, u \in \mathbb{R}^{1067}$: Variable bounds

#### B.2 Problem Size

**With $T = 96$ timesteps, $N_{\text{trinn}} = 10$ brackets**:

| Component | Number | Description |
|-----------|--------|-------------|
| **Variables** | $11T + 1 + N_{\text{trinn}} = 1067$ | Decision variables |
| **Equality constraints** | $5T + 1 = 481$ | Energy balance, battery dynamics, degradation |
| **Inequality constraints** | $3T + N_{\text{trinn}} - 1 = 297$ | Power peak tracking, bracket activation, max function |

**Detailed breakdown - Equality constraints ($5T + 1 = 481$)**:
- Energy balance: $T = 96$ constraints
- Battery dynamics: $T = 96$ constraints (incl. initial condition)
- Energy-delta balance: $T = 96$ constraints
- DOD definition: $T = 96$ constraints
- Cyclic degradation: $T = 96$ constraints
- Power peak definition: $1$ constraint

**Detailed breakdown - Inequality constraints ($3T + N_{\text{trinn}} - 1 = 297$)**:
- Power peak tracking: $T = 96$ constraints
- Total degradation ≥ Cyclic: $T = 96$ constraints
- Total degradation ≥ Calendar: $T = 96$ constraints
- Ordered bracket activation: $N_{\text{trinn}} - 1 = 9$ constraints

#### B.3 Sparse Matrix Structure

The constraint matrix is **very sparse** (~1% non-zero elements):
- $A_{\text{eq}}$ ($481 \times 1067$): ~2000 non-zero elements (~0.4%)
- $A_{\text{ub}}$ ($297 \times 1067$): ~300 non-zero elements (~0.1%)

The HiGHS solver efficiently exploits this sparsity through sparse matrix representations and algorithms.

#### B.4 Solution Method

**Solver**: HiGHS via `scipy.optimize.linprog`

HiGHS uses a **hybrid adaptive algorithm** that automatically chooses between:
1. **Simplex method**: Efficient for small-medium problems, guarantees optimal solution
2. **Interior-point method**: Scales better for large problems, faster for some problem types
3. **Crossover**: Converts interior-point solution to simplex basis for robustness

**Performance**:
- Solution time: 0.5-2 seconds per 24-hour optimization
- Memory usage: ~50 MB
- Re-optimization: Every 15-60 minutes
- Horizon: 24 hours (perfect foresight)

**Implementation files**:
- `battery_optimization/core/rolling_horizon_optimizer.py`
- `battery_optimization/configs/rolling_horizon_realtime.yaml`
- `battery_optimization/main.py`

**Design documents**:
- `OPERATIONAL_OPTIMIZATION_STRATEGY.md`
- `PEAK_PENALTY_METHODOLOGY.md`
- `COMMERCIAL_SYSTEMS_COMPARISON.md`

**Standard config**:
- 80 kWh battery @ 60 kW
- 90.25% roundtrip efficiency
- SOC [10%, 90%]
- 5000 cycle life @ 100% DOD
- 28 year calendar life
- 20% EOL degradation
- 70 kW grid limits
- Lnett commercial tariff structure

---

### Appendix C: Output and Key Metrics

#### C.1 Optimal Control Action

**Optimal control action** (next timestep):

$$
\boxed{
P_{\text{battery}}^{\text{setpoint}} = P_{\text{charge},0} - P_{\text{discharge},0} \quad \text{[kW]}
}
$$

**Interpretation**:
- Positive value ($P_{\text{battery}}^{\text{setpoint}} > 0$): Charge the battery
- Negative value ($P_{\text{battery}}^{\text{setpoint}} < 0$): Discharge the battery
- Zero ($P_{\text{battery}}^{\text{setpoint}} = 0$): Idle mode (no activity)

#### C.2 Economic Key Figures (24-hour aggregation)

**Energy cost**:

$$
C_{\text{energy}}^{24h} = \sum_{t=0}^{95} \left[ c_{\text{import},t} P_{\text{grid},t}^{\text{import}} - c_{\text{export},t} P_{\text{grid},t}^{\text{export}} \right] \Delta t
$$

**Degradation cost**:

$$
C_{\text{degradation}}^{24h} = \sum_{t=0}^{95} c_{\text{deg}}^{\text{percent}} DP_{\text{total},t}
$$

**Marginal tariff cost**:

$$
\Delta C_{\text{tariff}}^{\text{progressive}} = \sum_{i=0}^{N_{\text{trinn}}-1} c_{\text{trinn},i} z_i - c_{\text{baseline}}^{\text{tariff}}
$$

#### C.3 Degradation Metrics

**Equivalent full cycles**:

$$
\boxed{
\text{Cycles}_{\text{eq}}^{24h} = \sum_{t=0}^{95} \text{DOD}_{\text{abs},t}
}
$$

**Total degradation**:

$$
DP_{\text{total}}^{24h} = \sum_{t=0}^{95} DP_{\text{total},t} \quad [\%]
$$

**Annual degradation rate (extrapolated)**:

$$
\text{Degradation rate}_{\text{annual}} = DP_{\text{total}}^{24h} \times 365 \quad [\%/\text{year}]
$$

**Estimated lifetime**:

$$
\text{Estimated lifetime} = \frac{\text{EOL}_{\text{deg}}}{\text{Degradation rate}_{\text{annual}}} \quad [\text{years}]
$$

**Example calculation**:
- At $DP_{\text{total}}^{24h} = 0.002\%$ per day (typical with moderate activity)
- Annual degradation: $0.002\% \times 365 = 0.73\%$ per year
- Estimated lifetime: $20\% / 0.73\% = 27.4$ years

---

**Documentation generated:** 2025-01-09
**Source code:** `battery_optimization/core/rolling_horizon_optimizer.py:1-784`
**Author:** Klaus (Battery Optimization System)
