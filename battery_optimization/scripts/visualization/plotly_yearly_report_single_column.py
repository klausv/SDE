"""
Interactive Plotly Yearly Report Generator - Optimized Layout

Forbedringer v2:
- Én kolonne layout med consolidated net grid flow (import/export merged)
- Rad 11: 2 kolonner (monthly peaks + tables side-by-side)
- Legends inside top-right (reliable positioning)
- Sterkere fargekontrast for bedre lesbarhet
- Solid, tykkere spotpris-linje
- Tabell-tekst 30% mindre, uten scrollbar
"""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import Norsk Solkraft light theme
from src.visualization.norsk_solkraft_theme import apply_light_theme


def load_data(results_dir: str):
    """Load trajectory and input data"""
    results_path = Path(results_dir)

    # Load trajectory
    trajectory = pd.read_csv(results_path / "trajectory.csv", parse_dates=["timestamp"])

    # Load input data
    prices = pd.read_csv("data/spot_prices/NO2_2024_60min_real.csv")
    production = pd.read_csv("data/pv_profiles/pvgis_58.97_5.73_138.55kWp.csv", index_col=0)
    consumption = pd.read_csv("data/consumption/commercial_2024.csv", parse_dates=["timestamp"])

    # Convert production index to datetime (2020 labels → 2024)
    production.index = pd.to_datetime(production.index)
    production.index = production.index.map(lambda x: x.replace(year=2024))
    production = production.reset_index()
    production.columns = ["timestamp", "production_kw"]

    # Round production timestamps to nearest hour for merge
    production["timestamp"] = production["timestamp"].dt.floor("h")

    # Remove timezone from prices for alignment
    prices["timestamp"] = pd.to_datetime(prices["timestamp"], utc=True).dt.tz_localize(None)

    # Merge all data
    data = trajectory.copy()
    data = data.merge(prices, on="timestamp", how="left")
    data = data.merge(production, on="timestamp", how="left")
    data = data.merge(consumption, on="timestamp", how="left")

    # Fill missing values
    data["price_nok"] = data["price_nok"].ffill().bfill()
    data["production_kw"] = data["production_kw"].fillna(0)
    data["consumption_kw"] = data["consumption_kw"].ffill()

    return data


def calculate_reference_scenario(data: pd.DataFrame, grid_limit_kw: float = 77):
    """Calculate reference scenario WITHOUT battery"""
    ref = data.copy()
    ref["net_load_kw"] = ref["consumption_kw"] - ref["production_kw"]
    ref["P_grid_import_ref_kw"] = np.where(ref["net_load_kw"] > 0, ref["net_load_kw"], 0)
    potential_export = np.where(ref["net_load_kw"] < 0, -ref["net_load_kw"], 0)
    ref["P_grid_export_ref_kw"] = np.minimum(potential_export, grid_limit_kw)
    ref["P_curtail_ref_kw"] = potential_export - ref["P_grid_export_ref_kw"]
    return ref


def calculate_power_tariff_cost(monthly_peak_kw: float) -> float:
    """Calculate Lnett commercial progressive power tariff cost"""
    brackets = [
        (0, 50, 41.50),
        (50, 100, 50.00),
        (100, 200, 59.00),
        (200, 300, 84.00),
        (300, float('inf'), 102.00)
    ]
    total_cost = 0
    for low, high, rate in brackets:
        if monthly_peak_kw > low:
            bracket_kw = min(monthly_peak_kw, high) - low
            total_cost += bracket_kw * rate
    return total_cost


