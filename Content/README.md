# Unreal Content Layout

Create Unreal assets inside the following top-level folders:

```text
Content/
  Core/
    Blueprints/
    Interfaces/
    Data/
  Player/
  Hotel/
    Lobby/
    BOH/
    Rooms/
    Elevators/
  Systems/
    Interaction/
    Dialogue/
    Tasks/
    PMS/
    Phone/
    Radio/
    Save/
  Characters/
  UI/
  Audio/
  Narrative/
    Shift01/
  Maps/
```

## Naming

Initial conventions:

- `BP_` — Blueprint Actor / Object
- `BPI_` — Blueprint Interface
- `WBP_` — UMG Widget
- `DA_` — Data Asset
- `DT_` — Data Table
- `ST_` — Struct
- `E_` — Enum
- `MI_` — Material Instance
- `M_` — Material
- `T_` — Texture
- `SM_` — Static Mesh
- `SK_` — Skeletal Mesh
- `A_` — Audio asset
- `L_` — Level / Map

Do not create hundreds of physical room assets. The 300-room hotel inventory is primarily data-driven.
