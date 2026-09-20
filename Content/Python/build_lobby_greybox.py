import unreal

EXPECTED_LEVEL = "L_PrototypeEntry"
FOLDER_PATH = "Greybox/AutoLobby"
CUBE_ASSET = "/Engine/BasicShapes/Cube.Cube"

# One run builds the whole playable lobby block.
# All dimensions are in centimeters. Unreal's basic cube is 100 cm on each side.

BOXES = [
    ("GB_LobbyFloor", (0, 0, 10), (2400, 2200, 20)),
    ("GB_LobbyWall_Front_Left", (-700, -1100, 295), (1000, 20, 550)),
    ("GB_LobbyWall_Front_Right", (700, -1100, 295), (1000, 20, 550)),
    ("GB_MainEntrance_Header", (0, -1100, 505), (400, 20, 130)),
    ("GB_LobbyWall_Left_South", (-1200, -285, 295), (20, 1630, 550)),
    ("GB_LobbyWall_Left_North", (-1200, 935, 295), (20, 330, 550)),
    ("GB_WingA_Header", (-1200, 650, 445), (20, 240, 250)),
    ("GB_LobbyWall_Right_South", (1200, -285, 295), (20, 1630, 550)),
    ("GB_LobbyWall_Right_North", (1200, 935, 295), (20, 330, 550)),
    ("GB_WingB_Header", (1200, 650, 445), (20, 240, 250)),
    ("GB_LobbyWall_Back_Left", (-630, 1100, 295), (1140, 20, 550)),
    ("GB_LobbyWall_Back_Right", (630, 1100, 295), (1140, 20, 550)),
    ("GB_BackOfficeDoor_Header", (0, 1100, 405), (120, 20, 330)),
    ("GB_LobbyCeiling", (0, 0, 580), (2400, 2200, 20)),
    ("GB_EntranceColumn_Left", (-450, -780, 295), (50, 50, 550)),
    ("GB_EntranceColumn_Right", (450, -780, 295), (50, 50, 550)),
    ("GB_FrontDesk_Base", (0, 650, 72.5), (800, 80, 105)),
    ("GB_FrontDesk_Top", (0, 650, 130), (820, 100, 10)),
    ("GB_FrontDesk_Return_Left", (-405, 735, 72.5), (10, 170, 105)),
    ("GB_FrontDesk_Return_Right", (405, 735, 72.5), (10, 170, 105)),
    ("GB_Workstation_01", (-300, 720, 165), (45, 12, 30)),
    ("GB_Workstation_02", (-100, 720, 165), (45, 12, 30)),
    ("GB_Workstation_03", (100, 720, 165), (45, 12, 30)),
    ("GB_Workstation_04", (300, 720, 165), (45, 12, 30)),
    ("GB_BackOffice_Floor", (0, 1400, 10), (800, 600, 20)),
    ("GB_BackOffice_Wall_Left", (-400, 1400, 170), (20, 600, 300)),
    ("GB_BackOffice_Wall_Back", (0, 1700, 170), (800, 20, 300)),
    ("GB_BackOffice_Wall_Right_South", (400, 1250, 170), (20, 300, 300)),
    ("GB_BackOffice_Wall_Right_North", (400, 1600, 170), (20, 200, 300)),
    ("GB_BOHDoor_Header", (400, 1450, 280), (20, 100, 80)),
    ("GB_BackOffice_Ceiling", (0, 1400, 330), (800, 600, 20)),
    ("GB_BackOffice_Desk_01", (-180, 1400, 60), (180, 70, 80)),
    ("GB_BackOffice_Desk_02", (180, 1400, 60), (180, 70, 80)),
    ("GB_BackOffice_Cabinet", (0, 1660, 110), (260, 50, 180)),
    ("GB_Elevator_A1", (-850, 1085, 140), (180, 20, 240)),
    ("GB_Elevator_A2", (-620, 1085, 140), (180, 20, 240)),
    ("GB_Elevator_A1_Header", (-850, 1065, 285), (200, 40, 50)),
    ("GB_Elevator_A2_Header", (-620, 1065, 285), (200, 40, 50)),
    ("GB_Sofa_Left", (-650, -350, 60), (300, 85, 80)),
    ("GB_CoffeeTable_Left", (-650, -120, 40), (140, 70, 40)),
    ("GB_Sofa_Right", (650, -350, 60), (300, 85, 80)),
    ("GB_CoffeeTable_Right", (650, -120, 40), (140, 70, 40)),
    ("GB_LobbyTable_Center", (0, -300, 45), (160, 90, 50)),
    ("GB_BellDesk", (850, -750, 65), (220, 70, 90)),
    ("GB_QueueGuide_Left", (-230, 300, 55), (30, 30, 70)),
    ("GB_QueueGuide_Right", (230, 300, 55), (30, 30, 70)),
]

