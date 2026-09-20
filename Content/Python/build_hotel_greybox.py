import csv
import os
import unreal

EXPECTED_LEVEL = "L_PrototypeEntry"
CUBE_ASSET = "/Engine/BasicShapes/Cube.Cube"
ROOT_FOLDER = "Greybox/Hotel"

# Vertical layout (cm)
LOBBY_FLOOR_Z = 0
GUEST_FLOOR_2_Z = 650
GUEST_FLOOR_STEP = 360
GUEST_CLEAR_HEIGHT = 300

# Guest-floor core aligns with the public elevator area behind the lobby.
CORE_X = -750
CORE_Y = 1100

# Wing A: 40 rooms/floor, 20 door positions, 3 m module, 2 m corridor.
A_MODULES = 20
A_SPACING = 300
A_CORRIDOR_WIDTH = 200
A_ROOM_DEPTH = 700
A_START_X = CORE_X - 450

# Wing B: 20 rooms/floor, 10 door positions, 5 m module, 2.4 m corridor.
B_MODULES = 10
B_SPACING = 500
B_CORRIDOR_WIDTH = 240
B_ROOM_DEPTH = 700
B_START_X = CORE_X + 450

# Old one-room/lobby generator labels that this full generator replaces.
LEGACY_LABELS = {
    "GB_LobbyFloor", "GB_LobbyWall_Back", "GB_LobbyWall_Left", "GB_LobbyWall_Right",
    "GB_LobbyWall_Front_Left", "GB_LobbyWall_Front_Right", "GB_MainEntrance_Header",
    "GB_LobbyWall_Left_South", "GB_LobbyWall_Left_North", "GB_WingA_Header",
    "GB_LobbyWall_Right_South", "GB_LobbyWall_Right_North", "GB_WingB_Header",
    "GB_LobbyWall_Back_Left", "GB_LobbyWall_Back_Right", "GB_BackOfficeDoor_Header",
    "GB_LobbyCeiling", "GB_EntranceColumn_Left", "GB_EntranceColumn_Right",
    "GB_FrontDesk", "GB_FrontDesk_Base", "GB_FrontDesk_Top",
    "GB_FrontDesk_Return_Left", "GB_FrontDesk_Return_Right",
    "GB_Workstation_01", "GB_Workstation_02", "GB_Workstation_03", "GB_Workstation_04",
    "GB_BackOffice_Floor", "GB_BackOffice_Wall_Left", "GB_BackOffice_Wall_Right",
    "GB_BackOffice_Wall_Back", "GB_BackOffice_Wall_Front_Left",
    "GB_BackOffice_Wall_Front_Right", "GB_BackOffice_Wall_Right_South",
    "GB_BackOffice_Wall_Right_North", "GB_BackOffice_Ceiling",
    "GB_BackOffice_Desk_01", "GB_BackOffice_Desk_02", "GB_BackOffice_Cabinet",
    "GB_BOHDoor_Header", "GB_BOH_DoorMarker",
    "GB_Elevator_A1", "GB_Elevator_A2", "GB_Elevator_A1_Header", "GB_Elevator_A2_Header",
    "GB_Sofa_Left", "GB_CoffeeTable_Left", "GB_Sofa_Right", "GB_CoffeeTable_Right",
    "GB_LobbyTable_Center", "GB_BellDesk", "GB_QueueGuide_Left", "GB_QueueGuide_Right",
    "GB_Light_01", "GB_Light_02", "GB_Light_03", "GB_Light_04",
    "GB_Light_05", "GB_Light_06", "GB_Light_BackOffice",
}


def _world():
    return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()


def _ensure_level():
    world = _world()
    if not world:
        raise RuntimeError("No editor world is open.")
    if world.get_name() != EXPECTED_LEVEL:
        raise RuntimeError(
            f"Open {EXPECTED_LEVEL} before running this script. Current level: {world.get_name()}"
        )


