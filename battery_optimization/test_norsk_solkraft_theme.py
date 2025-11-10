"""
Demo: Norsk Solkraft Plotly Themes
===================================

Test og demonstrer begge Norsk Solkraft themes (light + dark).
Genererer eksempel-grafer for å vise fargepalett og styling.
"""

import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots
import numpy as np

# Import Norsk Solkraft themes
import sys
sys.path.insert(0, 'src')
from visualization.norsk_solkraft_theme import (
    register_norsk_solkraft_themes,
    apply_light_theme,
    apply_dark_theme,
    get_brand_colors,
    get_gray_scale
)


def create_demo_data():
    """Generate example data for battery optimization visualization."""
    hours = np.arange(0, 168, 1)  # 1 uke

    data = {
        'hours': hours,
        'solar_production': 50 * np.sin(hours * np.pi / 12) * (np.sin(hours * np.pi / 84) + 1.2),
        'grid_consumption': 30 + 20 * np.sin(hours * np.pi / 12 + 1) + np.random.normal(0, 5, len(hours)),
        'battery_soc': 50 + 30 * np.sin(hours * np.pi / 24),
        'electricity_price': 0.5 + 0.3 * np.sin(hours * np.pi / 12 + 2),
        'peak_demand': 40 + 15 * np.sin(hours * np.pi / 24 + 0.5),
        'forecast': 35 + 25 * np.sin(hours * np.pi / 12 + 0.3),
    }

    # Clip negative values
    for key in ['solar_production', 'grid_consumption', 'battery_soc']:
        data[key] = np.clip(data[key], 0, None)

    return data


def demo_light_theme():
    """Demo: Norsk Solkraft LIGHT theme."""
    print("\n" + "=" * 60)
    print("DEMO: NORSK SOLKRAFT LIGHT THEME (Hvit Bakgrunn)")
    print("=" * 60)

    # Aktiver light theme
    apply_light_theme()

    # Hent data
    data = create_demo_data()
    colors = get_brand_colors()

    # Create figure
    fig = go.Figure()

    # Serie 1: Solar production (Oransje - HOVEDDATA)
    fig.add_trace(go.Scatter(
        x=data['hours'],
        y=data['solar_production'],
        name='Solproduksjon (kW)',
        line=dict(width=3.5, color=colors['oransje']),
        mode='lines'
    ))

    # Serie 2: Grid consumption (Blå - Sammenligning)
    fig.add_trace(go.Scatter(
        x=data['hours'],
        y=data['grid_consumption'],
        name='Nettforbruk (kW)',
        line=dict(width=2.5, color=colors['blå']),
        mode='lines'
    ))

    # Serie 3: Battery SOC (Mose-grønn - Positive)
    fig.add_trace(go.Scatter(
        x=data['hours'],
        y=data['battery_soc'],
        name='Batteri SOC (%)',
        line=dict(width=2.5, color=colors['mose_grønn']),
        mode='lines',
        yaxis='y2'
    ))

    # Serie 4: Forecast (Gul - Prognose)
    fig.add_trace(go.Scatter(
        x=data['hours'],
        y=data['forecast'],
        name='Prognose (kW)',
        line=dict(width=2.0, color=colors['gul'], dash='dash'),
        mode='lines'
    ))

    # Layout
    fig.update_layout(
        title='Battery Optimization - Norsk Solkraft Light Theme',
        xaxis=dict(title='Timer (uke)'),
        yaxis=dict(title='Effekt (kW)', side='left'),
        yaxis2=dict(
            title='SOC (%)',
            overlaying='y',
            side='right',
            range=[0, 100]
        ),
        hovermode='x unified',
        height=600
    )

    # Save
    fig.write_html('demo_norsk_solkraft_light.html')
    print("✅ Saved: demo_norsk_solkraft_light.html")

    # Show
    fig.show()


def demo_dark_theme():
    """Demo: Norsk Solkraft DARK theme."""
    print("\n" + "=" * 60)
    print("DEMO: NORSK SOLKRAFT DARK THEME (Svart Bakgrunn)")
    print("=" * 60)

    # Aktiver dark theme
    apply_dark_theme()

    # Hent data
    data = create_demo_data()
    colors = get_brand_colors()

    # Create figure
    fig = go.Figure()

    # Serie 1: Solar production (Oransje - BRILJERER på svart)
    fig.add_trace(go.Scatter(
        x=data['hours'],
        y=data['solar_production'],
        name='Solproduksjon (kW)',
        line=dict(width=3.5, color=colors['oransje']),
        mode='lines'
    ))

    # Serie 2: Grid consumption (Blå - STERKT på svart)
    fig.add_trace(go.Scatter(
        x=data['hours'],
        y=data['grid_consumption'],
        name='Nettforbruk (kW)',
        line=dict(width=2.5, color=colors['blå']),
        mode='lines'
    ))

    # Serie 3: Battery SOC (Mose-grønn - PERFEKT på svart)
    fig.add_trace(go.Scatter(
        x=data['hours'],
        y=data['battery_soc'],
        name='Batteri SOC (%)',
        line=dict(width=2.5, color=colors['mose_grønn']),
        mode='lines',
        yaxis='y2'
    ))

    # Serie 4: Forecast (Gul - KRAFTIG på svart)
    fig.add_trace(go.Scatter(
        x=data['hours'],
        y=data['forecast'],
        name='Prognose (kW)',
        line=dict(width=2.0, color=colors['gul'], dash='dash'),
        mode='lines'
    ))

    # Layout
    fig.update_layout(
        title='Battery Optimization - Norsk Solkraft Dark Theme',
        xaxis=dict(title='Timer (uke)'),
        yaxis=dict(title='Effekt (kW)', side='left'),
        yaxis2=dict(
            title='SOC (%)',
            overlaying='y',
            side='right',
            range=[0, 100]
        ),
        hovermode='x unified',
        height=600
    )

    # Save
    fig.write_html('demo_norsk_solkraft_dark.html')
    print("✅ Saved: demo_norsk_solkraft_dark.html")

    # Show
    fig.show()


