# Hotel Sandbox v0.1

## Purpose

Build the smallest playable technical loop before implementing the full Shift 1 script.

## Player can

1. launch into the prototype map;
2. walk and look around;
3. focus an interactable object;
4. open a door;
5. use an elevator control;
6. interact with a PMS terminal;
7. find one test reservation;
8. assign a room;
9. issue a key;
10. receive one radio task;
11. walk to a guest-floor objective;
12. complete the task;
13. return to Front Office.

## Physical greybox scope

Only build:

- partial lobby;
- Front Desk;
- Back Office;
- Guest Elevator A;
- Floor 4 playable slice;
- Room 426 exterior;
- BOH shortcut;
- Service Elevator S2 area.

Do not build all 300 rooms.

## Systems required

### Interaction
One reusable interaction contract for doors, buttons, terminals, phones, NPCs, and room locks.

### Room data
At minimum:
- room number;
- floor;
- wing;
- room type;
- housekeeping state;
- occupancy state;
- maintenance state;
- DND;
- story flags.

### Reservation data
At minimum:
- guest id;
- guest name;
- arrival;
- departure;
- booked category;
- assigned room;
- notes.

### PMS prototype
Only:
- reservation search;
- arrivals;
- in-house list;
- room assignment;
- check-in;
- key action.

### Task prototype
One task:
`CHECK_GUEST_426`

### Radio prototype
One scripted call that creates the task.

## Definition of Done

The milestone is complete when the full loop can be played without developer commands and without opening the Unreal Editor during play.

No final art, voice acting, save system, relationship system, or supernatural effects are required for this milestone.
