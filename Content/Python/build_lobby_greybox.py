import unreal

EXPECTED_LEVEL = "L_PrototypeEntry"
FOLDER_PATH = "Greybox/Lobby"

# Unreal basic Cube is 100 x 100 x 100 cm.
CUBE_ASSET = "/Engine/BasicShapes/Cube.Cube"

# Only these labels are replaced when the script is run again.
GENERATED_LABELS = {
    "GB_LobbyFloor",
    "GB_LobbyWall_Back",
    "GB_LobbyWall_Left",
    "GB_LobbyWall_Right",
    "GB_LobbyWall_Front_Left",
    "GB_LobbyWall_Front_Right",
    "GB_FrontDesk",
    "GB_BackOffice_Wall_Left",
    "GB_BackOffice_Wall_Right",
    "GB_BackOffice_Wall_Front_Left",
    "GB_BackOffice_Wall_Front_Right",
    "GB_Elevator_A1",
    "GB_Elevator_A2",
    "GB_BOH_DoorMarker",
}


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
    for actor in actor_subsystem.get_all_level_actors():
        try:
            label = actor.get_actor_label()
        except Exception:
            continue

        if label in GENERATED_LABELS:
            actor_subsystem.destroy_actor(actor)


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


def build_lobby_greybox():
    _ensure_correct_level()

    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    mesh = _cube_mesh()

    # Design baseline:
    # Lobby: 24 m x 22 m
    # Public ceiling height: 5.5 m
    # Entrance: centered on south/front side
    # Front Desk: 8 m long
    # Back Office: approx. 8 m x 6 m

    boxes = [
        # label, location (cm), size (cm)
        ("GB_LobbyFloor", (0, 0, 10), (2400, 2200, 20)),

        # Outer shell. Entrance is a 4 m opening in the front wall.
        ("GB_LobbyWall_Back", (0, 1100, 295), (2400, 20, 550)),
        ("GB_LobbyWall_Left", (-1200, 0, 295), (20, 2200, 550)),
        ("GB_LobbyWall_Right", (1200, 0, 295), (20, 2200, 550)),
        ("GB_LobbyWall_Front_Left", (-700, -1100, 295), (1000, 20, 550)),
        ("GB_LobbyWall_Front_Right", (700, -1100, 295), (1000, 20, 550)),

        # Front Office counter: 8 m long, 0.8 m deep, 1.15 m high.
        ("GB_FrontDesk", (0, 250, 77.5), (800, 80, 115)),

        # Back Office: 8 m wide x 6 m deep, using the lobby back wall as its rear wall.
        ("GB_BackOffice_Wall_Left", (-400, 800, 170), (20, 600, 300)),
        ("GB_BackOffice_Wall_Right", (400, 800, 170), (20, 600, 300)),
        # Front wall split around a centered 1 m doorway.
        ("GB_BackOffice_Wall_Front_Left", (-225, 500, 170), (350, 20, 300)),
        ("GB_BackOffice_Wall_Front_Right", (225, 500, 170), (350, 20, 300)),

        # Simple elevator-bank placeholders on the left side.
        ("GB_Elevator_A1", (-1180, 250, 140), (20, 180, 240)),
        ("GB_Elevator_A2", (-1180, 520, 140), (20, 180, 240)),

        # BOH shortcut marker on the right side of the back-office area.
        ("GB_BOH_DoorMarker", (1180, 760, 120), (20, 120, 200)),
    ]

    with unreal.ScopedEditorTransaction("Build Where's My Room Lobby Greybox"):
        _delete_previous_generated_actors(actor_subsystem)
        created = [
            _spawn_box(actor_subsystem, mesh, label, location, size)
            for label, location, size in boxes
        ]

    unreal.log(
        f"Where's My Room: created {len(created)} lobby greybox actors in {EXPECTED_LEVEL}."
    )
    unreal.log(
        "Review the layout in the viewport, then save L_PrototypeEntry with Ctrl+S."
    )

    try:
        actor_subsystem.set_selected_level_actors(created)
    except Exception:
        pass


build_lobby_greybox()
