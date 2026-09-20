import os
import unreal

EXPECTED_LEVEL = "L_PrototypeEntry"
ROOT_FOLDER = "Greybox/Exterior"
CUBE_ASSET = "/Engine/BasicShapes/Cube.Cube"
MATERIAL_PATH = "/Game/Generated/Materials"

# Must match the interior generator.
CORE_X = -750
CORE_Y = 1100
GUEST_FLOOR_2_Z = 650
GUEST_FLOOR_STEP = 360

A_START_X = CORE_X - 450
A_LENGTH = 20 * 300 + 300
A_CENTER_X = A_START_X - A_LENGTH / 2
A_END_X = A_START_X - A_LENGTH

B_START_X = CORE_X + 450
B_LENGTH = 10 * 500 + 500
B_CENTER_X = B_START_X + B_LENGTH / 2
B_END_X = B_START_X + B_LENGTH

SOUTH_FACE_Y = 290
NORTH_FACE_Y = 1930

MATERIAL_SPECS = {
    "M_EXT_WarmStone": ((0.42, 0.38, 0.31), 0.72, 0.0),
    "M_EXT_LightStone": ((0.68, 0.65, 0.58), 0.78, 0.0),
    "M_EXT_DarkGlass": ((0.035, 0.07, 0.095), 0.10, 0.05),
    "M_EXT_Metal": ((0.09, 0.10, 0.11), 0.28, 0.70),
    "M_EXT_Asphalt": ((0.045, 0.047, 0.05), 0.92, 0.0),
    "M_EXT_Paving": ((0.32, 0.31, 0.29), 0.83, 0.0),
    "M_EXT_Green": ((0.07, 0.20, 0.08), 0.80, 0.0),
    "M_EXT_Roof": ((0.12, 0.12, 0.13), 0.88, 0.0),
}


def _ensure_level():
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    if not world:
        raise RuntimeError("No editor world is open.")
    if world.get_name() != EXPECTED_LEVEL:
        raise RuntimeError(
            f"Open {EXPECTED_LEVEL} first. Current level: {world.get_name()}"
        )


def _cube():
    mesh = unreal.EditorAssetLibrary.load_asset(CUBE_ASSET)
    if not mesh:
        raise RuntimeError(f"Could not load {CUBE_ASSET}")
    return mesh


def _ensure_material_folder():
    try:
        unreal.EditorAssetLibrary.make_directory(MATERIAL_PATH)
    except Exception:
        pass


def _get_or_create_material(name, color, roughness, metallic):
    path = f"{MATERIAL_PATH}/{name}"
    existing = unreal.EditorAssetLibrary.load_asset(path)
    if existing:
        return existing

    try:
        tools = unreal.AssetToolsHelpers.get_asset_tools()
        material = tools.create_asset(
            name,
            MATERIAL_PATH,
            unreal.Material,
            unreal.MaterialFactoryNew(),
        )
        if not material:
            return None

        color_expr = unreal.MaterialEditingLibrary.create_material_expression(
            material, unreal.MaterialExpressionConstant3Vector, -450, -40
        )
        color_expr.set_editor_property(
            "constant", unreal.LinearColor(color[0], color[1], color[2], 1.0)
        )
        unreal.MaterialEditingLibrary.connect_material_property(
            color_expr, "", unreal.MaterialProperty.MP_BASE_COLOR
        )

        rough_expr = unreal.MaterialEditingLibrary.create_material_expression(
            material, unreal.MaterialExpressionConstant, -450, 80
        )
        rough_expr.set_editor_property("r", roughness)
        unreal.MaterialEditingLibrary.connect_material_property(
            rough_expr, "", unreal.MaterialProperty.MP_ROUGHNESS
        )

        metal_expr = unreal.MaterialEditingLibrary.create_material_expression(
            material, unreal.MaterialExpressionConstant, -450, 180
        )
        metal_expr.set_editor_property("r", metallic)
        unreal.MaterialEditingLibrary.connect_material_property(
            metal_expr, "", unreal.MaterialProperty.MP_METALLIC
        )

        unreal.MaterialEditingLibrary.recompile_material(material)
        unreal.EditorAssetLibrary.save_loaded_asset(material)
        return material
    except Exception as exc:
        unreal.log_warning(f"Could not create material {name}: {exc}")
        return None


def _materials():
    _ensure_material_folder()
    result = {}
    for name, spec in MATERIAL_SPECS.items():
        result[name] = _get_or_create_material(name, *spec)
    return result