def calculate_4category_breakdown(data: pd.DataFrame, battery_kwh: float = 30, battery_kw: float = 15):
    """Calculate simplified 4-category revenue breakdown"""
    TARIFF_PEAK = 0.296
    TARIFF_OFFPEAK = 0.176
    ENERGY_TAX = 0.1791
    FEED_IN_PREMIUM = 0.04
    DEGRADATION_COST_PER_KWH = 0.05

    data["hour"] = data["timestamp"].dt.hour
    data["weekday"] = data["timestamp"].dt.weekday
    data["month"] = data["timestamp"].dt.to_period("M")
    data["is_peak"] = ((data["weekday"] < 5) & (data["hour"] >= 6) & (data["hour"] < 22))
    data["tariff"] = np.where(data["is_peak"], TARIFF_PEAK, TARIFF_OFFPEAK)

    ref = calculate_reference_scenario(data)
    ref["month"] = ref["timestamp"].dt.to_period("M")

    # Category 1: Peak power tariff savings
    monthly_peaks_with = data.groupby("month")["P_grid_import_kw"].max()
    monthly_peaks_ref = ref.groupby("month")["P_grid_import_ref_kw"].max()
    power_cost_with = sum(calculate_power_tariff_cost(peak) for peak in monthly_peaks_with)
    power_cost_ref = sum(calculate_power_tariff_cost(peak) for peak in monthly_peaks_ref)
    effektkostnad_besparelse = power_cost_ref - power_cost_with

    # Category 2: Reduced grid import
    import_ref_cost = (ref["P_grid_import_ref_kw"] * (ref["price_nok"] +
                       np.where(ref["is_peak"], TARIFF_PEAK, TARIFF_OFFPEAK) + ENERGY_TAX)).sum()
    import_with_cost = (data["P_grid_import_kw"] * (data["price_nok"] + data["tariff"] + ENERGY_TAX)).sum()
    export_ref_revenue = (ref["P_grid_export_ref_kw"] * (ref["price_nok"] + FEED_IN_PREMIUM)).sum()
    export_with_revenue = (data["P_grid_export_kw"] * (data["price_nok"] + FEED_IN_PREMIUM)).sum()
    redusert_nettimport = (import_ref_cost - import_with_cost) - (export_ref_revenue - export_with_revenue)

    # Category 3: Avoided curtailment
    curtailment_ref_kwh = ref["P_curtail_ref_kw"].sum()
    curtailment_with_kwh = data["P_curtail_kw"].sum()
    avg_export_price = data["price_nok"].mean() + FEED_IN_PREMIUM
    unngatt_curtailment = (curtailment_ref_kwh - curtailment_with_kwh) * avg_export_price

    # Category 4: Degradation
    total_charged = data["P_charge_kw"].sum()
    total_discharged = data["P_discharge_kw"].sum()
    avg_cycled = (total_charged + total_discharged) / 2
    batteridegradering = avg_cycled * DEGRADATION_COST_PER_KWH

    total_savings = (effektkostnad_besparelse + redusert_nettimport +
                     unngatt_curtailment - batteridegradering)

    context_metrics = {
        "curtailment_reduction_pct": ((curtailment_ref_kwh - curtailment_with_kwh) / curtailment_ref_kwh * 100) if curtailment_ref_kwh > 0 else 0,
        "avg_peak_reduction_kw": (monthly_peaks_ref - monthly_peaks_with).mean(),
        "battery_cycles": avg_cycled / (2 * battery_kwh),
        "capacity_factor": (total_discharged / (battery_kw * 8760)) * 100,
    }

    breakdown = {
        "Effektkostnad-besparelse": effektkostnad_besparelse,
        "Redusert nettimport": redusert_nettimport,
        "Unngått curtailment": unngatt_curtailment,
        "Batteridegradering": -batteridegradering,
    }

    return breakdown, total_savings, ref, monthly_peaks_ref, context_metrics


def create_table_trace(breakdown: dict, total_savings: float):
    """Create Plotly table trace with SMALLER fonts (30% reduction)"""
    categories = list(breakdown.keys()) + ["NETTO"]
    values = list(breakdown.values()) + [total_savings]

    cell_colors = []
    for val in values:
        if val >= 0:
            cell_colors.append('#2ecc71')
        else:
            cell_colors.append('#e74c3c')

    formatted_values = []
    for val in values:
        sign = "+" if val >= 0 else ""
        formatted_values.append(f"{sign}{val:,.0f} kr/år")

    table = go.Table(
        header=dict(
            values=['<b>Kategori</b>', '<b>Verdi</b>'],
            fill_color='#44546A',
            align='left',
            font=dict(color='white', size=18, family='Arial')  # Reduced from 26
        ),
        cells=dict(
            values=[categories, formatted_values],
            fill_color=['#E0E0E0', cell_colors],
            align=['left', 'right'],
            font=dict(color='#212121', size=17, family='Arial'),  # Reduced from 24
            height=35  # Reduced from 50
        )
    )
    return table


