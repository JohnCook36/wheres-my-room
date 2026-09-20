# Prototype Data

This directory stores source data that can later be imported into Unreal Data Tables / Data Assets.

## Hotel inventory

`rooms.seed.csv`

Contains exactly **300 active rooms**:

- Floors 2-6
- Wing A: 40 rooms per floor / 200 total
- Wing B: 20 rooms per floor / 100 total

Room 713 is intentionally **not** part of normal active inventory.

## Shift 1 reservations

`reservations.shift01.csv`

Small deterministic dataset for the Hotel Sandbox and Shift 1 prototype.

The dates use symbolic values such as `SHIFT1` because calendar/lore dates are not fixed yet.

## Room 713

`story/room713.prototype.json`

Room 713 is stored as a narrative injection rather than normal hotel inventory.

This is intentional: the PMS can temporarily expose 713 without treating it as one of the hotel's 300 active rooms.

## Import rule

CSV/JSON in this directory is the human-readable source of truth during early prototyping.

When Unreal Data Tables or Data Assets are generated, avoid manually diverging the binary asset from the source data without updating the source file.