def _cube():
    mesh = unreal.EditorAssetLibrary.load_asset(CUBE_ASSET)
    if not mesh:
        raise RuntimeError(f"Could not load {CUBE_ASSET}")
    return mesh


def _folder(floor_name):
    return f"{ROOT_FOLDER}/{floor_name}"


def _spawn_box(subsystem, mesh, label, location, size, folder):
    actor = subsystem.spawn_actor_from_class(
        unreal.StaticMeshActor,
        unreal.Vector(*location),
        unreal.Rotator(0.0, 0.0, 0.0),
    )
    if not actor:
        raise RuntimeError(f"Could not spawn {label}")

    actor.set_actor_label(label)
    try:
        actor.set_folder_path(folder)
    except Exception:
        pass

    component = actor.get_editor_property("static_mesh_component")
    component.set_static_mesh(mesh)

    # Everything generated for greybox stays movable so Unreal never asks us
    # to rebake static lighting every time the generator changes geometry.
    component.set_editor_property("mobility", unreal.ComponentMobility.MOVABLE)

    actor.set_actor_scale3d(
        unreal.Vector(size[0] / 100.0, size[1] / 100.0, size[2] / 100.0)
    )
    return actor


def _spawn_light(subsystem, label, location, folder, intensity=5000.0, radius=1400.0):
    try:
        actor = subsystem.spawn_actor_from_class(
            unreal.PointLight,
            unreal.Vector(*location),
            unreal.Rotator(0.0, 0.0, 0.0),
        )
        if not actor:
            return None
        actor.set_actor_label(label)
        try:
            actor.set_folder_path(folder)
        except Exception:
            pass

        comp = actor.get_editor_property("point_light_component")
        comp.set_editor_property("mobility", unreal.ComponentMobility.MOVABLE)
        comp.set_editor_property("intensity", intensity)
        comp.set_editor_property("attenuation_radius", radius)
        return actor
    except Exception as exc:
        unreal.log_warning(f"Light {label} skipped: {exc}")
        return None


def _delete_old(subsystem):
    deleted = 0
    for actor in subsystem.get_all_level_actors():
        try:
            label = actor.get_actor_label()
        except Exception:
            continue

        if label.startswith("AUTO_HOTEL_") or label in LEGACY_LABELS:
            subsystem.destroy_actor(actor)
            deleted += 1
    return deleted


def _read_rooms():
    path = os.path.join(unreal.Paths.project_dir(), "Data", "rooms.seed.csv")
    if not os.path.exists(path):
        raise RuntimeError(f"Room seed not found: {path}")

    rooms = []
    with open(path, "r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            rooms.append(
                {
                    "number": int(row["RoomNumber"]),
                    "floor": int(row["Floor"]),
                    "wing": row["Wing"].strip(),
                    "type": row["RoomType"].strip(),
                }
            )

    if len(rooms) != 300:
        raise RuntimeError(f"Expected 300 active rooms, found {len(rooms)}")
    return rooms


def _floor_z(floor_number):
    return GUEST_FLOOR_2_Z + (floor_number - 2) * GUEST_FLOOR_STEP


