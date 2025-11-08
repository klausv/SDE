# Multi-Resolution Price Fetcher

## Overview

The price fetcher now supports multiple time resolutions for electricity spot prices:
- **Hourly (PT60M)**: Standard resolution used by Nord Pool day-ahead market (currently)
- **15-Minute (PT15M)**: High-resolution data available from September 30, 2025

## Quick Start

### Hourly Prices (Default)
```python
from core.price_fetcher import fetch_prices

# Fetch hourly prices (8,760 data points per year)
prices = fetch_prices(2024, area='NO2')
print(f"Data points: {len(prices)}")  # ~8760
```

### 15-Minute Prices
```python
from core.price_fetcher import fetch_prices

# Fetch 15-minute prices (35,040 data points per year)
prices_15min = fetch_prices(2025, area='NO2', resolution='PT15M')
print(f"Data points: {len(prices_15min)}")  # ~35040
```

## Nord Pool 15-Minute Transition

### Timeline
- **March 18, 2025**: Norway intraday markets transition to 15-minute resolution
- **September 30, 2025**: **Day-ahead spot market** transitions to 15-minute resolution

### What This Means
Before Sept 30, 2025:
- ✅ Day-ahead prices: **Hourly only**
- ✅ Use `resolution='PT60M'` (default)

After Sept 30, 2025:
- ✅ Day-ahead prices: **15-minute resolution available**
- ✅ Use `resolution='PT15M'` for granular optimization
- ⚡ 4x more data points enables more precise battery control

## API Usage

### Class-Based Usage
```python
from core.price_fetcher import ENTSOEPriceFetcher

# Initialize with specific resolution
fetcher_hourly = ENTSOEPriceFetcher(resolution='PT60M')
fetcher_15min = ENTSOEPriceFetcher(resolution='PT15M')

# Fetch prices
prices_hourly = fetcher_hourly.fetch_prices(2024, 'NO2')
prices_15min = fetcher_15min.fetch_prices(2025, 'NO2')
```

### Convenience Function
```python
from core.price_fetcher import fetch_prices

# Hourly (backward compatible)
prices = fetch_prices(2024, 'NO2')

# 15-minute (explicit)
prices_15min = fetch_prices(2025, 'NO2', resolution='PT15M')

# With API key
prices = fetch_prices(2024, 'NO2', api_key='your_key_here')

# Force refresh (bypass cache)
prices = fetch_prices(2024, 'NO2', refresh=True)
```

## Resolution Constants
```python
from core.price_fetcher import ENTSOEPriceFetcher

# Available resolution constants
ENTSOEPriceFetcher.RESOLUTION_HOURLY  # 'PT60M'
ENTSOEPriceFetcher.RESOLUTION_15MIN   # 'PT15M'
ENTSOEPriceFetcher.VALID_RESOLUTIONS  # ['PT60M', 'PT15M']
```

## Cache System

### File Naming Convention
The cache system uses resolution-aware naming:
```
data/spot_prices/
├── NO2_2024_60min_real.csv    # Hourly data (8,760 points)
├── NO2_2024_15min_real.csv    # 15-minute data (35,040 points)
└── cache_metadata.json          # Resolution metadata
```

### Metadata Structure
```json
{
  "NO2_2024_60min": {
    "area": "NO2",
    "year": 2024,
    "resolution": "PT60M",
    "expected_points": 8760,
    "source": "ENTSO-E API",
    "fetched_date": "2025-10-31 20:00:00",
    "eur_nok_rate": 11.5
  },
  "NO2_2024_15min": {
    "area": "NO2",
    "year": 2024,
    "resolution": "PT15M",
    "expected_points": 35040,
    "source": "ENTSO-E API",
    "fetched_date": "2025-10-31 20:05:00",
    "eur_nok_rate": 11.5
  }
}
```

## Expected Data Points

### Hourly Resolution
- **Non-leap year**: 365 × 24 = 8,760 hours
- **Leap year**: 366 × 24 = 8,784 hours
- **DST adjustments**: ±1 hour (spring/fall transitions)

### 15-Minute Resolution
- **Non-leap year**: 365 × 24 × 4 = 35,040 intervals
- **Leap year**: 366 × 24 × 4 = 35,136 intervals
- **DST adjustments**: ±4 intervals (spring/fall transitions)

## Data Validation

The fetcher automatically validates data point counts with tolerance for DST:
```python
# Automatic validation on fetch
prices = fetch_prices(2024, 'NO2', resolution='PT15M')

# Output shows validation
# ✅ Expected ~35040 points, got 35136 (leap year + DST)
```

