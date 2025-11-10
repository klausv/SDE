"""
Norsk Solkraft - Custom Plotly Themes
=====================================

Moderne, fargerike themes basert på Norsk Solkraft sin offisielle fargepalett v4.
Støtter både hvit og mørk (svart) bakgrunn med optimal kontrast.

Fargepalett source: FARGEPALETT_NORSK_SOLKRAFT_FINAL_V4.md
Designer: Klaus + Claude
Dato: November 2025
"""

import plotly.graph_objects as go
import plotly.io as pio


# ═══════════════════════════════════════════════════════════════════════════
# NORSK SOLKRAFT FARGEPALETT (Official v4)
# ═══════════════════════════════════════════════════════════════════════════

# Hovedfarger (7 graf-farger)
COLORS = {
    # Kraftige farger (dominerer)
    'oransje': '#F5A621',       # Solenergi Oransje - HOVEDDATA, brand
    'blå': '#00609F',           # Profesjonell Blå - Sammenligning
    'gul': '#FCC808',           # Solkraft Gul - Prognose/høydepunkter

    # Støttende farger
    'mose_grønn': '#A8D8A8',    # Terminal Mose-grønn - Positive (LYS)
    'mørk_rød': '#B71C1C',      # Mørk Rød - Kritisk/alarm
    'indigo': '#1B263B',        # Mørk Indigo-blå - Info (kun på hvit!)
    'lilla': '#B8A8C8',         # Lys Lilla - Alternativ
}

# Grått fundament
GRAYS = {
    'svart': '#000000',         # Kraft Sort - Logo, brand
    'karbonsvart': '#212121',   # Hovedtekst
    'skifer': '#44546A',        # Overskrifter, headers
    'teknisk': '#8A8A8A',       # Labels (passer til alt)
    'silver': '#BDBDBD',        # Gridlinjer, borders
    'lys': '#E0E0E0',           # Bakgrunner
    'snø': '#F5F5F5',           # Alternerende rader
    'hvit': '#FFFFFF',          # Hvit bakgrunn
}

# Semantiske farger
SEMANTIC = {
    'success': COLORS['mose_grønn'],   # Terminal-kjent grønn
    'warning': COLORS['gul'],          # Kraftig gul oppmerksomhet
    'info': COLORS['indigo'],          # Alvorlig info (kun på hvit!)
    'error': COLORS['mørk_rød'],       # Alvorlig, ikke hysterisk
}


# ═══════════════════════════════════════════════════════════════════════════
# THEME 1: NORSK SOLKRAFT LIGHT (Hvit Bakgrunn)
# ═══════════════════════════════════════════════════════════════════════════

norsk_solkraft_light = go.layout.Template(
    layout=dict(
        # Farger (60-30-10 UI/UX regel) - MER GRÅ, MINDRE BLASS
        plot_bgcolor='#F0F0F0',             # 60% - Lys grå bakgrunn (ikke hvit!)
        paper_bgcolor='#FAFAFA',            # Papir lys grå

        # Font hierarki (mørkere for bedre kontrast)
        font=dict(
            family="Arial, Helvetica, sans-serif",
            size=12,
            color=GRAYS['karbonsvart']      # 30% - Hovedtekst (mørk)
        ),

        # Tittel (hierarki) - plassert høyt for legend under
        title=dict(
            font=dict(
                size=18,
                color=GRAYS['svart'],        # Kraftigere svart tittel
                family="Arial, Helvetica, sans-serif"
            ),
            x=0.5,                           # Sentrert
            xanchor='center',
            yanchor='top',
            y=0.98,                          # Helt øverst
            pad=dict(t=20, b=10)
        ),

        # Color palette (10% - accent colors for data series)
        # KRAFTIGERE FARGER - ikke blasse!
        colorway=[
            COLORS['oransje'],      # #1 HOVEDDATA - brand fargen (KRAFTIG)
            COLORS['blå'],          # #2 Sammenligning - kraftig
            '#7AC17A',              # #3 Mørkere grønn (ikke blass mose-grønn!)
            COLORS['gul'],          # #4 Prognose - kraftig gul
            COLORS['mørk_rød'],     # #5 Kritisk/alarm
            COLORS['indigo'],       # #6 Info - PERFEKT på grått (14.2:1)
            '#9B7BB8',              # #7 Mørkere lilla (ikke blass!)
        ],

        # Axes (moderne, tydeligere linjer)
        xaxis=dict(
            showgrid=True,
            gridcolor='#D0D0D0',             # Tydeligere gridlinjer (mørkere grå)
            gridwidth=1,
            zeroline=True,
            zerolinecolor=GRAYS['teknisk'],
            zerolinewidth=2,                 # Tykkere zero-linje
            showline=True,
            linecolor=GRAYS['skifer'],       # Mørkere akselinjer
            linewidth=2,                     # Tykkere akselinjer
            mirror=False,
            title_font=dict(
                size=13,
                color=GRAYS['karbonsvart'],  # Mørkere titler
                family="Arial, Helvetica, sans-serif"
            ),
            tickfont=dict(
                size=11,
                color=GRAYS['skifer']        # Mørkere tick-labels
            )
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor='#D0D0D0',             # Tydeligere gridlinjer
            gridwidth=1,
            zeroline=True,
            zerolinecolor=GRAYS['teknisk'],
            zerolinewidth=2,
            showline=True,
            linecolor=GRAYS['skifer'],       # Mørkere akselinjer
            linewidth=2,
            mirror=False,
            title_font=dict(
                size=13,
                color=GRAYS['karbonsvart'],
                family="Arial, Helvetica, sans-serif"
            ),
            tickfont=dict(
                size=11,
                color=GRAYS['skifer']
            )
        ),

        # Hover effects (moderne, clean)
        hoverlabel=dict(
            bgcolor='#FFFFFF',               # Hvit hover for kontrast
            font_size=12,
            font_family="Arial, Helvetica, sans-serif",
            font_color=GRAYS['karbonsvart'],
            bordercolor=GRAYS['teknisk'],
            align='left'
        ),

        # Legend (mellom tittel og graf - horisontal)
        legend=dict(
            bgcolor='rgba(250,250,250,0.98)', # Semi-transparent lys grå
            bordercolor=GRAYS['teknisk'],
            borderwidth=1.5,
            font=dict(
                size=11,
                color=GRAYS['karbonsvart']
            ),
            orientation='h',     # Horisontal
            yanchor='bottom',    # Anker på bunnen av legend
            y=1.0,               # Over graf-området (mellom tittel og graf)
            xanchor='center',    # Sentrert
            x=0.5
        ),

        # Annotations (hvis brukt)
        annotationdefaults=dict(
            font=dict(
                size=11,
                color=GRAYS['karbonsvart']   # Mørkere annotations
            ),
            arrowcolor=GRAYS['teknisk']
        ),

        # Moderne spacing (økt top margin for legend)
        margin=dict(l=60, r=40, t=120, b=60)
    )
)


