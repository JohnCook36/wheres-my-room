#!/usr/bin/env python3
import csv
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROOMS = ROOT / "Data" / "rooms.seed.csv"
RESERVATIONS = ROOT / "Data" / "reservations.shift01.csv"
ROOM_713 = ROOT / "Data" / "story" / "room713.prototype.json"


def fail(message: str) -> None:
    raise SystemExit(f"VALIDATION FAILED: {message}")


with ROOMS.open(encoding="utf-8", newline="") as f:
    rooms = list(csv.DictReader(f))

if len(rooms) != 300:
    fail(f"expected 300 active rooms, found {len(rooms)}")

numbers = [int(row["RoomNumber"]) for row in rooms]
if len(numbers) != len(set(numbers)):
    fail("duplicate room numbers found")

if 713 in numbers:
    fail("Room 713 must not exist in normal active inventory")

floors = Counter(int(row["Floor"]) for row in rooms)
if floors != Counter({2: 60, 3: 60, 4: 60, 5: 60, 6: 60}):
    fail(f"unexpected floor distribution: {dict(floors)}")

wings = Counter(row["Wing"] for row in rooms)
if wings != Counter({"A": 200, "B": 100}):
    fail(f"unexpected wing distribution: {dict(wings)}")

expected_types = Counter({
    "Standard": 160,
    "Corner": 20,
    "SuperiorCorner": 15,
    "CornerPremium": 5,
    "Apartment": 60,
    "SuperiorApartmentBalcony": 25,
    "TwoRoomApartment": 15,
})
room_types = Counter(row["RoomType"] for row in rooms)
if room_types != expected_types:
    fail(f"unexpected room type distribution: {dict(room_types)}")

for row in rooms:
    number = int(row["RoomNumber"])
    floor = int(row["Floor"])
    if number // 100 != floor:
        fail(f"room {number} does not match floor {floor}")

with RESERVATIONS.open(encoding="utf-8", newline="") as f:
    reservations = list(csv.DictReader(f))

known_rooms = set(numbers)
for row in reservations:
    assigned = row["AssignedRoom"].strip()
    if assigned and int(assigned) not in known_rooms:
        fail(
            f"reservation {row['ReservationId']} references unknown room {assigned}"
        )

with ROOM_713.open(encoding="utf-8") as f:
    story_room = json.load(f)

if story_room.get("roomNumber") != 713:
    fail("Room 713 story data must use roomNumber 713")

if story_room.get("normalInventory") is not False:
    fail("Room 713 must have normalInventory=false")

if story_room.get("defaultVisibleInPms") is not False:
    fail("Room 713 must not be visible in PMS by default")

print(
    "OK:",
    f"{len(rooms)} active rooms,",
    f"{len(reservations)} Shift 1 reservations,",
    "Room 713 isolated from normal inventory",
)
