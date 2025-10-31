# Break-Even Battery Cost Analysis

**Generated:** 2025-10-30 09:23:25

## Executive Summary

- **Annual Savings:** 40,000 NOK
- **Break-even Cost:** 15,443 NOK/kWh
- **Market Price:** 5,000 NOK/kWh
- **Required Price Reduction:** -208.9%
- **NPV at Market Prices:** 208,869 NOK (Viable)

## Assumptions

| Parameter | Value |
|-----------|-------|
| Battery capacity | 20 kWh |
| Battery power | 10 kW |
| Battery lifetime | 10 years |
| Discount rate | 5.0% |
| Reference scenario | reference |
| Battery scenario | simplerule_20kwh |

## 1. Annual Savings

| Cost Component | Value |
|----------------|-------|
| Reference case cost | 425,000 NOK/year |
| Battery strategy cost | 385,000 NOK/year |
| **Annual savings** | **40,000 NOK/year** |

## 2. Present Value Calculations

| Metric | Value |
|--------|-------|
| Annuity factor (PV of 1 NOK/year) | 7.7217 |
| PV of total savings | 308,869 NOK |

## 3. Break-Even Battery Cost

| Metric | Value |
|--------|-------|
| **Break-even cost (total)** | **308,869 NOK** |
| **Break-even cost (per kWh)** | **15,443 NOK/kWh** |
| **Break-even cost (per kW)** | **30,887 NOK/kW** |

## 4. Market Comparison

| Metric | Value |
|--------|-------|
| Current market price | 5,000 NOK/kWh |
| Current market cost (total) | 100,000 NOK |
| Required price reduction | -10,443 NOK/kWh (-208.9%) |
| NPV at market prices | 208,869 NOK |
| **Investment viability** | **✓ Viable (NPV > 0)** |

## 5. Sensitivity Analysis

### Break-even Cost vs Lifetime

| Lifetime (years) | Annuity Factor | Break-even (NOK/kWh) |
|------------------|----------------|---------------------|
| 5 | 4.3295 | 8,659 |
| 10 | 7.7217 | 15,443 |
| 15 | 10.3797 | 20,759 |
| 20 | 12.4622 | 24,924 |

### Break-even Cost vs Discount Rate

| Discount Rate (%) | Annuity Factor | Break-even (NOK/kWh) |
|-------------------|----------------|---------------------|
| 3.0 | 8.5302 | 17,060 |
| 5.0 | 7.7217 | 15,443 |
| 7.0 | 7.0236 | 14,047 |
| 10.0 | 6.1446 | 12,289 |

## Visualizations

### NPV Sensitivity to Battery Cost

![NPV Sensitivity](../figures/breakeven/npv_sensitivity.png)

### Break-even Cost vs Battery Lifetime

![Lifetime Sensitivity](../figures/breakeven/breakeven_vs_lifetime.png)

### Break-even Cost vs Discount Rate

![Discount Rate Sensitivity](../figures/breakeven/breakeven_vs_discount_rate.png)

## Summary and Recommendations

With the current battery strategy saving **40,000 NOK/year**, the maximum viable battery cost is **15,443 NOK/kWh**.

✓ **Investment is viable** at current market prices with positive NPV!

### Optimization Opportunities:

1. Implement advanced control strategies to increase annual savings
2. Negotiate better battery prices to improve NPV
3. Explore extended lifetime through proper O&M