def create_metrics_table_trace(context_metrics: dict, battery_kwh: float):
    """Create Plotly table trace for key metrics with SMALLER fonts (30% reduction)"""
    metrics = [
        ("Curtailment-reduksjon", f"{context_metrics['curtailment_reduction_pct']:.1f} %"),
        ("Gjennomsnittlig effektreduksjon", f"{context_metrics['avg_peak_reduction_kw']:.1f} kW"),
        ("Batterisykluser per år", f"{context_metrics['battery_cycles']:.1f}"),
        ("Kapasitetsfaktor", f"{context_metrics['capacity_factor']:.1f} %"),
    ]

    metric_names = [m[0] for m in metrics]
    metric_values = [m[1] for m in metrics]

    table = go.Table(
        header=dict(
            values=['<b>Metrikk</b>', '<b>Verdi</b>'],
            fill_color='#44546A',
            align='left',
            font=dict(color='white', size=18, family='Arial')  # Reduced from 26
        ),
        cells=dict(
            values=[metric_names, metric_values],
            fill_color=['#E0E0E0', '#B8D8E8'],
            align=['left', 'right'],
            font=dict(color='#212121', size=17, family='Arial'),  # Reduced from 24
            height=35  # Reduced from 50
        )
    )
    return table


def create_comprehensive_report(results_dir: str, battery_kwh: float = 30, battery_kw: float = 15):
    """
    Create comprehensive report with SINGLE COLUMN LAYOUT:
    - Row 1: Mai - PV-produksjon, Last og Spotpris
    - Row 2: Februar - PV-produksjon, Last og Spotpris
    - Row 3: Mai - Nettimport Med/Uten Batteri
    - Row 4: Februar - Nettimport Med/Uten Batteri
    - Row 5: Mai - Netteksport Med/Uten Batteri
    - Row 6: Februar - Netteksport Med/Uten Batteri
    - Row 7: Mai - Batterilading/-utlading
    - Row 8: Februar - Batterilading/-utlading
    - Row 9: Mai - Batterilading (SOC)
    - Row 10: Februar - Batterilading (SOC)
    - Row 11: Månedlig Effekttopp - Helår
    - Row 12: Kostnadsfordeling - Helår (table)
    - Row 13: Nøkkelmetrikker - Helår (table)

    All legends positioned OUTSIDE bottom of each graph.
    Graph heights increased by 30%.
    """

    # Load data
    print("Loading data...")
    data = load_data(results_dir)

    # Calculate breakdown and reference
    print("Calculating 4-category breakdown...")
    breakdown, total_savings, ref, monthly_peaks_ref, context_metrics = calculate_4category_breakdown(data, battery_kwh, battery_kw)

    # Get monthly peaks
    monthly_peaks_with = data.groupby(data["timestamp"].dt.to_period("M"))["P_grid_import_kw"].max()

    # Filter data for May (month 5) and February (month 2)
    data_may = data[data["timestamp"].dt.month == 5].copy()
    ref_may = ref[ref["timestamp"].dt.month == 5].copy()

    data_feb = data[data["timestamp"].dt.month == 2].copy()
    ref_feb = ref[ref["timestamp"].dt.month == 2].copy()

    print(f"  Mai data: {len(data_may)} hours")
    print(f"  Februar data: {len(data_feb)} hours")

    # Row heights: increased by 30% for graphs
    # Original: ~0.077 each for equal 13 rows
    # With 30% increase: 0.077 * 1.3 = 0.100 for graphs
    # Tables remain smaller: 0.06 each
    row_heights = [
        0.100, 0.100,  # Rows 1-2: PV/Load/Price (Mai, Feb)
        0.100, 0.100,  # Rows 3-4: Import (Mai, Feb)
        0.100, 0.100,  # Rows 5-6: Export (Mai, Feb)
        0.100, 0.100,  # Rows 7-8: Charge/Discharge (Mai, Feb)
        0.100, 0.100,  # Rows 9-10: SOC (Mai, Feb)
        0.100,         # Row 11: Monthly peaks bar chart
        0.06,          # Row 12: Cost breakdown table
        0.06           # Row 13: Metrics table
    ]

    # Create figure with single column
    fig = make_subplots(
        rows=13, cols=1,
        row_heights=row_heights,
        subplot_titles=(
            "MAI - PV-produksjon, Last og Spotpris",
            "FEBRUAR - PV-produksjon, Last og Spotpris",
            "MAI - Nettimport Med/Uten Batteri",
            "FEBRUAR - Nettimport Med/Uten Batteri",
            "MAI - Netteksport Med/Uten Batteri",
            "FEBRUAR - Netteksport Med/Uten Batteri",
            "MAI - Batterilading/-utlading",
            "FEBRUAR - Batterilading/-utlading",
            "MAI - Batterilading (SOC)",
            "FEBRUAR - Batterilading (SOC)",
            "Månedlig Effekttopp - Helår",
            "Kostnadsfordeling - Helår",
            "Nøkkelmetrikker - Helår"
        ),
        specs=[
            [{"secondary_y": True}],   # Row 1: Mai PV/Load/Price
            [{"secondary_y": True}],   # Row 2: Feb PV/Load/Price
            [{}],                      # Row 3: Mai Import
            [{}],                      # Row 4: Feb Import
            [{}],                      # Row 5: Mai Export
            [{}],                      # Row 6: Feb Export
            [{}],                      # Row 7: Mai Charge/Discharge
            [{}],                      # Row 8: Feb Charge/Discharge
            [{}],                      # Row 9: Mai SOC
            [{}],                      # Row 10: Feb SOC
            [{"type": "bar"}],         # Row 11: Monthly peaks
            [{"type": "table"}],       # Row 12: Cost breakdown
            [{"type": "table"}]        # Row 13: Metrics
        ],
        vertical_spacing=0.02,  # Tight vertical spacing
    )

    # Update subplot title font size (dark color for light theme)
    for annotation in fig['layout']['annotations']:
        annotation['font'] = dict(size=18, color='#212121')

    # === ROW 1: Mai - PV Production, Load, Spot Prices ===
    fig.add_trace(
        go.Scatter(x=data_may["timestamp"], y=data_may["production_kw"],
                   name="PV-produksjon", line=dict(color="#F5A621", width=1.5),
                   fill="tozeroy", fillcolor="rgba(245, 166, 33, 0.2)",
                   legendgroup="row1", showlegend=True, legend="legend"),
        row=1, col=1, secondary_y=False
    )
    fig.add_trace(
        go.Scatter(x=data_may["timestamp"], y=data_may["consumption_kw"],
                   name="Last", line=dict(color="#00609F", width=2),
                   legendgroup="row1", showlegend=True, legend="legend"),
        row=1, col=1, secondary_y=False
    )
    fig.add_trace(
        go.Scatter(x=data_may["timestamp"], y=data_may["price_nok"],
                   name="Spotpris", line=dict(color="#A8D8A8", width=1.5, dash="dot"),
                   legendgroup="row1", showlegend=True, legend="legend"),
        row=1, col=1, secondary_y=True
    )

    # === ROW 2: Februar - PV Production, Load, Spot Prices ===
    fig.add_trace(
        go.Scatter(x=data_feb["timestamp"], y=data_feb["production_kw"],
                   name="PV-produksjon", line=dict(color="#F5A621", width=1.5),
                   fill="tozeroy", fillcolor="rgba(245, 166, 33, 0.2)",
                   legendgroup="row2", showlegend=True, legend="legend2"),
        row=2, col=1, secondary_y=False
    )
    fig.add_trace(
        go.Scatter(x=data_feb["timestamp"], y=data_feb["consumption_kw"],
                   name="Last", line=dict(color="#00609F", width=2),
                   legendgroup="row2", showlegend=True, legend="legend2"),
        row=2, col=1, secondary_y=False
    )
    fig.add_trace(
        go.Scatter(x=data_feb["timestamp"], y=data_feb["price_nok"],
                   name="Spotpris", line=dict(color="#A8D8A8", width=1.5, dash="dot"),
                   legendgroup="row2", showlegend=True, legend="legend2"),
        row=2, col=1, secondary_y=True
    )

    # === ROW 3: Mai - Grid Import ===
    fig.add_trace(
        go.Scatter(x=ref_may["timestamp"], y=ref_may["P_grid_import_ref_kw"],
                   name="Uten batteri", line=dict(color="#FCC808", width=2),
                   fill="tozeroy", fillcolor="rgba(252, 200, 8, 0.2)",
                   legendgroup="row3", showlegend=True, legend="legend3"),
        row=3, col=1
    )
    fig.add_trace(
        go.Scatter(x=data_may["timestamp"], y=data_may["P_grid_import_kw"],
                   name="Med batteri", line=dict(color="#B71C1C", width=2),
                   fill="tozeroy", fillcolor="rgba(183, 28, 28, 0.3)",
                   legendgroup="row3", showlegend=True, legend="legend3"),
        row=3, col=1
    )

    # === ROW 4: Februar - Grid Import ===
    fig.add_trace(
        go.Scatter(x=ref_feb["timestamp"], y=ref_feb["P_grid_import_ref_kw"],
                   name="Uten batteri", line=dict(color="#FCC808", width=2),
                   fill="tozeroy", fillcolor="rgba(252, 200, 8, 0.2)",
                   legendgroup="row4", showlegend=True, legend="legend4"),
        row=4, col=1
    )
    fig.add_trace(
        go.Scatter(x=data_feb["timestamp"], y=data_feb["P_grid_import_kw"],
                   name="Med batteri", line=dict(color="#B71C1C", width=2),
                   fill="tozeroy", fillcolor="rgba(183, 28, 28, 0.3)",
                   legendgroup="row4", showlegend=True, legend="legend4"),
        row=4, col=1
    )

    # === ROW 5: Mai - Grid Export ===
    fig.add_trace(
        go.Scatter(x=ref_may["timestamp"], y=ref_may["P_grid_export_ref_kw"],
                   name="Uten batteri", line=dict(color="#B8A8C8", width=2),
                   fill="tozeroy", fillcolor="rgba(184, 168, 200, 0.2)",
                   legendgroup="row5", showlegend=True, legend="legend5"),
        row=5, col=1
    )
    fig.add_trace(
        go.Scatter(x=data_may["timestamp"], y=data_may["P_grid_export_kw"],
                   name="Med batteri", line=dict(color="#00609F", width=2),
                   fill="tozeroy", fillcolor="rgba(0, 96, 159, 0.3)",
                   legendgroup="row5", showlegend=True, legend="legend5"),
        row=5, col=1
    )

    # === ROW 6: Februar - Grid Export ===
    fig.add_trace(
        go.Scatter(x=ref_feb["timestamp"], y=ref_feb["P_grid_export_ref_kw"],
                   name="Uten batteri", line=dict(color="#B8A8C8", width=2),
                   fill="tozeroy", fillcolor="rgba(184, 168, 200, 0.2)",
                   legendgroup="row6", showlegend=True, legend="legend6"),
        row=6, col=1
    )
    fig.add_trace(
        go.Scatter(x=data_feb["timestamp"], y=data_feb["P_grid_export_kw"],
                   name="Med batteri", line=dict(color="#00609F", width=2),
                   fill="tozeroy", fillcolor="rgba(0, 96, 159, 0.3)",
                   legendgroup="row6", showlegend=True, legend="legend6"),
        row=6, col=1
    )

    # === ROW 7: Mai - Battery Charge/Discharge ===
    fig.add_trace(
        go.Scatter(x=data_may["timestamp"], y=data_may["P_charge_kw"],
                   name="Lading", line=dict(color="#A8D8A8", width=1.5),
                   fill="tozeroy", fillcolor="rgba(168, 216, 168, 0.2)",
                   legendgroup="row7", showlegend=True, legend="legend7"),
        row=7, col=1
    )
    fig.add_trace(
        go.Scatter(x=data_may["timestamp"], y=-data_may["P_discharge_kw"],
                   name="Utlading", line=dict(color="#B71C1C", width=1.5),
                   fill="tozeroy", fillcolor="rgba(183, 28, 28, 0.2)",
                   legendgroup="row7", showlegend=True, legend="legend7"),
        row=7, col=1
    )

    # === ROW 8: Februar - Battery Charge/Discharge ===
    fig.add_trace(
        go.Scatter(x=data_feb["timestamp"], y=data_feb["P_charge_kw"],
                   name="Lading", line=dict(color="#A8D8A8", width=1.5),
                   fill="tozeroy", fillcolor="rgba(168, 216, 168, 0.2)",
                   legendgroup="row8", showlegend=True, legend="legend8"),
        row=8, col=1
    )
    fig.add_trace(
        go.Scatter(x=data_feb["timestamp"], y=-data_feb["P_discharge_kw"],
                   name="Utlading", line=dict(color="#B71C1C", width=1.5),
                   fill="tozeroy", fillcolor="rgba(183, 28, 28, 0.2)",
                   legendgroup="row8", showlegend=True, legend="legend8"),
        row=8, col=1
    )

    # === ROW 9: Mai - Battery SOC ===
    fig.add_trace(
        go.Scatter(x=data_may["timestamp"], y=data_may["E_battery_kwh"],
                   name="SOC", line=dict(color="#B8A8C8", width=2),
                   fill="tozeroy", fillcolor="rgba(184, 168, 200, 0.3)",
                   legendgroup="row9", showlegend=True, legend="legend9"),
        row=9, col=1
    )
    fig.add_hline(y=battery_kwh * 0.9, line_dash="dash", line_color="#B71C1C",
                  annotation_text="Max SOC (90%)", annotation_font_size=14, row=9, col=1)
    fig.add_hline(y=battery_kwh * 0.1, line_dash="dash", line_color="#B71C1C",
                  annotation_text="Min SOC (10%)", annotation_font_size=14, row=9, col=1)

    # === ROW 10: Februar - Battery SOC ===
    fig.add_trace(
        go.Scatter(x=data_feb["timestamp"], y=data_feb["E_battery_kwh"],
                   name="SOC", line=dict(color="#B8A8C8", width=2),
                   fill="tozeroy", fillcolor="rgba(184, 168, 200, 0.3)",
                   legendgroup="row10", showlegend=True, legend="legend10"),
        row=10, col=1
    )
    fig.add_hline(y=battery_kwh * 0.9, line_dash="dash", line_color="#B71C1C",
                  annotation_text="Max SOC (90%)", annotation_font_size=14, row=10, col=1)
    fig.add_hline(y=battery_kwh * 0.1, line_dash="dash", line_color="#B71C1C",
                  annotation_text="Min SOC (10%)", annotation_font_size=14, row=10, col=1)

    # === ROW 11: Monthly Peaks (full year) ===
    months = [str(m) for m in monthly_peaks_ref.index]
    fig.add_trace(
        go.Bar(x=months, y=monthly_peaks_ref.values,
               name="Uten batteri", marker_color="#FCC808",
               legendgroup="row11", showlegend=True, legend="legend11"),
        row=11, col=1
    )
    fig.add_trace(
        go.Bar(x=months, y=monthly_peaks_with.values,
               name="Med batteri", marker_color="#F5A621",
               legendgroup="row11", showlegend=True, legend="legend11"),
        row=11, col=1
    )

    # === ROW 12: Cost Breakdown Table ===
    table = create_table_trace(breakdown, total_savings)
    fig.add_trace(table, row=12, col=1)

    # === ROW 13: Key Metrics Table ===
    metrics_table = create_metrics_table_trace(context_metrics, battery_kwh)
    fig.add_trace(metrics_table, row=13, col=1)

    # Update axes labels with appropriate fonts
    for row in range(1, 11):
        fig.update_xaxes(tickfont=dict(size=14), row=row, col=1)
        fig.update_yaxes(tickfont=dict(size=14), row=row, col=1)

    # Row 1-2 y-axis titles (dual y-axis)
    fig.update_yaxes(title_text="Effekt (kW)", title_font=dict(size=16), title_standoff=5, row=1, col=1, secondary_y=False)
    fig.update_yaxes(title_text="Pris (kr/kWh)", title_font=dict(size=16), title_standoff=5, row=1, col=1, secondary_y=True)
    fig.update_yaxes(title_text="Effekt (kW)", title_font=dict(size=16), title_standoff=5, row=2, col=1, secondary_y=False)
    fig.update_yaxes(title_text="Pris (kr/kWh)", title_font=dict(size=16), title_standoff=5, row=2, col=1, secondary_y=True)

    # Other y-axis titles
    fig.update_yaxes(title_text="Import (kW)", title_font=dict(size=16), row=3, col=1)
    fig.update_yaxes(title_text="Import (kW)", title_font=dict(size=16), row=4, col=1)
    fig.update_yaxes(title_text="Eksport (kW)", title_font=dict(size=16), row=5, col=1)
    fig.update_yaxes(title_text="Eksport (kW)", title_font=dict(size=16), row=6, col=1)
    fig.update_yaxes(title_text="Effekt (kW)", title_font=dict(size=16), row=7, col=1)
    fig.update_yaxes(title_text="Effekt (kW)", title_font=dict(size=16), row=8, col=1)
    fig.update_yaxes(title_text="Energi (kWh)", title_font=dict(size=16), row=9, col=1)
    fig.update_yaxes(title_text="Energi (kWh)", title_font=dict(size=16), row=10, col=1)

    # Row 11
    fig.update_xaxes(title_text="Måned", title_font=dict(size=16), tickfont=dict(size=14), row=11, col=1)
    fig.update_yaxes(title_text="Effekttopp (kW)", title_font=dict(size=16), tickfont=dict(size=14), row=11, col=1)

    # Update layout with legends OUTSIDE BOTTOM
    fig.update_layout(
        title=dict(
            text=f"Batterioptimalisering - Månedlig Detaljvisning 2024<br><sub>Batteri: {battery_kwh} kWh / {battery_kw} kW | Netto årlig verdi: {total_savings:,.0f} kr/år</sub>",
            x=0.5,
            xanchor='center',
            font=dict(size=24)
        ),
        height=4000,  # Increased height to accommodate 13 rows + legends
        showlegend=True,
        font=dict(size=16),
        barmode="group",
        margin=dict(l=80, r=40, t=100, b=60),

        # Configure 11 legends - positioned OUTSIDE BOTTOM of each graph
        legend=dict(font=dict(size=14, color='#212121'), bgcolor='rgba(255, 255, 255, 0.95)',
                   bordercolor='#44546A', borderwidth=1,
                   orientation='h', yanchor='top', y=-0.12, xanchor='center', x=0.5),
        legend2=dict(font=dict(size=14, color='#212121'), bgcolor='rgba(255, 255, 255, 0.95)',
                    bordercolor='#44546A', borderwidth=1,
                    orientation='h', yanchor='top', y=-0.12, xanchor='center', x=0.5),
        legend3=dict(font=dict(size=14, color='#212121'), bgcolor='rgba(255, 255, 255, 0.95)',
                    bordercolor='#44546A', borderwidth=1,
                    orientation='h', yanchor='top', y=-0.12, xanchor='center', x=0.5),
        legend4=dict(font=dict(size=14, color='#212121'), bgcolor='rgba(255, 255, 255, 0.95)',
                    bordercolor='#44546A', borderwidth=1,
                    orientation='h', yanchor='top', y=-0.12, xanchor='center', x=0.5),
        legend5=dict(font=dict(size=14, color='#212121'), bgcolor='rgba(255, 255, 255, 0.95)',
                    bordercolor='#44546A', borderwidth=1,
                    orientation='h', yanchor='top', y=-0.12, xanchor='center', x=0.5),
        legend6=dict(font=dict(size=14, color='#212121'), bgcolor='rgba(255, 255, 255, 0.95)',
                    bordercolor='#44546A', borderwidth=1,
                    orientation='h', yanchor='top', y=-0.12, xanchor='center', x=0.5),
        legend7=dict(font=dict(size=14, color='#212121'), bgcolor='rgba(255, 255, 255, 0.95)',
                    bordercolor='#44546A', borderwidth=1,
                    orientation='h', yanchor='top', y=-0.12, xanchor='center', x=0.5),
        legend8=dict(font=dict(size=14, color='#212121'), bgcolor='rgba(255, 255, 255, 0.95)',
                    bordercolor='#44546A', borderwidth=1,
                    orientation='h', yanchor='top', y=-0.12, xanchor='center', x=0.5),
        legend9=dict(font=dict(size=14, color='#212121'), bgcolor='rgba(255, 255, 255, 0.95)',
                    bordercolor='#44546A', borderwidth=1,
                    orientation='h', yanchor='top', y=-0.12, xanchor='center', x=0.5),
        legend10=dict(font=dict(size=14, color='#212121'), bgcolor='rgba(255, 255, 255, 0.95)',
                     bordercolor='#44546A', borderwidth=1,
                     orientation='h', yanchor='top', y=-0.12, xanchor='center', x=0.5),
        legend11=dict(font=dict(size=14, color='#212121'), bgcolor='rgba(255, 255, 255, 0.95)',
                     bordercolor='#44546A', borderwidth=1,
                     orientation='h', yanchor='top', y=-0.12, xanchor='center', x=0.5),
    )

    return fig, breakdown, total_savings, context_metrics


