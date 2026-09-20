# Technical Direction v0.1

## Engine

Working choice: **Unreal Engine 5.8**.

## Platform

First target: **PC / Windows**.

## Perspective

First-person narrative adventure.

## Visual direction

**Cinematic stylized realism**:
- realistic proportions;
- believable hotel materials;
- strong lighting and atmosphere;
- no requirement for absolute photorealism.

## Prototype strategy

Blueprint-first.

Use Blueprint initially for:
- interaction;
- doors;
- elevators;
- phone events;
- radio events;
- tasks;
- simple NPC triggers;
- scripted events;
- PMS prototype.

Move systems to C++ only when a stable reusable runtime clearly benefits from it.

## Core systems

- Interaction System
- Hotel State
- Room Data
- Reservation / Guest Data
- PMS
- Task System
- Dialogue System
- Relationship System
- Radio System
- Phone System
- Save System

## First technical milestone

**Hotel Sandbox v0.1**

The player must be able to:
1. launch the game;
2. walk around;
3. interact with objects;
4. open a door;
5. use an elevator;
6. sit at the PMS terminal;
7. find a test reservation;
8. assign a room;
9. make a key;
10. receive a radio task;
11. complete it on a guest floor.
