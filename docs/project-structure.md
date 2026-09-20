# Project Structure

## Unreal Content

Planned top-level structure:

```text
Content/
  Core/
    Blueprints/
    Interfaces/
    Data/
  Player/
  Hotel/
    Rooms/
    Lobby/
    BOH/
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

## First playable maps

- `L_Lobby`
- `L_BOH_01`
- `L_Floor_04`

Later:
- `L_Apartments`
- `L_B1`
- `L_Floor_07`

## Design rule

The full set of 300 hotel rooms exists as **game data**. Only rooms needed for gameplay must exist as fully modeled 3D spaces.

This preserves a believable PMS and hotel inventory without requiring hundreds of physical rooms in the vertical slice.