def _spawn_box(subsystem, mesh, label, location, size, material, folder=ROOT_FOLDER):
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
    component.set_editor_property("mobility", unreal.ComponentMobility.MOVABLE)
    if material:
        component.set_material(0, material)

    actor.set_actor_scale3d(
        unreal.Vector(size[0] / 100.0, size[1] / 100.0, size[2] / 100.0)
    )
    return actor


def _delete_previous(subsystem):
    deleted = 0
    for actor in subsystem.get_all_level_actors():
        try:
            label = actor.get_actor_label()
        except Exception:
            continue
        if label.startswith("AUTO_EXT_"):
            subsystem.destroy_actor(actor)
            deleted += 1
    return deleted


def _floor_z(floor):
    return GUEST_FLOOR_2_Z + (floor - 2) * GUEST_FLOOR_STEP


def _build_ground_front(subsystem, mesh, m, created):
    f = f"{ROOT_FOLDER}/Ground"

    # Podium cladding around the lobby: architectural skin placed just outside
    # the collision greybox made by build_hotel_greybox.py.
    for label, loc, size, mat in [
        ("AUTO_EXT_LobbyPlinth", (0, -1118, 95), (2400, 16, 170), m["M_EXT_WarmStone"]),
        ("AUTO_EXT_LobbyTopBand", (0, -1118, 515), (2400, 24, 90), m["M_EXT_LightStone"]),
        ("AUTO_EXT_EntranceCanopy", (0, -1400, 410), (1000, 560, 28), m["M_EXT_Metal"]),
        ("AUTO_EXT_CanopyColumn_L", (-420, -1510, 210), (38, 38, 400), m["M_EXT_Metal"]),
        ("AUTO_EXT_CanopyColumn_R", (420, -1510, 210), (38, 38, 400), m["M_EXT_Metal"]),
        ("AUTO_EXT_EntryPaving", (0, -1370, 5), (2500, 520, 10), m["M_EXT_Paving"]),
        ("AUTO_EXT_DropoffRoad", (0, -1980, 2), (3600, 700, 8), m["M_EXT_Asphalt"]),
        ("AUTO_EXT_Curb_L", (-1260, -1560, 15), (40, 900, 30), m["M_EXT_LightStone"]),
        ("AUTO_EXT_Curb_R", (1260, -1560, 15), (40, 900, 30), m["M_EXT_LightStone"]),
        ("AUTO_EXT_HotelSignSlab", (950, -1135, 300), (320, 26, 220), m["M_EXT_Metal"]),
    ]:
        created.append(_spawn_box(subsystem, mesh, label, loc, size, mat, f))

    # Glazed ground-floor façade. Leave the central 3 m opening for doors.
    x_positions = (-950, -700, -450, 450, 700, 950)
    for i, x in enumerate(x_positions, 1):
        created.append(_spawn_box(
            subsystem, mesh,
            f"AUTO_EXT_LobbyGlass_{i:02d}",
            (x, -1129, 300), (220, 10, 360),
            m["M_EXT_DarkGlass"], f
        ))

    # Entrance doors as dark glass panels.
    created.append(_spawn_box(
        subsystem, mesh, "AUTO_EXT_EntranceDoor_L",
        (-80, -1132, 180), (140, 8, 320), m["M_EXT_DarkGlass"], f
    ))
    created.append(_spawn_box(
        subsystem, mesh, "AUTO_EXT_EntranceDoor_R",
        (80, -1132, 180), (140, 8, 320), m["M_EXT_DarkGlass"], f
    ))

    # Planters make the entrance read as a hotel rather than a warehouse.
    for side, x in (("L", -760), ("R", 760)):
        created.append(_spawn_box(
            subsystem, mesh, f"AUTO_EXT_Planter_{side}",
            (x, -1360, 55), (230, 90, 90), m["M_EXT_WarmStone"], f
        ))
        created.append(_spawn_box(
            subsystem, mesh, f"AUTO_EXT_PlanterGreen_{side}",
            (x, -1360, 120), (200, 65, 70), m["M_EXT_Green"], f
        ))