def _build_lobby(subsystem, mesh, created):
    f = _folder("Floor_1_Lobby")

    specs = [
        ("AUTO_HOTEL_Lobby_Floor", (0, 0, 10), (2400, 2200, 20)),
        ("AUTO_HOTEL_Lobby_Front_L", (-700, -1100, 295), (1000, 20, 550)),
        ("AUTO_HOTEL_Lobby_Front_R", (700, -1100, 295), (1000, 20, 550)),
        ("AUTO_HOTEL_Lobby_Entrance_Header", (0, -1100, 505), (400, 20, 130)),
        ("AUTO_HOTEL_Lobby_Left_S", (-1200, -285, 295), (20, 1630, 550)),
        ("AUTO_HOTEL_Lobby_Left_N", (-1200, 935, 295), (20, 330, 550)),
        ("AUTO_HOTEL_Lobby_Right_S", (1200, -285, 295), (20, 1630, 550)),
        ("AUTO_HOTEL_Lobby_Right_N", (1200, 935, 295), (20, 330, 550)),
        ("AUTO_HOTEL_Lobby_Back_L", (-630, 1100, 295), (1140, 20, 550)),
        ("AUTO_HOTEL_Lobby_Back_R", (630, 1100, 295), (1140, 20, 550)),
        ("AUTO_HOTEL_Lobby_Ceiling", (0, 0, 580), (2400, 2200, 20)),
        ("AUTO_HOTEL_Entrance_Column_L", (-450, -780, 295), (50, 50, 550)),
        ("AUTO_HOTEL_Entrance_Column_R", (450, -780, 295), (50, 50, 550)),

        # Front Desk
        ("AUTO_HOTEL_FrontDesk_Base", (0, 650, 72.5), (800, 80, 105)),
        ("AUTO_HOTEL_FrontDesk_Top", (0, 650, 130), (820, 100, 10)),
        ("AUTO_HOTEL_FrontDesk_Return_L", (-405, 735, 72.5), (10, 170, 105)),
        ("AUTO_HOTEL_FrontDesk_Return_R", (405, 735, 72.5), (10, 170, 105)),

        # Back Office
        ("AUTO_HOTEL_BackOffice_Floor", (0, 1400, 10), (800, 600, 20)),
        ("AUTO_HOTEL_BackOffice_Wall_L", (-400, 1400, 170), (20, 600, 300)),
        ("AUTO_HOTEL_BackOffice_Wall_Back", (0, 1700, 170), (800, 20, 300)),
        ("AUTO_HOTEL_BackOffice_Wall_R_S", (400, 1250, 170), (20, 300, 300)),
        ("AUTO_HOTEL_BackOffice_Wall_R_N", (400, 1600, 170), (20, 200, 300)),
        ("AUTO_HOTEL_BackOffice_Ceiling", (0, 1400, 330), (800, 600, 20)),

        # Lobby furniture scale references
        ("AUTO_HOTEL_Sofa_L", (-650, -350, 60), (300, 85, 80)),
        ("AUTO_HOTEL_Table_L", (-650, -120, 40), (140, 70, 40)),
        ("AUTO_HOTEL_Sofa_R", (650, -350, 60), (300, 85, 80)),
        ("AUTO_HOTEL_Table_R", (650, -120, 40), (140, 70, 40)),
        ("AUTO_HOTEL_BellDesk", (850, -750, 65), (220, 70, 90)),

        # Public elevator markers on the rear-left wall.
        ("AUTO_HOTEL_L1_Elevator_A1", (-850, 1085, 140), (180, 20, 240)),
        ("AUTO_HOTEL_L1_Elevator_A2", (-620, 1085, 140), (180, 20, 240)),
        # Service elevator S2 and staff stair C markers.
        ("AUTO_HOTEL_L1_Service_S2", (-300, 1685, 140), (120, 20, 240)),
        ("AUTO_HOTEL_L1_Stair_C", (300, 1685, 140), (120, 20, 240)),
    ]

    for spec in specs:
        created.append(_spawn_box(subsystem, mesh, *spec, f))

    for i, x in enumerate((-700, 0, 700), start=1):
        light = _spawn_light(
            subsystem,
            f"AUTO_HOTEL_Lobby_Light_{i}",
            (x, -250, 500),
            f,
            6500.0,
            1200.0,
        )
        if light:
            created.append(light)


def _wall_split_for_door(subsystem, mesh, floor, z, wall_y, corridor_start, corridor_end, door_x, folder, created):
    # Creates two long inner-wall pieces leaving a 120 cm opening for Room 426.
    gap_half = 60
    lo = min(corridor_start, corridor_end)
    hi = max(corridor_start, corridor_end)

    left_end = door_x - gap_half
    right_start = door_x + gap_half

    if left_end > lo:
        length = left_end - lo
        created.append(_spawn_box(
            subsystem, mesh,
            f"AUTO_HOTEL_F{floor}_A_InnerWall_426_A",
            ((lo + left_end) / 2, wall_y, z + 160),
            (length, 20, 300),
            folder,
        ))

    if hi > right_start:
        length = hi - right_start
        created.append(_spawn_box(
            subsystem, mesh,
            f"AUTO_HOTEL_F{floor}_A_InnerWall_426_B",
            ((right_start + hi) / 2, wall_y, z + 160),
            (length, 20, 300),
            folder,
        ))


