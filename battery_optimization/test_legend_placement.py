"""
Test Legend Placement - Norsk Solkraft
======================================

Viser 3 ulike legend-plasseringer:
1. Topp (mellom tittel og graf) - UTENFOR
2. Bunn (under graf) - UTENFOR
3. Høyre side (classic) - INNENFOR
"""

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import sys
sys.path.insert(0, 'src')
from visualization.norsk_solkraft_theme import apply_dark_theme, get_brand_colors

# Apply theme
apply_dark_theme()
colors = get_brand_colors()

# Generate example data
x = np.linspace(0, 24, 100)
y1 = 50 + 30 * np.sin(x * np.pi / 12)
y2 = 40 + 20 * np.sin(x * np.pi / 12 + 1)
y3 = 30 + 25 * np.sin(x * np.pi / 12 + 2)

# ═══════════════════════════════════════════════════════════════════════════
# VARIANT 1: LEGEND PÅ TOPP (mellom tittel og graf)
# ═══════════════════════════════════════════════════════════════════════════

fig1 = go.Figure()

fig1.add_trace(go.Scatter(
    x=x, y=y1,
    name='Solproduksjon',
    line=dict(width=3, color=colors['oransje'])
))

fig1.add_trace(go.Scatter(
    x=x, y=y2,
    name='Nettforbruk',
    line=dict(width=2.5, color=colors['blå'])
))

fig1.add_trace(go.Scatter(
    x=x, y=y3,
    name='Batteri SOC',
    line=dict(width=2.5, color=colors['mose_grønn'])
))

fig1.update_layout(
    title=dict(
        text='Solar Production Analysis',
        y=0.98,              # Tittel helt øverst
        x=0.5,
        xanchor='center',
        yanchor='top'
    ),

    # LEGEND MELLOM TITTEL OG GRAF
    legend=dict(
        orientation="h",     # Horisontal
        yanchor="bottom",    # Anker på bunnen av legend-boksen
        y=1.0,               # Plassering akkurat OVER grafen (y=1 er topp av graf)
        xanchor="center",    # Sentrert
        x=0.5,

        # Styling
        bgcolor='rgba(33,33,33,0.95)',
        bordercolor='#8A8A8A',
        borderwidth=1,
        font=dict(size=11, color='white')
    ),

    xaxis_title='Timer',
    yaxis_title='Effekt (kW)',

    # GI PLASS TIL LEGEND PÅ TOPP
    margin=dict(t=120, b=60, l=60, r=40)  # t=top margin økt!
)

print("\n" + "="*60)
print("VARIANT 1: Legend på TOPP (mellom tittel og graf)")
print("="*60)
fig1.write_html('legend_top.html')
print("✅ Saved: legend_top.html")
fig1.show()


# ═══════════════════════════════════════════════════════════════════════════
# VARIANT 2: LEGEND PÅ BUNN (under graf)
# ═══════════════════════════════════════════════════════════════════════════

fig2 = go.Figure()

fig2.add_trace(go.Scatter(
    x=x, y=y1,
    name='Solproduksjon',
    line=dict(width=3, color=colors['oransje'])
))

fig2.add_trace(go.Scatter(
    x=x, y=y2,
    name='Nettforbruk',
    line=dict(width=2.5, color=colors['blå'])
))

fig2.add_trace(go.Scatter(
    x=x, y=y3,
    name='Batteri SOC',
    line=dict(width=2.5, color=colors['mose_grønn'])
))

fig2.update_layout(
    title='Solar Production Analysis',

    # LEGEND UNDER GRAF
    legend=dict(
        orientation="h",     # Horisontal
        yanchor="top",       # Anker på toppen av legend-boksen
        y=-0.15,             # Plassering UNDER grafen (negativ!)
        xanchor="center",
        x=0.5,

        # Styling
        bgcolor='rgba(33,33,33,0.95)',
        bordercolor='#8A8A8A',
        borderwidth=1,
        font=dict(size=11, color='white')
    ),

    xaxis_title='Timer',
    yaxis_title='Effekt (kW)',

    # GI PLASS TIL LEGEND PÅ BUNN
    margin=dict(t=80, b=100, l=60, r=40)  # b=bottom margin økt!
)

print("\n" + "="*60)
print("VARIANT 2: Legend på BUNN (under graf)")
print("="*60)
fig2.write_html('legend_bottom.html')
print("✅ Saved: legend_bottom.html")
fig2.show()