# ═══════════════════════════════════════════════════════════════════════════
# THEME 2: NORSK SOLKRAFT DARK (Svart Bakgrunn - Moderne)
# ═══════════════════════════════════════════════════════════════════════════

norsk_solkraft_dark = go.layout.Template(
    layout=dict(
        # Farger (dark mode)
        plot_bgcolor=GRAYS['svart'],        # Svart bakgrunn (brand!)
        paper_bgcolor=GRAYS['svart'],       # Svart papir

        # Font hierarki (hvit på svart)
        font=dict(
            family="Arial, Helvetica, sans-serif",
            size=12,
            color=GRAYS['hvit']             # Hvit tekst
        ),

        # Tittel - plassert høyt for legend under
        title=dict(
            font=dict(
                size=18,
                color=GRAYS['hvit'],
                family="Arial, Helvetica, sans-serif"
            ),
            x=0.5,
            xanchor='center',
            yanchor='top',
            y=0.98,                          # Helt øverst
            pad=dict(t=20, b=10)
        ),

        # Color palette optimalisert for SVART bakgrunn
        # OBS: Mørk indigo (#1B263B) UTELATT - for lav kontrast (1.5:1)!
        colorway=[
            COLORS['oransje'],      # #1 BRILJERER på svart (6.8:1)
            COLORS['blå'],          # #2 STERKT på svart (3.2:1 - kun store)
            COLORS['mose_grønn'],   # #3 PERFEKT på svart (10.2:1) - terminal!
            COLORS['gul'],          # #4 KRAFTIG på svart (12.3:1)
            COLORS['mørk_rød'],     # #5 Alvorlig (4.6:1 - OK)
            COLORS['lilla'],        # #6 Elegant på svart (8.1:1)
            GRAYS['silver'],        # #7 Fallback hvis flere farger trengs
        ],

        # Axes (dark mode styling)
        xaxis=dict(
            showgrid=True,
            gridcolor=GRAYS['skifer'],       # Mørkere grid på svart
            gridwidth=1,
            zeroline=True,
            zerolinecolor=GRAYS['teknisk'],
            zerolinewidth=1.5,
            showline=True,
            linecolor=GRAYS['teknisk'],
            linewidth=1.5,
            mirror=False,
            title_font=dict(
                size=13,
                color=GRAYS['hvit'],
                family="Arial, Helvetica, sans-serif"
            ),
            tickfont=dict(
                size=11,
                color=GRAYS['lys']           # Litt dempet for ticks
            )
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor=GRAYS['skifer'],
            gridwidth=1,
            zeroline=True,
            zerolinecolor=GRAYS['teknisk'],
            zerolinewidth=1.5,
            showline=True,
            linecolor=GRAYS['teknisk'],
            linewidth=1.5,
            mirror=False,
            title_font=dict(
                size=13,
                color=GRAYS['hvit'],
                family="Arial, Helvetica, sans-serif"
            ),
            tickfont=dict(
                size=11,
                color=GRAYS['lys']
            )
        ),

        # Hover effects (dark mode)
        hoverlabel=dict(
            bgcolor=GRAYS['karbonsvart'],    # Nesten-svart for kontrast
            font_size=12,
            font_family="Arial, Helvetica, sans-serif",
            font_color=GRAYS['hvit'],
            bordercolor=GRAYS['skifer'],
            align='left'
        ),

        # Legend (mellom tittel og graf - horisontal)
        legend=dict(
            bgcolor='rgba(33,33,33,0.95)',   # Semi-transparent karbonsvart
            bordercolor=GRAYS['skifer'],
            borderwidth=1,
            font=dict(
                size=11,
                color=GRAYS['hvit']
            ),
            orientation='h',     # Horisontal
            yanchor='bottom',    # Anker på bunnen av legend
            y=1.0,               # Over graf-området (mellom tittel og graf)
            xanchor='center',    # Sentrert
            x=0.5
        ),

        # Annotations (dark mode)
        annotationdefaults=dict(
            font=dict(
                size=11,
                color=GRAYS['lys']
            ),
            arrowcolor=GRAYS['teknisk']
        ),

        # Moderne spacing (økt top margin for legend)
        margin=dict(l=60, r=40, t=120, b=60)
    )
)