def _build_guest_floor(subsystem, mesh, floor, floor_rooms, created):
    z = _floor_z(floor)
    folder = _folder(f"Floor_{floor}")

    a_rooms = sorted([r for r in floor_rooms if r["wing"] == "A"], key=lambda r: r["number"])
    b_rooms = sorted([r for r in floor_rooms if r["wing"] == "B"], key=lambda r: r["number"])

    if len(a_rooms) != 40 or len(b_rooms) != 20:
        raise RuntimeError(
            f"Floor {floor}: expected 40 A rooms and 20 B rooms, "
            f"found {len(a_rooms)} A / {len(b_rooms)} B"
        )

    # Central elevator / stair core.
    core_specs = [
        (f"AUTO_HOTEL_F{floor}_Core_Floor", (CORE_X, CORE_Y, z + 10), (900, 900, 20)),
        (f"AUTO_HOTEL_F{floor}_Core_Ceiling", (CORE_X, CORE_Y, z + 320), (900, 900, 20)),
        (f"AUTO_HOTEL_F{floor}_Elevator_A1", (CORE_X - 170, CORE_Y - 430, z + 120), (140, 20, 220)),
        (f"AUTO_HOTEL_F{floor}_Elevator_A2", (CORE_X + 20, CORE_Y - 430, z + 120), (140, 20, 220)),
        (f"AUTO_HOTEL_F{floor}_Service_S2", (CORE_X + 230, CORE_Y + 430, z + 120), (120, 20, 220)),
        (f"AUTO_HOTEL_F{floor}_Stair_C", (CORE_X - 260, CORE_Y + 430, z + 120), (120, 20, 220)),
    ]
    for spec in core_specs:
        created.append(_spawn_box(subsystem, mesh, *spec, folder))

    # ---------------- Wing A ----------------
    a_length = A_MODULES * A_SPACING + 300
    a_center_x = A_START_X - a_length / 2
    a_end_x = A_START_X - a_length

    created.append(_spawn_box(
        subsystem, mesh, f"AUTO_HOTEL_F{floor}_A_Corridor_Floor",
        (a_center_x, CORE_Y, z + 10), (a_length, A_CORRIDOR_WIDTH, 20), folder
    ))
    created.append(_spawn_box(
        subsystem, mesh, f"AUTO_HOTEL_F{floor}_A_Corridor_Ceiling",
        (a_center_x, CORE_Y, z + 320), (a_length, A_CORRIDOR_WIDTH, 20), folder
    ))

    north_y = CORE_Y + A_CORRIDOR_WIDTH / 2
    south_y = CORE_Y - A_CORRIDOR_WIDTH / 2
    outer_north_y = north_y + A_ROOM_DEPTH
    outer_south_y = south_y - A_ROOM_DEPTH

    # Room-row slabs and exterior walls.
    for side_name, room_y, outer_y in (
        ("N", north_y + A_ROOM_DEPTH / 2, outer_north_y),
        ("S", south_y - A_ROOM_DEPTH / 2, outer_south_y),
    ):
        created.append(_spawn_box(
            subsystem, mesh, f"AUTO_HOTEL_F{floor}_A_RoomRow_{side_name}_Floor",
            (a_center_x, room_y, z + 10), (a_length, A_ROOM_DEPTH, 20), folder
        ))
        created.append(_spawn_box(
            subsystem, mesh, f"AUTO_HOTEL_F{floor}_A_OuterWall_{side_name}",
            (a_center_x, outer_y, z + 160), (a_length, 20, 300), folder
        ))

    # Inner corridor walls. Floor 4 north side leaves a real opening for 426.
    room_426_x = None
    if floor == 4:
        for idx, room in enumerate(a_rooms):
            if room["number"] == 426:
                module = idx // 2
                room_426_x = A_START_X - (module + 0.5) * A_SPACING
                break

    created.append(_spawn_box(
        subsystem, mesh, f"AUTO_HOTEL_F{floor}_A_InnerWall_S",
        (a_center_x, south_y, z + 160), (a_length, 20, 300), folder
    ))

    if floor == 4 and room_426_x is not None:
        _wall_split_for_door(
            subsystem, mesh, floor, z, north_y,
            a_end_x, A_START_X, room_426_x, folder, created
        )
    else:
        created.append(_spawn_box(
            subsystem, mesh, f"AUTO_HOTEL_F{floor}_A_InnerWall_N",
            (a_center_x, north_y, z + 160), (a_length, 20, 300), folder
        ))

    created.append(_spawn_box(
        subsystem, mesh, f"AUTO_HOTEL_F{floor}_A_EndWall",
        (a_end_x, CORE_Y, z + 160),
        (20, A_CORRIDOR_WIDTH + A_ROOM_DEPTH * 2, 300), folder
    ))

    # 40 actual room doors from rooms.seed.csv, paired along the corridor.
    for idx, room in enumerate(a_rooms):
        module = idx // 2
        side_north = (idx % 2) == 1
        door_x = A_START_X - (module + 0.5) * A_SPACING
        door_y = north_y - 8 if side_north else south_y + 8

        if room["number"] == 426:
            # Real doorway instead of a blocking door slab.
            created.append(_spawn_box(
                subsystem, mesh, "AUTO_HOTEL_Room_426_Header",
                (door_x, north_y, z + 270), (120, 20, 80), folder
            ))
            created.append(_spawn_box(
                subsystem, mesh, "AUTO_HOTEL_Room_426_Jamb_L",
                (door_x - 70, north_y, z + 120), (20, 20, 220), folder
            ))
            created.append(_spawn_box(
                subsystem, mesh, "AUTO_HOTEL_Room_426_Jamb_R",
                (door_x + 70, north_y, z + 120), (20, 20, 220), folder
            ))

            # Simple accessible Room 426 interior.
            room_center_y = north_y + A_ROOM_DEPTH / 2
            created.append(_spawn_box(
                subsystem, mesh, "AUTO_HOTEL_Room_426_Partition_L",
                (door_x - 150, room_center_y, z + 160), (20, A_ROOM_DEPTH, 300), folder
            ))
            created.append(_spawn_box(
                subsystem, mesh, "AUTO_HOTEL_Room_426_Partition_R",
                (door_x + 150, room_center_y, z + 160), (20, A_ROOM_DEPTH, 300), folder
            ))
            created.append(_spawn_box(
                subsystem, mesh, "AUTO_HOTEL_Room_426_Ceiling",
                (door_x, room_center_y, z + 320), (300, A_ROOM_DEPTH, 20), folder
            ))
        else:
            created.append(_spawn_box(
                subsystem, mesh,
                f"AUTO_HOTEL_RoomDoor_{room['number']}",
                (door_x, door_y, z + 120), (105, 16, 220), folder
            ))

    # ---------------- Wing B ----------------
    b_length = B_MODULES * B_SPACING + 500
    b_center_x = B_START_X + b_length / 2
    b_end_x = B_START_X + b_length

    created.append(_spawn_box(
        subsystem, mesh, f"AUTO_HOTEL_F{floor}_B_Corridor_Floor",
        (b_center_x, CORE_Y, z + 10), (b_length, B_CORRIDOR_WIDTH, 20), folder
    ))
    created.append(_spawn_box(
        subsystem, mesh, f"AUTO_HOTEL_F{floor}_B_Corridor_Ceiling",
        (b_center_x, CORE_Y, z + 320), (b_length, B_CORRIDOR_WIDTH, 20), folder
    ))

    b_north_y = CORE_Y + B_CORRIDOR_WIDTH / 2
    b_south_y = CORE_Y - B_CORRIDOR_WIDTH / 2
    b_outer_north_y = b_north_y + B_ROOM_DEPTH
    b_outer_south_y = b_south_y - B_ROOM_DEPTH

    for side_name, room_y, outer_y in (
        ("N", b_north_y + B_ROOM_DEPTH / 2, b_outer_north_y),
        ("S", b_south_y - B_ROOM_DEPTH / 2, b_outer_south_y),
    ):
        created.append(_spawn_box(
            subsystem, mesh, f"AUTO_HOTEL_F{floor}_B_RoomRow_{side_name}_Floor",
            (b_center_x, room_y, z + 10), (b_length, B_ROOM_DEPTH, 20), folder
        ))
        created.append(_spawn_box(
            subsystem, mesh, f"AUTO_HOTEL_F{floor}_B_OuterWall_{side_name}",
            (b_center_x, outer_y, z + 160), (b_length, 20, 300), folder
        ))

    created.append(_spawn_box(
        subsystem, mesh, f"AUTO_HOTEL_F{floor}_B_InnerWall_N",
        (b_center_x, b_north_y, z + 160), (b_length, 20, 300), folder
    ))
    created.append(_spawn_box(
        subsystem, mesh, f"AUTO_HOTEL_F{floor}_B_InnerWall_S",
        (b_center_x, b_south_y, z + 160), (b_length, 20, 300), folder
    ))
    created.append(_spawn_box(
        subsystem, mesh, f"AUTO_HOTEL_F{floor}_B_EndWall",
        (b_end_x, CORE_Y, z + 160),
        (20, B_CORRIDOR_WIDTH + B_ROOM_DEPTH * 2, 300), folder
    ))

    for idx, room in enumerate(b_rooms):
        module = idx // 2
        side_north = (idx % 2) == 1
        door_x = B_START_X + (module + 0.5) * B_SPACING
        door_y = b_north_y - 8 if side_north else b_south_y + 8

        created.append(_spawn_box(
            subsystem, mesh,
            f"AUTO_HOTEL_RoomDoor_{room['number']}",
            (door_x, door_y, z + 120), (110, 16, 220), folder
        ))

    # Movable corridor preview lights.
    for idx, x in enumerate(
        (A_START_X - 1200, A_START_X - 3000, A_START_X - 4800), start=1
    ):
        light = _spawn_light(
            subsystem, f"AUTO_HOTEL_F{floor}_A_Light_{idx}",
            (x, CORE_Y, z + 270), folder
        )
        if light:
            created.append(light)

    for idx, x in enumerate((B_START_X + 1400, B_START_X + 3600), start=1):
        light = _spawn_light(
            subsystem, f"AUTO_HOTEL_F{floor}_B_Light_{idx}",
            (x, CORE_Y, z + 270), folder
        )
        if light:
            created.append(light)

    core_light = _spawn_light(
        subsystem, f"AUTO_HOTEL_F{floor}_Core_Light",
        (CORE_X, CORE_Y, z + 270), folder
    )
    if core_light:
        created.append(core_light)


