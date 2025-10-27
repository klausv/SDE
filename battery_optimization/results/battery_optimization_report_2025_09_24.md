# Battery Optimization Report - Snødevegen 122
**Date:** September 24, 2025
**System:** 150 kWp Solar PV with Battery Storage Analysis
**Location:** Stavanger, Norway (58.97°N, 5.73°E)

## Executive Summary

Analysis of battery storage economics for a 150 kWp solar installation with updated system parameters shows marginal economic viability at current battery prices. The system requires battery costs to drop to ~2,500 NOK/kWh for positive returns.

## System Configuration (Updated)

### Solar PV System
- **DC Capacity:** 150 kWp (138.55 kWp rated)
- **Tilt Angle:** 15° (updated from 25-30°)
- **Azimuth:** 173° (updated from 180°)
- **Inverter:** 110 kW AC (oversizing ratio 1.36)
- **Grid Connection Limit:** 77 kW

### Location & Climate
- **Site:** Stavanger, Norway
- **Coordinates:** 58.97°N, 5.73°E
- **Annual Irradiation:** ~950 kWh/m²
- **Data Source:** PVGIS TMY data

## Production Analysis

### Annual Energy Production
- **Total DC Production:** 130.8 MWh/year
- **Total AC Production:** 125.9 MWh/year
- **Grid Export (after curtailment):** 120.2 MWh/year

### System Losses
- **Inverter Clipping:** 2.3 MWh (1.8% of DC production)
- **Grid Curtailment:** 5.6 MWh (4.5% of AC production)
- **Total Curtailed Energy:** 7.9 MWh (6.0% of DC production)

### Production Characteristics
- **Peak DC Power:** 137.3 kW
- **Peak AC Power:** 110.0 kW (inverter limited)
- **Capacity Factor:** 10.0%
- **Performance Ratio:** 0.91

## Consumption Profile

### Commercial Load Pattern
- **Annual Consumption:** 210.7 MWh
- **Peak Demand:** 68.5 kW
- **Minimum Load:** 8.3 kW
- **Average Load:** 24.0 kW

### Time-of-Use Characteristics
- **Weekday Business Hours (8-17):** 46.8 kW average
- **Weekend Average:** 13.7 kW
- **Night Hours (0-6):** 10.8 kW average

## Battery Optimization Results

### Optimal Configuration at 2,500 NOK/kWh
- **Battery Capacity:** 10 kWh
- **Battery Power:** 10 kW (C-rate = 1.0)
- **NPV:** 63,806 NOK
- **IRR:** 28.5%
- **Payback Period:** 2.9 years
- **Annual Savings:** 8,556 NOK

### Sensitivity Analysis

#### 50 kWh Battery System
| Battery Cost | NPV | Payback | Viable |
|-------------|-----|---------|---------|
| 2,500 NOK/kWh | -7,758 NOK | 11.1 years | ❌ |
| 3,000 NOK/kWh | -32,758 NOK | 13.3 years | ❌ |
| 5,000 NOK/kWh | -132,758 NOK | 22.1 years | ❌ |

#### Break-even Analysis
- **Maximum Battery Cost for Positive NPV:** ~2,450 NOK/kWh
- **Current Market Price:** 5,000 NOK/kWh
- **Required Price Reduction:** 51%

## Value Drivers

### Revenue Streams (15-year total for 10 kWh @ 2,500 NOK/kWh)
1. **Peak Shaving (Curtailment Avoidance):** 45,230 NOK (35%)
2. **Energy Arbitrage:** 38,450 NOK (30%)
3. **Self-Consumption Optimization:** 32,120 NOK (25%)
4. **Power Tariff Reduction:** 12,540 NOK (10%)

### Key Performance Indicators
- **Battery Utilization:** 365 equivalent full cycles/year
- **Round-trip Efficiency:** 90%
- **Degradation Rate:** 2% per year
- **End-of-Life Capacity:** 70% after 15 years

## Economic Analysis

### Investment Metrics at Current Prices (5,000 NOK/kWh)
- **Initial Investment (50 kWh):** 250,000 NOK
- **Annual O&M:** 2,500 NOK
- **NPV:** -132,758 NOK
- **Project Viability:** ❌ Not Recommended

### Investment Metrics at Target Price (2,500 NOK/kWh)
- **Initial Investment (10 kWh):** 25,000 NOK
- **Annual O&M:** 250 NOK
- **NPV:** 63,806 NOK
- **Project Viability:** ✅ Recommended

## Tariff Structure Impact

### Lnett Commercial Tariff
- **Energy Charge Peak (06-22 weekdays):** 0.296 NOK/kWh
- **Energy Charge Off-peak:** 0.176 NOK/kWh
- **Power Tariff:** Progressive brackets
  - 0-50 kW: 165 NOK/kW/month
  - 50-100 kW: 132 NOK/kW/month
  - 100-200 kW: 99 NOK/kW/month

### Grid Fees & Taxes (2024)
- **Enova Fee:** 0.010 NOK/kWh
- **Electricity Tax:** 0.916 NOK/kWh
- **Total Grid Cost:** ~1.40 NOK/kWh delivered

## Technical Specifications

### Battery Requirements
- **Technology:** Lithium-ion (LFP preferred)
- **Minimum Cycles:** 6,000+ rated cycles
- **Temperature Range:** -20°C to +45°C operation
- **Response Time:** <1 second
- **Communication:** Modbus TCP/IP

### Integration Requirements
- **EMS Integration:** Required for optimization
- **Grid Code Compliance:** NEK 400:2022
- **Safety Standards:** IEC 62619, UN38.3
- **Installation:** Indoor, climate controlled

## Risk Assessment

### Technical Risks
- **Degradation Uncertainty:** ±10% on lifetime estimates
- **Curtailment Variability:** Weather dependent
- **Grid Regulation Changes:** Potential tariff restructuring

### Economic Risks
- **Electricity Price Volatility:** ±30% impact on arbitrage value
- **Battery Price Evolution:** Declining but uncertain rate
- **Subsidy Dependency:** Enova support not guaranteed

## Recommendations

### Immediate Actions
1. **Do Not Invest** at current battery prices (5,000 NOK/kWh)
2. **Monitor** battery price trends quarterly
3. **Prepare** technical specifications for future installation

### Investment Trigger Points
- **Proceed** when battery costs drop below 2,500 NOK/kWh
- **Consider** pilot installation at 3,000 NOK/kWh with subsidies
- **Evaluate** alternative revenue streams (frequency regulation)

### Future Optimization Opportunities
1. **Dynamic Load Management:** Shift flexible loads to peak production
2. **EV Charging Integration:** Coordinate with future EV infrastructure
3. **Virtual Power Plant:** Participate in aggregated grid services
4. **Seasonal Storage:** Evaluate hydrogen for long-term storage

## Conclusion

The battery storage system shows **positive economics only when battery costs reach 2,500 NOK/kWh**. At current market prices of 5,000 NOK/kWh, the investment produces a negative NPV of -132,758 NOK for a 50 kWh system.

The updated system parameters (tilt=15°, azimuth=173°) provide marginally better production (+2%) compared to previous assumptions, improving the business case by approximately 1,800 NOK in NPV terms.

**Key Insight:** Small battery systems (10 kWh) optimized for daily cycling provide better returns than larger systems aimed at energy autonomy. Focus on high-value applications (peak shaving, power tariff reduction) rather than bulk energy storage.

---

*Report Generated: 2025-09-24*
*Analysis Tool: Battery Optimization System v1.0*
*Data Sources: PVGIS 5.2, Lnett Tariff 2024*