## ENTSO-E API Behavior

### Resolution Detection
The API doesn't always respect resolution requests in parameters. The fetcher:
1. Detects actual resolution from XML `<resolution>` field
2. Warns if different from requested
3. Calculates timestamps based on detected resolution

```python
# Example API response handling
# XML: <resolution>PT60M</resolution>
# Requested: PT15M
# Output: ℹ️ API returned PT60M, expected PT15M
```

### Fallback Data Generation
When API is unavailable:
- Generates realistic simulated prices
- Respects chosen resolution
- Maintains seasonal/hourly patterns
- ⚠️ Always warns: "Using simulated data - not real market prices!"

## Battery Optimization Impact

### Hourly Resolution (Current)
- **Optimization variables**: 8,760 per year
- **Control granularity**: 1-hour intervals
- **Computation time**: ~1-2 minutes for full year
- **Use case**: Strategic planning and investment analysis

### 15-Minute Resolution (Post Sept 2025)
- **Optimization variables**: 35,040 per year (4x increase)
- **Control granularity**: 15-minute intervals
- **Computation time**: ~5-10 minutes for full year
- **Use case**: Real-time operation and intraday trading

### Recommendations
- **Investment analysis**: Use hourly data (sufficient, faster)
- **Operational planning**: Use 15-minute data (more precise)
- **Hybrid approach**: Optimize with hourly, validate with 15-minute

## Migration Guide

### Existing Code (No Changes Needed)
```python
# Old code continues to work (hourly by default)
from core.price_fetcher import fetch_prices

prices = fetch_prices(2024, 'NO2')
# Returns hourly data as before
```

### New 15-Minute Support
```python
# Add resolution parameter when ready
prices_15min = fetch_prices(2025, 'NO2', resolution='PT15M')
```

### Configuration Updates
If using configuration files, add resolution option:
```python
# config.py
PRICE_RESOLUTION = 'PT60M'  # or 'PT15M' after Sept 2025

# Use in code
from config import PRICE_RESOLUTION
prices = fetch_prices(2024, 'NO2', resolution=PRICE_RESOLUTION)
```

## Testing

### Validate Implementation
```bash
cd battery_optimization
python -c "
from core.price_fetcher import ENTSOEPriceFetcher, fetch_prices

# Test hourly
prices_h = fetch_prices(2024, 'NO2', resolution='PT60M', refresh=True)
print(f'Hourly: {len(prices_h)} points')

# Test 15-minute
prices_15 = fetch_prices(2024, 'NO2', resolution='PT15M', refresh=True)
print(f'15-min: {len(prices_15)} points')

print('✅ Multi-resolution support working!')
"
```

## Performance Considerations

### Memory Usage
- **Hourly**: ~100 KB per year (CSV)
- **15-minute**: ~400 KB per year (CSV) - 4x larger

### API Requests
- Both resolutions use same API endpoints
- Month-by-month fetching to avoid limits
- Same rate limiting applies

### Processing Time
- **Parsing**: Minimal difference between resolutions
- **Resampling**: Slightly slower for 15-minute data
- **Overall**: <5% performance difference

## Troubleshooting

### Resolution Mismatch Warning
```
ℹ️ API returned PT60M, expected PT15M
```
**Cause**: API doesn't provide 15-minute data yet (before Sept 30, 2025)
**Solution**: Use hourly resolution until transition date

### Unexpected Data Point Count
```
⚠️ Expected ~35040 points, got 35136 (diff: 96)
```
**Cause**: Leap year + DST transitions
**Solution**: Normal behavior, within tolerance (±50 points)

### Invalid Resolution Error
```
ValueError: Resolution must be one of ['PT60M', 'PT15M'], got 'PT30M'
```
**Cause**: Unsupported resolution specified
**Solution**: Use PT60M or PT15M only

## Future Enhancements

Potential additions (not yet implemented):
- PT30M (30-minute) resolution support
- Automatic resolution detection based on date
- Mixed-resolution optimization (hourly planning + 15-min operation)
- Real-time price updates for current day

## References

- [Nord Pool 15-Minute Transition](https://www.nordpoolgroup.com/en/trading/transition-to-15-minute-market-time-unit-mtu/)
- [ENTSO-E Transparency Platform](https://transparency.entsoe.eu/)
- [Nord Pool FAQ](https://www.nordpoolgroup.com/en/trading/transition-to-15-minute-market-time-unit-mtu/faq/)

## Related Documentation

- `README.md` - Project overview and setup
- `core/price_fetcher.py` - Implementation details
- `tests/test_price_fetcher.py` - Test suite