def _build_seventh_floor(subsystem, mesh, created):
    floor = 7
    z = _floor_z(floor)
    folder = _folder("Floor_7_Closed")

    # Old closed floor: shorter, simpler, clearly separate from active inventory.
    modules = 8
    spacing = 350
    corridor_width = 190
    room_depth = 650
    start_x = CORE_X - 450
    length = modules * spacing + 350
    center_x = start_x - length / 2
    end_x = start_x - length

    specs = [
        ("AUTO_HOTEL_F7_Core_Floor", (CORE_X, CORE_Y, z + 10), (900, 900, 20)),
        ("AUTO_HOTEL_F7_Core_Ceiling", (CORE_X, CORE_Y, z + 320), (900, 900, 20)),
        # No normal guest-elevator door on 7. Only service S2 and staff stair C reach it.
        ("AUTO_HOTEL_F7_Service_S2", (CORE_X + 230, CORE_Y + 430, z + 120), (120, 20, 220)),
        ("AUTO_HOTEL_F7_Stair_C", (CORE_X - 260, CORE_Y + 430, z + 120), (120, 20, 220)),
        ("AUTO_HOTEL_F7_Corridor_Floor", (center_x, CORE_Y, z + 10), (length, corridor_width, 20)),
        ("AUTO_HOTEL_F7_Corridor_Ceiling", (center_x, CORE_Y, z + 320), (length, corridor_width, 20)),
        ("AUTO_HOTEL_F7_InnerWall_N", (center_x, CORE_Y + corridor_width / 2, z + 160), (length, 20, 300)),
        ("AUTO_HOTEL_F7_InnerWall_S", (center_x, CORE_Y - corridor_width / 2, z + 160), (length, 20, 300)),
        ("AUTO_HOTEL_F7_OuterWall_N", (center_x, CORE_Y + corridor_width / 2 + room_depth, z + 160), (length, 20, 300)),
        ("AUTO_HOTEL_F7_OuterWall_S", (center_x, CORE_Y - corridor_width / 2 - room_depth, z + 160), (length, 20, 300)),
        ("AUTO_HOTEL_F7_EndWall", (end_x, CORE_Y, z + 160), (20, corridor_width + room_depth * 2, 300)),
    ]
    for spec in specs:
        created.append(_spawn_box(subsystem, mesh, *spec, folder))

    # 701–708 on south side, 709–716 on north side.
    # This places 713 around the middle of the corridor instead of at the far end.
    for number in range(701, 717):
        if number <= 708:
            module = number - 701
            door_y = CORE_Y - corridor_width / 2 + 8
        else:
            module = number - 709
            door_y = CORE_Y + corridor_width / 2 - 8

        door_x = start_x - (module + 0.5) * spacing
        label = (
            "AUTO_HOTEL_Room713_Door"
            if number == 713
            else f"AUTO_HOTEL_RoomDoor_{number}"
        )
        created.append(_spawn_box(
            subsystem, mesh, label,
            (door_x, door_y, z + 120), (105, 16, 220), folder
        ))

    for idx, x in enumerate((start_x - 800, start_x - 1800, start_x - 2800), start=1):
        light = _spawn_light(
            subsystem, f"AUTO_HOTEL_F7_Light_{idx}",
            (x, CORE_Y, z + 270), folder,
            3500.0, 1100.0
        )
        if light:
            created.append(light)


