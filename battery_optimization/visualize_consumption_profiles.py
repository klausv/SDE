"""
Visualize consumption profiles from consumption_profiles.py
"""
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from core.consumption_profiles import ConsumptionProfile

# Set style
plt.style.use('seaborn-v0_8-darkgrid')
fig = plt.figure(figsize=(16, 12))

# 1. HOURLY PATTERNS - WEEKDAY
ax1 = plt.subplot(3, 2, 1)
for profile_type, color, label in [
    ('commercial_office', '#2E86AB', 'Office'),
    ('commercial_retail', '#A23B72', 'Retail'),
    ('industrial', '#F18F01', 'Industrial')
]:
    profile = getattr(ConsumptionProfile, profile_type)()
    hours = np.arange(24)
    ax1.plot(hours, profile['weekday'], marker='o', linewidth=2.5,
             color=color, label=label, alpha=0.8)

ax1.set_xlabel('Hour of Day', fontsize=11, fontweight='bold')
ax1.set_ylabel('Relative Consumption', fontsize=11, fontweight='bold')
ax1.set_title('Weekday Consumption Patterns', fontsize=13, fontweight='bold')
ax1.legend(loc='best', fontsize=10)
ax1.grid(True, alpha=0.3)
ax1.set_xticks(range(0, 24, 2))
ax1.axvspan(12, 13, color='yellow', alpha=0.1, label='Lunch hour')

# 2. HOURLY PATTERNS - WEEKEND
ax2 = plt.subplot(3, 2, 2)
for profile_type, color, label in [
    ('commercial_office', '#2E86AB', 'Office'),
    ('commercial_retail', '#A23B72', 'Retail'),
    ('industrial', '#F18F01', 'Industrial')
]:
    profile = getattr(ConsumptionProfile, profile_type)()
    hours = np.arange(24)
    ax2.plot(hours, profile['weekend'], marker='o', linewidth=2.5,
             color=color, label=label, alpha=0.8)

ax2.set_xlabel('Hour of Day', fontsize=11, fontweight='bold')
ax2.set_ylabel('Relative Consumption', fontsize=11, fontweight='bold')
ax2.set_title('Weekend Consumption Patterns', fontsize=13, fontweight='bold')
ax2.legend(loc='best', fontsize=10)
ax2.grid(True, alpha=0.3)
ax2.set_xticks(range(0, 24, 2))

# 3. WEEKDAY VS WEEKEND COMPARISON (Office)
ax3 = plt.subplot(3, 2, 3)
office = ConsumptionProfile.commercial_office()
hours = np.arange(24)
ax3.plot(hours, office['weekday'], marker='o', linewidth=2.5,
         color='#2E86AB', label='Weekday', alpha=0.8)
ax3.plot(hours, office['weekend'], marker='s', linewidth=2.5,
         color='#C73E1D', label='Weekend', alpha=0.8)
ax3.set_xlabel('Hour of Day', fontsize=11, fontweight='bold')
ax3.set_ylabel('Relative Consumption', fontsize=11, fontweight='bold')
ax3.set_title('Office: Weekday vs Weekend', fontsize=13, fontweight='bold')
ax3.legend(loc='best', fontsize=10)
ax3.grid(True, alpha=0.3)
ax3.set_xticks(range(0, 24, 2))
ax3.fill_between(hours, office['weekday'], office['weekend'], alpha=0.2, color='#2E86AB')

# 4. ANNUAL PROFILE - ONE WEEK IN JANUARY
ax4 = plt.subplot(3, 2, 4)
for profile_type, color, label in [
    ('commercial_office', '#2E86AB', 'Office'),
    ('commercial_retail', '#A23B72', 'Retail'),
    ('industrial', '#F18F01', 'Industrial')
]:
    series = ConsumptionProfile.generate_annual_profile(
        profile_type=profile_type,
        annual_kwh=90000,
        year=2024
    )
    # Show first week of January
    week_data = series['2024-01-01':'2024-01-07']
    ax4.plot(week_data.index, week_data.values, linewidth=2,
             color=color, label=label, alpha=0.8)

ax4.set_xlabel('Date', fontsize=11, fontweight='bold')
ax4.set_ylabel('Power (kW)', fontsize=11, fontweight='bold')
ax4.set_title('Week Profile (Jan 1-7, 2024)', fontsize=13, fontweight='bold')
ax4.legend(loc='best', fontsize=10)
ax4.grid(True, alpha=0.3)
ax4.tick_params(axis='x', rotation=45)

