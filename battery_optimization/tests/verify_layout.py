"""
Verify that text annotations don't overlap in the visualization
"""

print("=" * 70)
print("LAYOUT VERIFICATION - Checking for text overlaps")
print("=" * 70)

# Panel 1: Top annotations (y-coordinates in EUR/MWh, x in years)
print("\nPANEL 1 - Historisk Prisutvikling:")
print("Top annotations:")
annotations_top = [
    ("COVID-19", 2020, 120),
    ("NordLink", 2021, 180),
    ("North Sea Link", 2021.7, 240),
    ("Energikrise", 2022, 265),
]

for i, (name1, x1, y1) in enumerate(annotations_top):
    for name2, x2, y2 in annotations_top[i+1:]:
        x_dist = abs(x2 - x1)
        y_dist = abs(y2 - y1)
        # Text boxes are roughly 60 units tall and 0.5 years wide
        overlap = ""
        if x_dist < 0.6 and y_dist < 70:
            overlap = " ⚠️ POTENTIAL OVERLAP"
        print(f"  {name1} vs {name2}: Δx={x_dist:.1f}yr, Δy={y_dist}EUR" + overlap)

print("\nBottom annotations:")
annotations_bottom = [
    ("Single Price", 2021.8, 20),
]
print(f"  Single Price at y=20 (bottom) - should not overlap with top annotations")

print("\nPeriod labels:")
period_labels = [
    ("STABIL", 2016.5, 285),
    ("OVERGANG", 2020.5, 270),
    ("NYTT NORMALT", 2023, 285),
]
for i, (name1, x1, y1) in enumerate(period_labels):
    for name2, x2, y2 in enumerate(period_labels[i+1:]):
        x_dist = abs(x2 - x1)
        y_dist = abs(y2 - y1)
        overlap = ""
        if x_dist < 2.5 and y_dist < 25:
            overlap = " ⚠️ POTENTIAL OVERLAP"
        print(f"  {name1} vs {name2}: Δx={x_dist:.1f}yr, Δy={y_dist}EUR" + overlap)

# Panel 2: Volatility annotations
print("\n" + "=" * 70)
print("PANEL 2 - Volatilitetsutvikling:")
vol_annotations = [
    ("STRUKTURELT SKIFTE", 2017.5, 75),
    ("Nordic Balancing", 2019, 45),
    ("Permanent høyt", 2022, 92),
]
for i, (name1, x1, y1) in enumerate(vol_annotations):
    for name2, x2, y2 in vol_annotations[i+1:]:
        x_dist = abs(x2 - x1)
        y_dist = abs(y2 - y1)
        overlap = ""
        # Text boxes roughly 2 years wide, 20% tall
        if x_dist < 3.0 and y_dist < 25:
            overlap = " ⚠️ POTENTIAL OVERLAP"
        print(f"  {name1} vs {name2}: Δx={x_dist:.1f}yr, Δy={y_dist}%" + overlap)

# Panel 3: Negative prices
print("\n" + "=" * 70)
print("PANEL 3 - Negative Priser:")
neg_annotations = [
    ("Første negative", 2017, 100),  # xytext position
    ("381 timer", 2021, 320),
]
for i, (name1, x1, y1) in enumerate(neg_annotations):
    for name2, x2, y2 in neg_annotations[i+1:]:
        x_dist = abs(x2 - x1)
        y_dist = abs(y2 - y1)
        overlap = ""
        if x_dist < 3.0 and y_dist < 150:
            overlap = " ⚠️ POTENTIAL OVERLAP"
        print(f"  {name1} vs {name2}: Δx={x_dist:.1f}yr, Δy={y_dist} timer" + overlap)

# Panel 4: Price extremes
print("\n" + "=" * 70)
print("PANEL 4 - Prisekstremer:")
price_annotations = [
    ("Max 800", 2020, 700),
    ("Min -62", 2021, -150),
]
for i, (name1, x1, y1) in enumerate(price_annotations):
    for name2, x2, y2 in price_annotations[i+1:]:
        x_dist = abs(x2 - x1)
        y_dist = abs(y2 - y1)
        overlap = ""
        if x_dist < 3.0 and y_dist < 200:
            overlap = " ⚠️ POTENTIAL OVERLAP"
        print(f"  {name1} vs {name2}: Δx={x_dist:.1f}yr, Δy={y_dist}EUR" + overlap)

# Panel 5: Three factors
print("\n" + "=" * 70)
print("PANEL 5 - Tre Hovedårsaker (most critical!):")
factors = [
    ("Factor 1: MARKEDSREFORMER", 0.87, "top"),
    ("Factor 2: UTENLANDSKABLER", 0.55, "top"),
    ("Factor 3: IMPORTERT VOLATILITET", 0.27, "top"),
]

print("Vertical positions (as % of panel height):")
for name, y_pos, va in factors:
    print(f"  {name}: y={y_pos:.2f} ({va} anchor)")

print("\nSpacing analysis:")
for i, (name1, y1, va1) in enumerate(factors):
    for name2, y2, va2 in factors[i+1:]:
        spacing = abs(y2 - y1)
        # Each text box is roughly 0.25-0.30 tall
        overlap = ""
        if spacing < 0.25:
            overlap = " ⚠️ POTENTIAL OVERLAP"
        elif spacing < 0.28:
            overlap = " ⚡ TIGHT (but OK)"
        else:
            overlap = " ✓ GOOD SPACING"
        print(f"  {name1} -> {name2}: Δy={spacing:.2f}" + overlap)

print("\n" + "=" * 70)
print("VERIFICATION COMPLETE")
print("=" * 70)
print("\nIf no ⚠️ warnings above, the layout should be good!")
print("⚡ warnings indicate tight spacing but should still be readable")
print("✓ indicates good spacing with no overlap concerns")