# ═══════════════════════════════════════════════════════════════════════════
# REGISTRER THEMES I PLOTLY
# ═══════════════════════════════════════════════════════════════════════════

def register_norsk_solkraft_themes():
    """
    Registrer Norsk Solkraft themes i Plotly.

    Usage:
        import plotly.io as pio
        from visualization.norsk_solkraft_theme import register_norsk_solkraft_themes

        # Registrer themes
        register_norsk_solkraft_themes()

        # Bruk light theme (default)
        pio.templates.default = "norsk_solkraft_light"

        # Eller dark theme
        pio.templates.default = "norsk_solkraft_dark"

        # Eller per figur
        fig.update_layout(template='norsk_solkraft_dark')
    """
    pio.templates["norsk_solkraft_light"] = norsk_solkraft_light
    pio.templates["norsk_solkraft_dark"] = norsk_solkraft_dark

    print("✅ Norsk Solkraft themes registered:")
    print("   - 'norsk_solkraft_light' (hvit bakgrunn)")
    print("   - 'norsk_solkraft_dark' (svart bakgrunn)")
    print("\nSet default: pio.templates.default = 'norsk_solkraft_dark'")


# ═══════════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

def get_brand_colors():
    """Returner Norsk Solkraft fargepalett som dict."""
    return COLORS.copy()


def get_gray_scale():
    """Returner grå-skala som dict."""
    return GRAYS.copy()


def get_semantic_colors():
    """Returner semantiske farger som dict."""
    return SEMANTIC.copy()


def apply_light_theme():
    """Shortcut for å aktivere light theme globally."""
    register_norsk_solkraft_themes()
    pio.templates.default = "norsk_solkraft_light"
    print("✅ Norsk Solkraft LIGHT theme activated (hvit bakgrunn)")


def apply_dark_theme():
    """Shortcut for å aktivere dark theme globally."""
    register_norsk_solkraft_themes()
    pio.templates.default = "norsk_solkraft_dark"
    print("✅ Norsk Solkraft DARK theme activated (svart bakgrunn)")


# ═══════════════════════════════════════════════════════════════════════════
# AUTO-REGISTER VED IMPORT (optional)
# ═══════════════════════════════════════════════════════════════════════════

# Uncomment for auto-registration:
# register_norsk_solkraft_themes()


if __name__ == "__main__":
    # Test script
    print("Norsk Solkraft Plotly Themes")
    print("=" * 50)

    # Registrer themes
    register_norsk_solkraft_themes()

    # Vis tilgjengelige templates
    print("\nTilgjengelige Plotly templates:")
    print(pio.templates)

    # Eksempel bruk
    print("\n" + "=" * 50)
    print("EKSEMPEL BRUK:")
    print("=" * 50)
    print("""
# Light theme (hvit bakgrunn)
from visualization.norsk_solkraft_theme import apply_light_theme
apply_light_theme()

# Dark theme (svart bakgrunn)
from visualization.norsk_solkraft_theme import apply_dark_theme
apply_dark_theme()

# Eller manuelt per figur:
import plotly.graph_objects as go
fig = go.Figure(data=[...])
fig.update_layout(template='norsk_solkraft_dark')
fig.show()

# Hent farger for custom bruk:
from visualization.norsk_solkraft_theme import get_brand_colors
colors = get_brand_colors()
print(colors['oransje'])  # #F5A621
    """)