# 5. MONTHLY AVERAGE CONSUMPTION
ax5 = plt.subplot(3, 2, 5)
months = []
office_monthly = []
retail_monthly = []
industrial_monthly = []

for month in range(1, 13):
    months.append(month)
    for profile_type, monthly_list in [
        ('commercial_office', office_monthly),
        ('commercial_retail', retail_monthly),
        ('industrial', industrial_monthly)
    ]:
        series = ConsumptionProfile.generate_annual_profile(
            profile_type=profile_type,
            annual_kwh=90000,
            year=2024
        )
        month_data = series[series.index.month == month]
        monthly_list.append(month_data.mean())

x = np.arange(12)
width = 0.25
ax5.bar(x - width, office_monthly, width, label='Office', color='#2E86AB', alpha=0.8)
ax5.bar(x, retail_monthly, width, label='Retail', color='#A23B72', alpha=0.8)
ax5.bar(x + width, industrial_monthly, width, label='Industrial', color='#F18F01', alpha=0.8)

ax5.set_xlabel('Month', fontsize=11, fontweight='bold')
ax5.set_ylabel('Average Power (kW)', fontsize=11, fontweight='bold')
ax5.set_title('Monthly Average Consumption', fontsize=13, fontweight='bold')
ax5.set_xticks(x)
ax5.set_xticklabels(['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                     'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'])
ax5.legend(loc='best', fontsize=10)
ax5.grid(True, alpha=0.3, axis='y')

# 6. DURATION CURVES (load duration)
ax6 = plt.subplot(3, 2, 6)
for profile_type, color, label in [
    ('commercial_office', '#2E86AB', 'Office'),
    ('commercial_retail', '#A23B72', 'Retail'),
    ('industrial', '#F18F01', 'Industrial')
]:
    series = ConsumptionProfile.generate_annual_profile(
        profile_type=profile_type,
        annual_kwh=90000,
        year=2024
    )
    # Sort values descending for duration curve
    sorted_values = np.sort(series.values)[::-1]
    hours = np.arange(len(sorted_values))
    ax6.plot(hours, sorted_values, linewidth=2, color=color, label=label, alpha=0.8)

ax6.set_xlabel('Hours per Year', fontsize=11, fontweight='bold')
ax6.set_ylabel('Power (kW)', fontsize=11, fontweight='bold')
ax6.set_title('Annual Load Duration Curves', fontsize=13, fontweight='bold')
ax6.legend(loc='best', fontsize=10)
ax6.grid(True, alpha=0.3)

# Add overall title
fig.suptitle('Consumption Profile Analysis - 90 MWh Annual Consumption',
             fontsize=16, fontweight='bold', y=0.995)

plt.tight_layout()

# Save figure
plt.savefig('battery_optimization/results/consumption_profiles_analysis.png',
            dpi=300, bbox_inches='tight')
print("✓ Plot saved to: battery_optimization/results/consumption_profiles_analysis.png")

# Show statistics
print("\n📊 CONSUMPTION PROFILE STATISTICS")
print("=" * 70)

for profile_type in ['commercial_office', 'commercial_retail', 'industrial']:
    series = ConsumptionProfile.generate_annual_profile(
        profile_type=profile_type,
        annual_kwh=90000,
        year=2024
    )

    print(f"\n{profile_type.upper().replace('_', ' ')}:")
    print(f"  Annual consumption: {series.sum()/1000:.1f} MWh")
    print(f"  Peak power:         {series.max():.1f} kW")
    print(f"  Minimum power:      {series.min():.1f} kW")
    print(f"  Average power:      {series.mean():.1f} kW")
    print(f"  Load factor:        {series.mean()/series.max()*100:.1f}%")

    # Weekday vs weekend
    weekday_avg = series[series.index.weekday < 5].mean()
    weekend_avg = series[series.index.weekday >= 5].mean()
    print(f"  Weekday average:    {weekday_avg:.1f} kW")
    print(f"  Weekend average:    {weekend_avg:.1f} kW ({weekend_avg/weekday_avg*100:.0f}%)")

    # Lunch dip check
    lunch_12 = series[series.index.hour == 12].mean()
    lunch_11 = series[series.index.hour == 11].mean()
    if lunch_12 < lunch_11 * 0.85:
        print(f"  Lunch dip:          YES ({lunch_12:.1f} kW vs {lunch_11:.1f} kW at 11:00)")
    else:
        print(f"  Lunch dip:          NO (steady consumption)")

plt.show()