def _build_wing_shell(subsystem, mesh, m, created, wing, center_x, length, start_x, modules, spacing):
    f = f"{ROOT_FOLDER}/GuestWings"

    # Continuous stone façade backing, front and rear.
    active_bottom = GUEST_FLOOR_2_Z
    active_top = _floor_z(6) + 330
    height = active_top - active_bottom
    center_z = active_bottom + height / 2

    created.append(_spawn_box(
        subsystem, mesh, f"AUTO_EXT_Wing{wing}_Facade_S",
        (center_x, SOUTH_FACE_Y, center_z), (length, 24, height),
        m["M_EXT_WarmStone"], f
    ))
    created.append(_spawn_box(
        subsystem, mesh, f"AUTO_EXT_Wing{wing}_Facade_N",
        (center_x, NORTH_FACE_Y, center_z), (length, 24, height),
        m["M_EXT_WarmStone"], f
    ))

    # Roof cap and parapets.
    roof_z = active_top + 10
    created.append(_spawn_box(
        subsystem, mesh, f"AUTO_EXT_Wing{wing}_Roof",
        (center_x, CORE_Y, roof_z),
        (length, NORTH_FACE_Y - SOUTH_FACE_Y, 20),
        m["M_EXT_Roof"], f
    ))
    created.append(_spawn_box(
        subsystem, mesh, f"AUTO_EXT_Wing{wing}_Parapet_S",
        (center_x, SOUTH_FACE_Y, roof_z + 50), (length, 28, 100),
        m["M_EXT_LightStone"], f
    ))
    created.append(_spawn_box(
        subsystem, mesh, f"AUTO_EXT_Wing{wing}_Parapet_N",
        (center_x, NORTH_FACE_Y, roof_z + 50), (length, 28, 100),
        m["M_EXT_LightStone"], f
    ))

    # Floor bands create a believable hotel façade rhythm.
    for floor in range(2, 7):
        band_z = _floor_z(floor) + 320
        for face, y in (("S", SOUTH_FACE_Y - 16), ("N", NORTH_FACE_Y + 16)):
            created.append(_spawn_box(
                subsystem, mesh,
                f"AUTO_EXT_Wing{wing}_Band_F{floor}_{face}",
                (center_x, y, band_z), (length, 18, 32),
                m["M_EXT_LightStone"], f
            ))

    # One exterior window per room on each side: 20+20 for A, 10+10 for B.
    # This makes the 300-room inventory visible in the massing.
    for floor in range(2, 7):
        z = _floor_z(floor) + 185
        for module in range(modules):
            if wing == "A":
                x = start_x - (module + 0.5) * spacing
                south_room = floor * 100 + module * 2 + 1
                north_room = floor * 100 + module * 2 + 2
            else:
                x = start_x + (module + 0.5) * spacing
                south_room = floor * 100 + 51 + module * 2
                north_room = floor * 100 + 52 + module * 2

            for face, y, room_no in (
                ("S", SOUTH_FACE_Y - 22, south_room),
                ("N", NORTH_FACE_Y + 22, north_room),
            ):
                created.append(_spawn_box(
                    subsystem, mesh,
                    f"AUTO_EXT_Window_{room_no}_{face}",
                    (x, y, z), (185 if wing == "A" else 260, 10, 155),
                    m["M_EXT_DarkGlass"], f
                ))

    # End wall closes the visible massing.
    end_x = start_x - length if wing == "A" else start_x + length
    created.append(_spawn_box(
        subsystem, mesh, f"AUTO_EXT_Wing{wing}_EndWall",
        (end_x, CORE_Y, center_z),
        (26, NORTH_FACE_Y - SOUTH_FACE_Y, height),
        m["M_EXT_WarmStone"], f
    ))


def _build_core(subsystem, mesh, m, created):
    f = f"{ROOT_FOLDER}/Core"
    bottom = GUEST_FLOOR_2_Z
    top = _floor_z(6) + 330
    height = top - bottom
    center_z = bottom + height / 2

    # Central vertical core between the two room wings.
    created.append(_spawn_box(
        subsystem, mesh, "AUTO_EXT_Core_Front",
        (CORE_X, 635, center_z), (900, 30, height),
        m["M_EXT_LightStone"], f
    ))
    created.append(_spawn_box(
        subsystem, mesh, "AUTO_EXT_Core_Back",
        (CORE_X, 1565, center_z), (900, 30, height),
        m["M_EXT_LightStone"], f
    ))

    # Narrow vertical glass stripe hints at lift/stair circulation.
    created.append(_spawn_box(
        subsystem, mesh, "AUTO_EXT_Core_GlassStripe",
        (CORE_X, 615, center_z), (230, 10, height - 120),
        m["M_EXT_DarkGlass"], f
    ))


