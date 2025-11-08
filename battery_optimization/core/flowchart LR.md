flowchart LR
  %% Layout
  %% Left -> center (AC bus) -> right
  classDef bus fill:#000,stroke:#000,stroke-width:1,color:#fff;

  %% Nodes
  Grid([Grid])
  Load([Load])

  Bus["AC bus bar"]
  class Bus bus

  subgraph PV["PV system"]
    direction LR
    PVmod[PV array]
    PVinv[AC inverter]
    PVmod --> PVinv
  end

  subgraph BESS["BESS"]
    direction LR
    Batt[Battery]
    BInv[Bi-dir inverter\nη₍inv₎]
    Batt <-->|P_disch / P_charge| BInv
  end

  %% Connections to the AC bus
  Bus -->|P_load| Load

  PVinv -->|P_pv| Bus

  Grid -->|P_grid,b (buy)| Bus
  Bus -->|P_grid,s (sell)| Grid

  BInv -->|P_disch| Bus
  Bus -->|P_charge| BInv