# ═══════════════════════════════════════════════════════════════════════════
# VARIANT 3: LEGEND PÅ HØYRE SIDE (classic - innenfor graf)
# ═══════════════════════════════════════════════════════════════════════════

fig3 = go.Figure()

fig3.add_trace(go.Scatter(
    x=x, y=y1,
    name='Solproduksjon',
    line=dict(width=3, color=colors['oransje'])
))

fig3.add_trace(go.Scatter(
    x=x, y=y2,
    name='Nettforbruk',
    line=dict(width=2.5, color=colors['blå'])
))

fig3.add_trace(go.Scatter(
    x=x, y=y3,
    name='Batteri SOC',
    line=dict(width=2.5, color=colors['mose_grønn'])
))

fig3.update_layout(
    title='Solar Production Analysis',

    # LEGEND INNE I GRAF (høyre side)
    legend=dict(
        orientation="v",     # Vertikal
        yanchor="top",
        y=0.99,              # Innenfor (0-1)
        xanchor="right",
        x=0.99,

        # Styling
        bgcolor='rgba(33,33,33,0.95)',
        bordercolor='#8A8A8A',
        borderwidth=1,
        font=dict(size=11, color='white')
    ),

    xaxis_title='Timer',
    yaxis_title='Effekt (kW)',

    margin=dict(t=80, b=60, l=60, r=40)
)

print("\n" + "="*60)
print("VARIANT 3: Legend HØYRE SIDE (classic, innenfor graf)")
print("="*60)
fig3.write_html('legend_right.html')
print("✅ Saved: legend_right.html")
fig3.show()


# ═══════════════════════════════════════════════════════════════════════════
# COMPARISON - Alle tre varianter side-by-side
# ═══════════════════════════════════════════════════════════════════════════

print("\n" + "="*60)
print("SAMMENLIGNING - Alle 3 varianter")
print("="*60)

from plotly.subplots import make_subplots

fig_compare = make_subplots(
    rows=1, cols=3,
    subplot_titles=(
        'Legend TOPP (over graf)',
        'Legend BUNN (under graf)',
        'Legend HØYRE (inne i graf)'
    ),
    horizontal_spacing=0.08
)

# Add data to all subplots
for col in range(1, 4):
    fig_compare.add_trace(
        go.Scatter(x=x, y=y1, name='Sol', line=dict(width=2, color=colors['oransje']),
                   showlegend=(col == 1)),
        row=1, col=col
    )
    fig_compare.add_trace(
        go.Scatter(x=x, y=y2, name='Nett', line=dict(width=2, color=colors['blå']),
                   showlegend=(col == 1)),
        row=1, col=col
    )
    fig_compare.add_trace(
        go.Scatter(x=x, y=y3, name='Batteri', line=dict(width=2, color=colors['mose_grønn']),
                   showlegend=(col == 1)),
        row=1, col=col
    )

# Legend på topp (for første subplot)
fig_compare.update_layout(
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.0,
        xanchor="left",
        x=0.0,
        bgcolor='rgba(33,33,33,0.95)',
        bordercolor='#8A8A8A',
        borderwidth=1
    ),
    height=500,
    title_text='Legend Placement Comparison',
    margin=dict(t=140, b=60)
)

fig_compare.write_html('legend_comparison.html')
print("✅ Saved: legend_comparison.html")
fig_compare.show()

print("\n" + "="*60)
print("✅ ALLE DEMOS FULLFØRT!")
print("="*60)
print("\nGenererte filer:")
print("  - legend_top.html       (legend mellom tittel og graf)")
print("  - legend_bottom.html    (legend under graf)")
print("  - legend_right.html     (legend inne i graf)")
print("  - legend_comparison.html (alle tre side-by-side)")
print("\nÅpne i nettleser for å sammenligne!")
print("\n" + "="*60)
print("VIKTIGE PARAMETRE:")
print("="*60)
print("\n1. Legend på TOPP (mellom tittel og graf):")
print("   legend=dict(")
print("       orientation='h',")
print("       yanchor='bottom',")
print("       y=1.0,              # Akkurat OVER grafen")
print("       xanchor='center',")
print("       x=0.5")
print("   )")
print("   margin=dict(t=120)      # Øk top margin!")
print("\n2. Legend på BUNN (under graf):")
print("   legend=dict(")
print("       orientation='h',")
print("       yanchor='top',")
print("       y=-0.15,            # UNDER grafen (negativ!)")
print("       xanchor='center',")
print("       x=0.5")
print("   )")
print("   margin=dict(b=100)      # Øk bottom margin!")