def _build_seventh_floor(subsystem, mesh, m, created):
    f = f"{ROOT_FOLDER}/ClosedFloor7"
    z = _floor_z(7)

    # Closed historic floor is real but set back from the main façade so it does
    # not read as a normal guest floor from the entrance.
    start_x = CORE_X - 450
    length = 8 * 350 + 350
    center_x = start_x - length / 2
    south = 430
    north = 1770
    height = 320
    center_z = z + 160

    for label, loc, size in [
        ("AUTO_EXT_F7_SouthWall", (center_x, south, center_z), (length, 24, height)),
        ("AUTO_EXT_F7_NorthWall", (center_x, north, center_z), (length, 24, height)),
        ("AUTO_EXT_F7_EndWall", (start_x - length, CORE_Y, center_z), (24, north - south, height)),
        ("AUTO_EXT_F7_Roof", (center_x, CORE_Y, z + 330), (length, north - south, 20)),
        ("AUTO_EXT_F7_Parapet_S", (center_x, south, z + 385), (length, 28, 110)),
        ("AUTO_EXT_F7_Parapet_N", (center_x, north, z + 385), (length, 28, 110)),
    ]:
        created.append(_spawn_box(
            subsystem, mesh, label, loc, size,
            m["M_EXT_LightStone"] if "Roof" not in label else m["M_EXT_Roof"], f
        ))

    # 701–716 exterior windows; Room 713 is not visually supernatural.
    for i in range(8):
        x = start_x - (i + 0.5) * 350
        created.append(_spawn_box(
            subsystem, mesh, f"AUTO_EXT_F7_Window_{701+i}",
            (x, south - 18, z + 180), (190, 10, 145),
            m["M_EXT_DarkGlass"], f
        ))
        created.append(_spawn_box(
            subsystem, mesh, f"AUTO_EXT_F7_Window_{709+i}",
            (x, north + 18, z + 180), (190, 10, 145),
            m["M_EXT_DarkGlass"], f
        ))


def _build_rooftop_details(subsystem, mesh, m, created):
    f = f"{ROOT_FOLDER}/Roof"
    roof_z = _floor_z(6) + 390

    # Mechanical blocks break up the silhouette and make the massing believable.
    details = [
        ("AUTO_EXT_HVAC_01", (-5000, 1100, roof_z), (500, 320, 180)),
        ("AUTO_EXT_HVAC_02", (-3900, 1100, roof_z), (420, 300, 150)),
        ("AUTO_EXT_HVAC_03", (1800, 1100, roof_z), (550, 350, 170)),
        ("AUTO_EXT_HVAC_04", (3200, 1100, roof_z), (380, 260, 140)),
    ]
    for spec in details:
        created.append(_spawn_box(
            subsystem, mesh, *spec, m["M_EXT_Metal"], f
        ))


def _build_service_rear(subsystem, mesh, m, created):
    f = f"{ROOT_FOLDER}/Service"
    specs = [
        ("AUTO_EXT_ServiceYard", (0, 2200, 5), (2200, 700, 10), m["M_EXT_Asphalt"]),
        ("AUTO_EXT_LoadingCanopy", (250, 1910, 280), (900, 350, 24), m["M_EXT_Metal"]),
        ("AUTO_EXT_LoadingBay_01", (50, 1940, 125), (260, 20, 220), m["M_EXT_Metal"]),
        ("AUTO_EXT_LoadingBay_02", (360, 1940, 125), (260, 20, 220), m["M_EXT_Metal"]),
        ("AUTO_EXT_ServiceWall", (0, 1920, 180), (1500, 30, 320), m["M_EXT_WarmStone"]),
    ]
    for spec in specs:
        created.append(_spawn_box(subsystem, mesh, *spec, f))


def build_hotel_exterior():
    _ensure_level()
    subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    mesh = _cube()
    m = _materials()

    with unreal.ScopedEditorTransaction("Build Where's My Room hotel exterior"):
        deleted = _delete_previous(subsystem)
        created = []

        _build_ground_front(subsystem, mesh, m, created)
        _build_core(subsystem, mesh, m, created)
        _build_wing_shell(
            subsystem, mesh, m, created, "A",
            A_CENTER_X, A_LENGTH, A_START_X, 20, 300
        )
        _build_wing_shell(
            subsystem, mesh, m, created, "B",
            B_CENTER_X, B_LENGTH, B_START_X, 10, 500
        )
        _build_seventh_floor(subsystem, mesh, m, created)
        _build_rooftop_details(subsystem, mesh, m, created)
        _build_service_rear(subsystem, mesh, m, created)

    unreal.log(
        f"Where's My Room exterior: removed {deleted} old exterior actors and "
        f"created {len(created)} façade/roof/site actors."
    )
    unreal.log(
        "Exterior now includes lobby glazing, porte-cochere, drop-off, two guest wings, "
        "one window per active room, central core, rooftop equipment, service yard, "
        "and a set-back closed seventh floor."
    )


build_hotel_exterior()
