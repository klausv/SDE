#!/usr/bin/env python3
"""
Update NPV graph with corrected simulation results
"""

import plotly.graph_objects as go
import numpy as np

def create_npv_graph():
    """Create updated NPV graph with corrected values"""

    # Battery cost range (NOK/kWh)
    battery_costs = np.linspace(1000, 6000, 50)

    # Battery specifications
    battery_kwh = 10
    battery_kw = 5
    battery_lifetime = 15
    discount_rate = 0.05

    # Annual savings at different battery costs (based on simulation)
    # With corrected consumption (90,000 kWh) and 95% efficiency
    # The battery actually loses money due to reduced export revenue
    annual_savings_base = -515  # NOK/year at 2500 NOK/kWh

    # NPV calculation for each battery cost
    npv_values = []
    for cost_per_kwh in battery_costs:
        battery_cost = battery_kwh * cost_per_kwh

        # Annual savings remain constant (battery performance doesn't change with cost)
        annual_savings = annual_savings_base

        # Calculate NPV
        npv = -battery_cost
        for year in range(1, battery_lifetime + 1):
            npv += annual_savings / (1 + discount_rate) ** year

        npv_values.append(npv)

    # Create the plot
    fig = go.Figure()

    # Main NPV line
    fig.add_trace(go.Scatter(
        x=battery_costs,
        y=npv_values,
        mode='lines',
        name='NPV',
        line=dict(color='#1E88E5', width=3),
        hovertemplate='Battery Cost: %{x:,.0f} NOK/kWh<br>NPV: %{y:,.0f} NOK<extra></extra>'
    ))

    # Add break-even line at NPV = 0
    fig.add_hline(
        y=0,
        line_dash="dash",
        line_color="red",
        annotation_text="Break-even (NPV = 0)"
    )

    # Add marker for target cost (2500 NOK/kWh)
    target_cost = 2500
    target_npv = -30341  # From corrected simulation

    fig.add_trace(go.Scatter(
        x=[target_cost],
        y=[target_npv],
        mode='markers+text',
        name='Target Cost',
        marker=dict(size=12, color='red', symbol='star'),
        text=['Target: -30,341 NOK'],
        textposition="top center",
        showlegend=True,
        hovertemplate='Target Cost: 2,500 NOK/kWh<br>NPV: -30,341 NOK<extra></extra>'
    ))

    # Add marker for current market price
    market_cost = 5000
    market_npv = -battery_kwh * market_cost + annual_savings_base * sum(1/(1.05)**i for i in range(1, 16))

    fig.add_trace(go.Scatter(
        x=[market_cost],
        y=[market_npv],
        mode='markers+text',
        name='Current Market',
        marker=dict(size=10, color='orange', symbol='circle'),
        text=['Market: {:,.0f} NOK'.format(market_npv)],
        textposition="bottom center",
        showlegend=True,
        hovertemplate='Market Price: 5,000 NOK/kWh<br>NPV: {:,.0f} NOK<extra></extra>'.format(market_npv)
    ))

    # Update layout
    fig.update_layout(
        title={
            'text': 'NPV Analysis: Battery Investment<br><sub>Corrected with 90,000 kWh consumption & 95% efficiency</sub>',
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 18}
        },
        xaxis=dict(
            title="Battery Cost (NOK/kWh)",
            tickformat=",.",
            gridcolor='#E0E0E0',
            showgrid=True,
            range=[1000, 6000]
        ),
        yaxis=dict(
            title="Net Present Value (NOK)",
            tickformat=",.",
            gridcolor='#E0E0E0',
            showgrid=True,
            zeroline=True,
            zerolinewidth=2,
            zerolinecolor='red'
        ),
        plot_bgcolor='#FAFAFA',
        paper_bgcolor='white',
        hovermode='x unified',
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        height=500,
        margin=dict(t=120, b=80, l=80, r=50)
    )

    # Add annotations
    fig.add_annotation(
        x=0.5,
        y=-0.15,
        xref="paper",
        yref="paper",
        text="<b>Key Finding:</b> Battery investment is not economically viable at any realistic cost level<br>" +
             "Annual losses of 515 NOK mean NPV remains negative even at very low battery costs",
        showarrow=False,
        font=dict(size=12, color='#d32f2f'),
        align="center",
        bgcolor="rgba(255, 235, 235, 0.8)",
        bordercolor="#d32f2f",
        borderwidth=1
    )

    # Save the figure
    html_content = fig.to_html(include_plotlyjs='cdn', config={'displayModeBar': False})

    with open('results/fig7_npv.html', 'w', encoding='utf-8') as f:
        f.write(html_content)

    print("NPV graph updated successfully!")
    print(f"Target NPV (2,500 NOK/kWh): -30,341 NOK")
    print(f"Market NPV (5,000 NOK/kWh): {market_npv:,.0f} NOK")
    print("Saved to: results/fig7_npv.html")

if __name__ == "__main__":
    create_npv_graph()