if __name__ == "__main__":
    # Apply Norsk Solkraft light theme
    apply_light_theme()

    # Generate report
    results_dir = "results/yearly_2024"
    battery_kwh = 30
    battery_kw = 15

    print(f"\nGenerating Single Column Report (Mai + Februar) for {battery_kwh} kWh / {battery_kw} kW battery...")
    print("=" * 80)
    fig, breakdown, total, context = create_comprehensive_report(results_dir, battery_kwh, battery_kw)

    # Print breakdown
    print("\n=== KOSTNADSFORDELING (4 KATEGORIER) ===")
    for category, value in breakdown.items():
        sign = "+" if value >= 0 else ""
        print(f"{category:.<45} {sign}{value:>10,.2f} kr/år")
    print(f"{'=' * 56}")
    print(f"{'NETTO ÅRLIG VERDI':.<45} {total:>10,.2f} kr/år")

    print("\n=== NØKKELMETRIKKER ===")
    print(f"{'Curtailment-reduksjon':.<45} {context['curtailment_reduction_pct']:>10.1f} %")
    print(f"{'Gjennomsnittlig effektreduksjon':.<45} {context['avg_peak_reduction_kw']:>10.1f} kW")
    print(f"{'Batterisykluser per år':.<45} {context['battery_cycles']:>10.1f}")
    print(f"{'Kapasitetsfaktor':.<45} {context['capacity_factor']:>10.1f} %")

    # Save interactive HTML
    output_file = f"{results_dir}/plotly_single_column_mai_feb.html"
    fig.write_html(output_file)
    print(f"\n✅ Interactive report saved to: {output_file}")
    print("=" * 80)

    # Open in browser
    import webbrowser
    webbrowser.open(f"file://{Path(output_file).absolute()}")