def demo_comparison_subplots():
    """Demo: Side-by-side comparison of light vs dark themes."""
    print("\n" + "=" * 60)
    print("DEMO: LIGHT vs DARK COMPARISON")
    print("=" * 60)

    # Register themes
    register_norsk_solkraft_themes()

    # Get data
    data = create_demo_data()
    colors = get_brand_colors()

    # Create subplots
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=('Light Theme (Hvit)', 'Dark Theme (Svart)'),
        horizontal_spacing=0.12
    )

    # LEFT: Light theme traces
    fig.add_trace(
        go.Scatter(
            x=data['hours'],
            y=data['solar_production'],
            name='Sol (Light)',
            line=dict(width=3, color=colors['oransje']),
            showlegend=True
        ),
        row=1, col=1
    )
    fig.add_trace(
        go.Scatter(
            x=data['hours'],
            y=data['grid_consumption'],
            name='Nett (Light)',
            line=dict(width=2, color=colors['blå']),
            showlegend=True
        ),
        row=1, col=1
    )

    # RIGHT: Dark theme traces (same data, different styling)
    fig.add_trace(
        go.Scatter(
            x=data['hours'],
            y=data['solar_production'],
            name='Sol (Dark)',
            line=dict(width=3, color=colors['oransje']),
            showlegend=True
        ),
        row=1, col=2
    )
    fig.add_trace(
        go.Scatter(
            x=data['hours'],
            y=data['grid_consumption'],
            name='Nett (Dark)',
            line=dict(width=2, color=colors['blå']),
            showlegend=True
        ),
        row=1, col=2
    )

    # Apply light theme to left subplot
    fig.update_xaxes(
        showgrid=True,
        gridcolor='#BDBDBD',
        title_text='Timer',
        row=1, col=1
    )
    fig.update_yaxes(
        showgrid=True,
        gridcolor='#BDBDBD',
        title_text='kW',
        row=1, col=1
    )

    # Apply dark theme styling to right subplot
    fig.update_xaxes(
        showgrid=True,
        gridcolor='#44546A',
        title_text='Timer',
        title_font_color='#FFFFFF',
        tickfont_color='#E0E0E0',
        row=1, col=2
    )
    fig.update_yaxes(
        showgrid=True,
        gridcolor='#44546A',
        title_text='kW',
        title_font_color='#FFFFFF',
        tickfont_color='#E0E0E0',
        row=1, col=2
    )

    # Make right subplot dark
    fig.update_layout(
        plot_bgcolor='white',
        paper_bgcolor='white',
        title='Norsk Solkraft Themes - Sammenligning',
        height=500,
        showlegend=True
    )

    # Manually override right plot background
    fig.layout.xaxis2.update(dict(
        showgrid=True,
        gridcolor='#44546A',
        plot_bgcolor='#000000'
    ))

    # Save
    fig.write_html('demo_norsk_solkraft_comparison.html')
    print("✅ Saved: demo_norsk_solkraft_comparison.html")

    # Show
    fig.show()


def demo_all_colors():
    """Demo: Vis alle 7 farger i fargepaletten."""
    print("\n" + "=" * 60)
    print("DEMO: ALLE 7 FARGER I PALETTEN")
    print("=" * 60)

    # Aktiver dark theme (fargerik!)
    apply_dark_theme()

    colors = get_brand_colors()
    color_names = [
        'Oransje (HOVEDDATA)',
        'Blå (Sammenligning)',
        'Mose-grønn (Positive)',
        'Gul (Prognose)',
        'Mørk Rød (Kritisk)',
        'Indigo (Info - UNNGÅ PÅ SVART)',
        'Lilla (Alternativ)'
    ]

    # Create traces for each color
    fig = go.Figure()

    for i, (name, color_key) in enumerate(zip(color_names, colors.keys())):
        x = np.linspace(0, 10, 100)
        y = np.sin(x + i * 0.5) + i * 0.8

        fig.add_trace(go.Scatter(
            x=x,
            y=y,
            name=name,
            line=dict(width=3),
            mode='lines'
        ))

    fig.update_layout(
        title='Norsk Solkraft - Full Fargepalett (Dark Theme)',
        xaxis=dict(title='X-akse'),
        yaxis=dict(title='Y-akse'),
        height=600
    )

    # Save
    fig.write_html('demo_norsk_solkraft_all_colors.html')
    print("✅ Saved: demo_norsk_solkraft_all_colors.html")

    # Show
    fig.show()


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("NORSK SOLKRAFT PLOTLY THEMES - DEMO")
    print("=" * 60)

    # Run all demos
    demo_light_theme()
    demo_dark_theme()
    demo_all_colors()
    # demo_comparison_subplots()  # Optional

    print("\n" + "=" * 60)
    print("✅ ALLE DEMOS FULLFØRT!")
    print("=" * 60)
    print("\nGenererte filer:")
    print("  - demo_norsk_solkraft_light.html")
    print("  - demo_norsk_solkraft_dark.html")
    print("  - demo_norsk_solkraft_all_colors.html")
    print("\nÅpne i nettleser for å se resultatene!")
