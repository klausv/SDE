# Lnett Tariff Maintenance Guide

**Status**: Manual hardcoded values (no automatic fetching)
**Source**: Lnett commercial tariff documentation
**Last verified**: Unknown (needs manual verification)

---

## Current Implementation

Tariffs are **hardcoded** in `config.py` (lines 60-91):

### Power Tariff Brackets (Effekttariff)
```python
power_brackets: List[Tuple[float, float, float]] = [
    (0, 2, 136),           # 136 kr/måned for 0-2 kW
    (2, 5, 232),           # 232 kr/måned for 2-5 kW
    (5, 10, 372),          # 372 kr/måned for 5-10 kW
    (10, 15, 572),         # 572 kr/måned for 10-15 kW
    (15, 20, 772),         # 772 kr/måned for 15-20 kW
    (20, 25, 972),         # 972 kr/måned for 20-25 kW
    (25, 50, 1772),        # 1772 kr/måned for 25-50 kW
    (50, 75, 2572),        # 2572 kr/måned for 50-75 kW
    (75, 100, 3372),       # 3372 kr/måned for 75-100 kW
    (100, float('inf'), 5600)  # 5600 kr/måned for >100 kW
]
```

### Energy Charges (Energiledd)
```python
energy_peak: float = 0.296      # Mon-Fri 06:00-22:00
energy_offpeak: float = 0.176   # Nights/weekends
energy_tariff: float = 0.054    # Grid energy component
```

### Consumption Tax (Forbruksavgift el)
```python
consumption_tax_monthly: Dict[int, float] = {
    1: 0.0979, 2: 0.0979, 3: 0.0979,    # Jan-Mar (winter low)
    4: 0.1693, 5: 0.1693, 6: 0.1693,    # Apr-Jun (spring high)
    7: 0.1693, 8: 0.1693, 9: 0.1693,    # Jul-Sep (summer high)
    10: 0.1253, 11: 0.1253, 12: 0.1253  # Oct-Dec (autumn medium)
}
```

---

## ⚠️ Important Notes

### Discrepancy Found
There are **two different sets** of consumption_tax values in the codebase:

1. **`config.py` (ACTIVE)**:
   - Jan-Mar: 0.0979 kr/kWh
   - Apr-Sep: 0.1693 kr/kWh
   - Oct-Dec: 0.1253 kr/kWh

2. **`archive/empty_lib/energy_toolkit/tariffs.py`** (archived):
   - Jan-Mar: 0.1541 kr/kWh
   - Apr-Sep: 0.0891 kr/kWh
   - Oct-Dec: 0.1541 kr/kWh (winter) / 0.0891 kr/kWh (autumn)

**Action needed**: Verify which values are correct for 2024/2025 rates from Lnett

---

## How to Update Tariffs

### Manual Update Process

1. **Check Lnett's website** for latest commercial tariff rates:
   - Go to: https://www.lnett.no/nettleie/bedrift/
   - Look for "Nettleiepriser næring" or similar

2. **Update `config.py`**:
   - Lines 64-66: Energy charges (peak/offpeak/tariff)
   - Lines 70-81: Power brackets (effekttariff)
   - Lines 84-89: Consumption tax (forbruksavgift)

3. **Update `config.yaml`** (if used):
   - Currently not storing tariff data in YAML
   - Consider adding if manual updates become frequent

4. **Verify with tests**:
   ```bash
   python -m pytest tests/test_price_data_fetching.py -v
   python -m pytest tests/test_solar_production.py -v
   ```

5. **Document the change**:
   - Update "Last verified" date in this file
   - Note source and effective date of new rates
   - Commit with clear message: `chore: Update Lnett tariffs for [year]`

---

## Future Automation

### Potential Approaches

**Option 1: Manual Script (Recommended for now)**
```python
# scripts/verify_lnett_tariffs.py
# - Prompts user to visit Lnett website
# - Asks user to input current rates
# - Compares with config.py values
# - Shows differences and suggests updates
```

**Option 2: Web Scraping (Future enhancement)**
```python
# scripts/fetch_lnett_tariffs.py
# - Scrape https://www.lnett.no/nettleie/bedrift/
# - Parse tariff tables (requires HTML structure analysis)
# - Update config.py automatically
# - Send alert if rates changed
```

**Option 3: API Integration (Ideal but unlikely)**
- Requires Lnett to provide tariff API
- Currently no known API available
- Monitor for future availability

---

## Comparison with Other Data Sources

| Data Type | Source | Automation |
|-----------|--------|------------|
| **Electricity Prices** | ENTSO-E API | ✅ Automatic (`price_fetcher.py`) |
| **Solar Production** | PVGIS API | ✅ Automatic (`pvgis_solar.py`) |
| **Grid Tariffs** | Lnett (manual) | ❌ Hardcoded (`config.py`) |
| **Consumption Tax** | Skatteetaten (manual) | ❌ Hardcoded (`config.py`) |

---

## Verification Schedule

**Recommended frequency**: Check every 6-12 months or when notified of rate changes

**Key dates to check**:
- January (new year rates often take effect)
- July (mid-year adjustments common)
- When receiving Lnett rate change notifications

**Verification checklist**:
- [ ] Power tariff brackets (effekttariff)
- [ ] Energy charges (energiledd peak/offpeak)
- [ ] Consumption tax rates (forbruksavgift)
- [ ] Enova fee (fixed annual fee)
- [ ] Grid energy component (nettleie energiledd)

---

## Contact Information

**Lnett Customer Service**:
- Website: https://www.lnett.no
- Email: kundesenter@lnett.no
- Phone: 51 90 91 00

**For technical questions about this implementation**:
- Check: `config.py` (TariffConfig class)
- Archive: `archive/empty_lib/energy_toolkit/tariffs.py` (alternative OOP implementation)

---

**Last Updated**: 2025-10-27
**Last Verified Against Lnett**: Unknown (needs verification)
**Next Review**: 2025-04 (suggested)
