# Impact of Battery Power Rating on Resolution Benefit

## Comparison: 30 kWh / 15 kW vs 30 kWh / 30 kW

Period: September 30 - October 31, 2025

### Configuration A: 30 kWh / 15 kW (C-rate = 0.5)

**October 2025 Results:**
- Hourly (PT60M): 4,407 kr
- 15-minute (PT15M): 4,342 kr
- **Savings: 66 kr (1.5%)**

**Battery Utilization:**
- Hourly: 38.4 cycles/month
- 15-minute: 42.4 cycles/month
- **+10% more cycles**

**Annual Projection:**
- **~718 kr/year savings (+1.3%)**

---

### Configuration B: 30 kWh / 30 kW (C-rate = 1.0)

**October 2025 Results:**
- Hourly (PT60M): 4,377 kr
- 15-minute (PT15M): 4,308 kr
- **Savings: 69 kr (1.6%)**

**Battery Utilization:**
- Hourly: 45.1 cycles/month
- 15-minute: 47.7 cycles/month
- **+5.8% more cycles**

**Annual Projection:**
- **~848 kr/year savings (+1.5%)**

---

## Key Findings

### 1. Marginal Improvement from Higher Power Rating

Despite **doubling the power rating** (15 kW → 30 kW), the 15-minute resolution benefit increased only modestly:
- **Absolute gain: +130 kr/year** (848 vs 718)
- **Relative improvement: +18%** in savings from resolution

### 2. Diminishing Returns Hypothesis

**Why doesn't 2x power = 2x benefit?**

The battery is constrained by multiple factors:
1. **Energy capacity (30 kWh)**: Limits total arbitrage volume regardless of power
2. **Physical efficiency (90%)**: Round-trip losses eat into arbitrage margins
3. **Price correlation**: Adjacent 15-min intervals are highly correlated (~85-90%)
4. **Grid limits**: Cannot always discharge at full power during peak PV production
5. **Power tariff penalty**: More aggressive cycling increases monthly peak demand

### 3. Price Volatility vs Battery Capability

**Intra-hour price statistics (from analysis):**
- Mean absolute deviation: **0.092 kr/kWh**
- Mean intra-hour range: **0.274 kr/kWh**
- Hours with >10% swing: **95.4%**
- Mean swing magnitude: **35.5%**

**But battery can only capture:**
- 15 kW battery: 1.5% economic gain
- 30 kW battery: 1.6% economic gain

**Bottleneck:** Energy capacity (30 kWh) becomes the limiting factor. The battery fills up quickly during cheap periods and empties during expensive periods, then must wait for the next cycle opportunity.

### 4. Battery Cycling Increase

| Config | Hourly Cycles | 15-min Cycles | Increase |
|--------|---------------|---------------|----------|
| 15 kW  | 38.4/month   | 42.4/month   | +10.4%  |
| 30 kW  | 45.1/month   | 47.7/month   | +5.8%   |

Higher power rating enables more baseline cycles, but **15-min resolution adds progressively less** as power increases.

### 5. Energy Cost vs Power Cost Trade-off

**30 kW Battery (October 2025):**
- Energy savings (arbitrage): -78 kr (-2.0%)
- Power cost increase (tariff): +9 kr (+1.7%)
- **Net benefit: 69 kr**

The more aggressive cycling enabled by 15-minute resolution slightly increases the monthly peak demand, partially offsetting arbitrage gains.

---

## Conclusion

**For this 30 kWh battery:**
- 15-minute resolution provides **consistent ~1.5% savings** regardless of power rating
- Doubling power (15 kW → 30 kW) adds only **~18% more savings** from resolution benefit
- **Energy capacity**, not power rating, is the primary constraint

**Recommendation:**
- For **30 kWh batteries**, hourly resolution is sufficient for planning (difference <2%)
- 15-minute resolution becomes more valuable for:
  - **Larger energy capacity** (e.g., 100+ kWh)
  - **Intraday trading strategies** with real-time price updates
  - **Peak shaving** applications with high power tariffs

**The intra-hour price volatility is substantial (35% average swings), but a 30 kWh battery simply cannot exploit enough of these opportunities to achieve large economic gains, regardless of its power rating.**