LIGHTS = [
    ("GB_Light_01", (-700, -500, 500)),
    ("GB_Light_02", (0, -500, 500)),
    ("GB_Light_03", (700, -500, 500)),
    ("GB_Light_04", (-700, 300, 500)),
    ("GB_Light_05", (0, 300, 500)),
    ("GB_Light_06", (700, 300, 500)),
    ("GB_Light_BackOffice", (0, 1400, 270)),
]

GENERATED_LABELS = {spec[0] for spec in BOXES} | {spec[0] for spec in LIGHTS}


def _editor_world():
    subsystem = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    return subsystem.get_editor_world()


def _ensure_correct_level():
    world = _editor_world()
    if not world:
        raise RuntimeError("No editor world is currently open.")

    level_name = world.get_name()
    if level_name != EXPECTED_LEVEL:
        raise RuntimeError(
            f"Open {EXPECTED_LEVEL} before running this script. "
            f"Current level: {level_name}"
        )


def _cube_mesh():
    mesh = unreal.EditorAssetLibrary.load_asset(CUBE_ASSET)
    if not mesh:
        raise RuntimeError(f"Could not load Unreal cube asset: {CUBE_ASSET}")
    return mesh


def _delete_previous_generated_actors(actor_subsystem):
    deleted = 0
    for actor in actor_subsystem.get_all_level_actors():
        try:
            label = actor.get_actor_label()
        except Exception:
            continue

        if label in GENERATED_LABELS:
            actor_subsystem.destroy_actor(actor)
            deleted += 1

    return deleted


def _spawn_box(actor_subsystem, mesh, label, location_cm, size_cm):
    actor = actor_subsystem.spawn_actor_from_class(
        unreal.StaticMeshActor,
        unreal.Vector(*location_cm),
        unreal.Rotator(0.0, 0.0, 0.0),
    )
    if not actor:
        raise RuntimeError(f"Could not create actor: {label}")

    actor.set_actor_label(label)

    try:
        actor.set_folder_path(FOLDER_PATH)
    except Exception:
        pass

    component = actor.get_editor_property("static_mesh_component")
    component.set_static_mesh(mesh)

    actor.set_actor_scale3d(
        unreal.Vector(
            size_cm[0] / 100.0,
            size_cm[1] / 100.0,
            size_cm[2] / 100.0,
        )
    )
    return actor


def _spawn_point_light(actor_subsystem, label, location_cm):
    """Create movable preview lighting so greybox edits never require a light bake."""
    try:
        actor = actor_subsystem.spawn_actor_from_class(
            unreal.PointLight,
            unreal.Vector(*location_cm),
            unreal.Rotator(0.0, 0.0, 0.0),
        )
        if not actor:
            return None

        actor.set_actor_label(label)

        try:
            actor.set_folder_path(FOLDER_PATH)
        except Exception:
            pass

        component = actor.get_editor_property("point_light_component")
        component.set_editor_property("mobility", unreal.ComponentMobility.MOVABLE)
        component.set_editor_property("intensity", 3500.0)
        component.set_editor_property("attenuation_radius", 900.0)
        return actor
    except Exception as exc:
        unreal.log_warning(f"Could not create {label}: {exc}")
        return None


def build_lobby_greybox():
    _ensure_correct_level()

    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    mesh = _cube_mesh()

    with unreal.ScopedEditorTransaction("Build complete Where's My Room lobby greybox"):
        deleted = _delete_previous_generated_actors(actor_subsystem)

        created = [
            _spawn_box(actor_subsystem, mesh, label, location, size)
            for label, location, size in BOXES
        ]

        for label, location in LIGHTS:
            light = _spawn_point_light(actor_subsystem, label, location)
            if light:
                created.append(light)

    unreal.log(
        f"Where's My Room: removed {deleted} previous generated actors and "
        f"created {len(created)} lobby actors in {EXPECTED_LEVEL}."
    )
    unreal.log(
        "Generated: complete lobby shell, entrance, wing portals, Front Desk, "
        "Back Office, BOH doorway, elevators, furniture scale references and movable preview lights."
    )
    unreal.log(
        "Walk the route in Play mode. If the proportions feel good, save with Ctrl+S."
    )

    try:
        actor_subsystem.set_selected_level_actors([])
    except Exception:
        pass


build_lobby_greybox()