def build_hotel():
    _ensure_level()
    subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    mesh = _cube()
    rooms = _read_rooms()

    by_floor = {}
    for room in rooms:
        by_floor.setdefault(room["floor"], []).append(room)

    with unreal.ScopedEditorTransaction("Build complete Where's My Room hotel greybox"):
        deleted = _delete_old(subsystem)
        created = []

        _build_lobby(subsystem, mesh, created)

        for floor in range(2, 7):
            _build_guest_floor(subsystem, mesh, floor, by_floor.get(floor, []), created)

        _build_seventh_floor(subsystem, mesh, created)

    unreal.log(
        f"Where's My Room: removed {deleted} previous generated actors and "
        f"created {len(created)} hotel greybox actors."
    )
    unreal.log(
        "Built: lobby, Front Desk, Back Office, floors 2–6, Wing A, Wing B, "
        "300 active-room door markers from rooms.seed.csv, Room 426 interior, "
        "service S2, stair C, and closed floor 7 with rooms 701–716 / Room 713."
    )
    unreal.log(
        "This is navigation greybox, not 300 furnished interiors. "
        "Save L_PrototypeEntry only after walking the layout in Play mode."
    )

    try:
        subsystem.set_selected_level_actors([])
    except Exception:
        pass


build_hotel()
