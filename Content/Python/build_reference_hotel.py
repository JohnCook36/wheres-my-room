import math
import unreal


# -----------------------------------------------------------------------------
# Where's My Room? - reference hotel generator
# Target: Unreal Engine 5.8.2, Editor Python. Run outside PIE/Simulate.
# Architectural blockout; elevator operation and door interaction are runtime
# Blueprint responsibilities. Python builds the editor geometry only.
# Public Python API signatures were checked; the host has no Unreal runtime.
# Units: centimetres
# -----------------------------------------------------------------------------

REQUIRED_LEVEL = "L_PrototypeEntry"
ACTOR_PREFIX = "AUTO_REFHOTEL_"
MATERIAL_ROOT = "/Game/Generated/Materials"

FOLDER_EXTERIOR = "ReferenceHotel/Exterior"
FOLDER_ENTRANCE = "ReferenceHotel/Entrance"
FOLDER_WINDOWS = "ReferenceHotel/Windows"
FOLDER_ROOF = "ReferenceHotel/Roof"
FOLDER_SITE = "ReferenceHotel/Site"
FOLDER_SERVICE = "ReferenceHotel/Service"

CUBE_PATH = "/Engine/BasicShapes/Cube.Cube"
CYLINDER_PATH = "/Engine/BasicShapes/Cylinder.Cylinder"
SPHERE_PATH = "/Engine/BasicShapes/Sphere.Sphere"

# Vertical organisation: ground floor + five active guest floors + closed 7th.
GROUND_Z = 0.0
LOBBY_HEIGHT = 550.0
GUEST_FLOOR_HEIGHT = 350.0
ACTIVE_GUEST_FLOORS = (2, 3, 4, 5, 6)
SEVENTH_BASE_Z = LOBBY_HEIGHT + len(ACTIVE_GUEST_FLOORS) * GUEST_FLOOR_HEIGHT
SEVENTH_HEIGHT = 350.0
MAIN_ROOF_Z = SEVENTH_BASE_Z + SEVENTH_HEIGHT

# The front elevation faces negative Y.
FRONT_Y = -1800.0
REAR_Y = 2800.0

# Reference-derived composition: dense guest wing A, broader apartment wing B,
# and a recessed, strongly framed central lobby/crown.
LEFT_WING_CENTER_X = -3100.0
LEFT_WING_WIDTH = 3800.0
LEFT_WING_DEPTH = 4600.0
RIGHT_WING_CENTER_X = 2900.0
RIGHT_WING_WIDTH = 3400.0
RIGHT_WING_DEPTH = 4600.0
WING_CENTER_Y = 500.0
CENTRAL_WIDTH = 2400.0
CENTRAL_DEPTH = 2600.0
CENTRAL_CENTER_Y = -500.0

# Recessed seventh-floor volumes.
LEFT_SEVENTH_WIDTH = 3500.0
RIGHT_SEVENTH_WIDTH = 3100.0
SEVENTH_DEPTH = 4200.0
SEVENTH_CENTER_Y = 500.0

ACTOR_SUBSYSTEM = None
ASSET_TOOLS = None
CUBE_MESH = None
CYLINDER_MESH = None
SPHERE_MESH = None
MATERIALS = {}
CREATED_ACTORS = []
TARGET_LEVEL = None


def current_level_name():
    editor_subsystem = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    world = editor_subsystem.get_editor_world()
    if not world:
        return ""
    path_name = world.get_path_name()
    leaf = path_name.rsplit("/", 1)[-1]
    return leaf.split(".", 1)[0]


def require_target_level():
    """Read-only guard, also used directly by the deletion helper."""
    editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    if editor.get_game_world() is not None:
        raise RuntimeError("Stop Play/Simulate before building ReferenceHotel.")
    level = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).get_current_level()
    package_name = level.get_path_name().rsplit("/", 1)[-1].split(".", 1)[0] if level else ""
    if current_level_name() != REQUIRED_LEVEL or package_name != REQUIRED_LEVEL:
        raise RuntimeError(
            "Open L_PrototypeEntry and make its persistent level current. "
            "Nothing was created or deleted."
        )
    return level


def validate_api():
    """Check the installed editor's actual Python surface before any mutation."""
    required = {
        "EditorActorSubsystem": ("spawn_actor_from_class", "get_all_level_actors", "destroy_actor"),
        "UnrealEditorSubsystem": ("get_editor_world", "get_game_world"),
        "LevelEditorSubsystem": ("get_current_level",),
        "EditorAssetLibrary": ("load_asset", "does_asset_exist", "make_directory", "save_loaded_asset"),
        "MaterialEditingLibrary": ("create_material_expression", "connect_material_property", "recompile_material"),
        "StaticMeshComponent": ("set_static_mesh", "set_material", "set_mobility", "set_collision_enabled"),
        "Actor": ("get_level", "get_actor_label", "set_actor_label", "set_folder_path", "set_actor_scale3d"),
        "TextRenderComponent": ("set_text", "set_world_size", "set_text_render_color"),
        "PointLightComponent": (
            "set_mobility",
            "set_intensity_units",
            "set_intensity",
            "set_attenuation_radius",
            "set_light_color",
        ),
        "PointLight": (), "TextRenderActor": (), "StaticMeshActor": (),
        "MaterialFactoryNew": (), "MaterialExpressionConstant3Vector": (),
        "MaterialExpressionConstant": (), "ScopedEditorTransaction": (),
    }
    missing = []
    for class_name, methods in required.items():
        cls = getattr(unreal, class_name, None)
        if cls is None:
            missing.append(class_name)
        else:
            missing.extend(class_name + "." + name for name in methods if not hasattr(cls, name))
    if missing:
        raise RuntimeError("Unreal Python API unavailable: " + ", ".join(missing))


def evenly_spaced(start, end, count):
    if count <= 1:
        return [(start + end) * 0.5]
    step = (end - start) / float(count - 1)
    return [start + step * index for index in range(count)]


def guest_window_z(floor_number):
    floor_base = LOBBY_HEIGHT + (floor_number - 2) * GUEST_FLOOR_HEIGHT
    return floor_base + 190.0


def set_actor_identity(actor, label, folder, tags=None):
    actor.set_actor_label(ACTOR_PREFIX + label)
    actor.set_folder_path(unreal.Name(folder))
    tag_names = [unreal.Name("ReferenceHotelGenerated")]
    if tags:
        tag_names.extend(unreal.Name(tag) for tag in tags)
    actor.set_editor_property("tags", tag_names)
    CREATED_ACTORS.append(actor)
    return actor


def spawn_mesh(label, location, dimensions, material, folder, mesh=None,
               rotation=(0.0, 0.0, 0.0), collision=True, tags=None):
    static_mesh = mesh or CUBE_MESH
    if any(not math.isfinite(float(v)) or v <= 0 for v in dimensions):
        raise ValueError("Invalid dimensions for " + label)
    rotator = unreal.Rotator(
        pitch=float(rotation[0]),
        yaw=float(rotation[1]),
        roll=float(rotation[2]),
    )
    actor = ACTOR_SUBSYSTEM.spawn_actor_from_class(
        unreal.StaticMeshActor,
        unreal.Vector(float(location[0]), float(location[1]), float(location[2])),
        rotator,
    )
    if actor is None:
        raise RuntimeError("Unable to spawn StaticMeshActor: " + label)

    set_actor_identity(actor, label, folder, tags)
    component = actor.get_component_by_class(unreal.StaticMeshComponent)
    component.set_mobility(unreal.ComponentMobility.MOVABLE)
    component.set_static_mesh(static_mesh)
    actor.set_actor_scale3d(
        unreal.Vector(
            float(dimensions[0]) / 100.0,
            float(dimensions[1]) / 100.0,
            float(dimensions[2]) / 100.0,
        )
    )
    if material:
        component.set_material(0, material)
    if material in (MATERIALS.get("glass"), MATERIALS.get("glass_warm")):
        component.set_editor_property("cast_shadow", False)
    if not collision:
        component.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        component.set_editor_property("generate_overlap_events", False)
    return actor


def spawn_cube(label, location, dimensions, material, folder, collision=True, tags=None):
    return spawn_mesh(
        label, location, dimensions, material, folder,
        mesh=CUBE_MESH, collision=collision, tags=tags,
    )


def spawn_cylinder(label, location, dimensions, material, folder, collision=True, tags=None):
    return spawn_mesh(
        label, location, dimensions, material, folder,
        mesh=CYLINDER_MESH, collision=collision, tags=tags,
    )


def spawn_sphere(label, location, diameter, material, folder, collision=False, tags=None):
    return spawn_mesh(
        label, location, (diameter, diameter, diameter), material, folder,
        mesh=SPHERE_MESH, collision=collision, tags=tags,
    )


def create_simple_material(asset_name, color, roughness, metallic=0.0, opacity=1.0):
    asset_path = MATERIAL_ROOT + "/" + asset_name
    existing = (unreal.EditorAssetLibrary.load_asset(asset_path)
                if unreal.EditorAssetLibrary.does_asset_exist(asset_path) else None)
    if existing:
        if not isinstance(existing, unreal.Material):
            raise RuntimeError("Material path is occupied by another asset: " + asset_path)
        return existing

    material = ASSET_TOOLS.create_asset(
        asset_name,
        MATERIAL_ROOT,
        unreal.Material,
        unreal.MaterialFactoryNew(),
    )
    if material is None:
        raise RuntimeError("Unable to create material: " + asset_path)

    base_color = unreal.MaterialEditingLibrary.create_material_expression(
        material, unreal.MaterialExpressionConstant3Vector, -420, -80
    )
    base_color.set_editor_property(
        "constant", unreal.LinearColor(float(color[0]), float(color[1]), float(color[2]), 1.0)
    )
    unreal.MaterialEditingLibrary.connect_material_property(
        base_color, "", unreal.MaterialProperty.MP_BASE_COLOR
    )

    roughness_node = unreal.MaterialEditingLibrary.create_material_expression(
        material, unreal.MaterialExpressionConstant, -420, 40
    )
    roughness_node.set_editor_property("r", float(roughness))
    unreal.MaterialEditingLibrary.connect_material_property(
        roughness_node, "", unreal.MaterialProperty.MP_ROUGHNESS
    )

    metallic_node = unreal.MaterialEditingLibrary.create_material_expression(
        material, unreal.MaterialExpressionConstant, -420, 140
    )
    metallic_node.set_editor_property("r", float(metallic))
    unreal.MaterialEditingLibrary.connect_material_property(
        metallic_node, "", unreal.MaterialProperty.MP_METALLIC
    )

    if opacity < 1.0:
        material.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
        material.set_editor_property("two_sided", True)
        opacity_node = unreal.MaterialEditingLibrary.create_material_expression(
            material, unreal.MaterialExpressionConstant, -420, 240
        )
        opacity_node.set_editor_property("r", float(opacity))
        unreal.MaterialEditingLibrary.connect_material_property(
            opacity_node, "", unreal.MaterialProperty.MP_OPACITY
        )

    compile_errors = unreal.MaterialEditingLibrary.recompile_material(material)
    if compile_errors:
        raise RuntimeError(
            "Material compile failed for {}: {}".format(
                asset_path, "; ".join(str(item) for item in compile_errors)
            )
        )
    if not unreal.EditorAssetLibrary.save_loaded_asset(material, False):
        raise RuntimeError("Unable to save material: " + asset_path)
    return material


def create_materials():
    unreal.EditorAssetLibrary.make_directory(MATERIAL_ROOT)
    definitions = {
        # Warm limestone, charcoal-brown frames and blue-black glass match the reference.
        "facade": ("M_RefHotel_FacadeWarmStone", (0.42, 0.34, 0.25), 0.72, 0.0, 1.0),
        "facade_light": ("M_RefHotel_FacadeLight", (0.64, 0.55, 0.43), 0.68, 0.0, 1.0),
        "facade_dark": ("M_RefHotel_FacadeDark", (0.075, 0.064, 0.056), 0.60, 0.05, 1.0),
        "glass": ("M_RefHotel_Glass", (0.018, 0.052, 0.075), 0.14, 0.08, 0.34),
        "glass_warm": ("M_RefHotel_GlassWarm", (0.16, 0.105, 0.050), 0.18, 0.02, 0.42),
        "metal": ("M_RefHotel_Metal", (0.095, 0.075, 0.055), 0.30, 0.78, 1.0),
        "gold": ("M_RefHotel_GoldAccent", (0.36, 0.235, 0.085), 0.27, 0.72, 1.0),
        "roof": ("M_RefHotel_Roof", (0.035, 0.040, 0.043), 0.76, 0.10, 1.0),
        "asphalt": ("M_RefHotel_Asphalt", (0.026, 0.031, 0.033), 0.93, 0.0, 1.0),
        "paving": ("M_RefHotel_Paving", (0.30, 0.265, 0.215), 0.82, 0.0, 1.0),
        "concrete": ("M_RefHotel_Concrete", (0.22, 0.225, 0.22), 0.88, 0.0, 1.0),
        "green": ("M_RefHotel_Green", (0.055, 0.105, 0.047), 0.92, 0.0, 1.0),
        "wood": ("M_RefHotel_Wood", (0.18, 0.095, 0.045), 0.66, 0.0, 1.0),
        "interior": ("M_RefHotel_InteriorWarm", (0.48, 0.34, 0.20), 0.74, 0.0, 1.0),
    }
    result = {}
    for key, data in definitions.items():
        result[key] = create_simple_material(data[0], data[1], data[2], data[3], data[4])
    return result


def delete_previous_generated_actors():
    target = require_target_level()
    deleted = 0
    for actor in list(ACTOR_SUBSYSTEM.get_all_level_actors()):
        try:
            label = actor.get_actor_label()
        except Exception:
            continue
        if actor.get_level() == target and label.startswith(ACTOR_PREFIX):
            if not ACTOR_SUBSYSTEM.destroy_actor(actor):
                raise RuntimeError("Unable to delete generated actor: " + label)
            deleted += 1
    unreal.log("ReferenceHotel: removed {} previously generated actors.".format(deleted))


def build_left_wing():
    # Ground podium, active guest block, recessed old seventh floor, and front corner tower.
    spawn_cube(
        "LeftWing_GroundPodium", (LEFT_WING_CENTER_X, WING_CENTER_Y, LOBBY_HEIGHT * 0.5),
        (LEFT_WING_WIDTH, LEFT_WING_DEPTH, LOBBY_HEIGHT), MATERIALS["facade_light"], FOLDER_EXTERIOR,
        tags=["WingA", "GroundFloor"]
    )
    active_height = SEVENTH_BASE_Z - LOBBY_HEIGHT
    spawn_cube(
        "LeftWing_ActiveGuestBlock", (LEFT_WING_CENTER_X, WING_CENTER_Y, LOBBY_HEIGHT + active_height * 0.5),
        (LEFT_WING_WIDTH, LEFT_WING_DEPTH, active_height), MATERIALS["facade"], FOLDER_EXTERIOR,
        tags=["WingA", "Floors2To6", "RoomCapacity200"]
    )

    spawn_cube(
        "LeftWing_FrontCornerTower", (-4850.0, -1460.0, 1450.0),
        (430.0, 760.0, 2900.0), MATERIALS["facade_dark"], FOLDER_EXTERIOR,
        tags=["ReferenceCornerTower", "WingA"]
    )
    spawn_cube(
        "LeftWing_RearCornerTower", (-4850.0, 2460.0, 1400.0),
        (430.0, 760.0, 2800.0), MATERIALS["facade_dark"], FOLDER_EXTERIOR,
        tags=["WingA"]
    )


def build_right_wing():
    # Apartment wing is slightly narrower and uses broader bays/balconies.
    spawn_cube(
        "RightWing_GroundPodium", (RIGHT_WING_CENTER_X, WING_CENTER_Y, LOBBY_HEIGHT * 0.5),
        (RIGHT_WING_WIDTH, RIGHT_WING_DEPTH, LOBBY_HEIGHT), MATERIALS["facade_light"], FOLDER_EXTERIOR,
        tags=["WingB", "GroundFloor"]
    )
    active_height = SEVENTH_BASE_Z - LOBBY_HEIGHT
    spawn_cube(
        "RightWing_ActiveGuestBlock", (RIGHT_WING_CENTER_X, WING_CENTER_Y, LOBBY_HEIGHT + active_height * 0.5),
        (RIGHT_WING_WIDTH, RIGHT_WING_DEPTH, active_height), MATERIALS["facade"], FOLDER_EXTERIOR,
        tags=["WingB", "Floors2To6", "RoomCapacity100"]
    )

    spawn_cube(
        "RightWing_FrontCornerTower", (4450.0, -1510.0, 1500.0),
        (520.0, 820.0, 3000.0), MATERIALS["facade_dark"], FOLDER_EXTERIOR,
        tags=["ReferenceCornerTower", "WingB"]
    )
    spawn_cube(
        "RightWing_RearCornerTower", (4450.0, 2460.0, 1430.0),
        (520.0, 760.0, 2860.0), MATERIALS["facade_dark"], FOLDER_EXTERIOR,
        tags=["WingB"]
    )


def build_main_mass():
    build_left_wing()
    build_right_wing()

    # Central floors are deliberately shallower than the wings, matching the recessed facade.
    active_height = SEVENTH_BASE_Z - LOBBY_HEIGHT
    spawn_cube(
        "CentralUpperBlock", (0.0, CENTRAL_CENTER_Y + 55.0, LOBBY_HEIGHT + active_height * 0.5),
        (CENTRAL_WIDTH, CENTRAL_DEPTH - 110.0, active_height), MATERIALS["facade_dark"], FOLDER_EXTERIOR,
        tags=["CentralBlock", "RecessedFacade"]
    )
    spawn_cube(
        "CentralSeventhCrownFloor", (0.0, -420.0, SEVENTH_BASE_Z + 12.0),
        (2400.0, 1900.0, 24.0), MATERIALS["concrete"], FOLDER_EXTERIOR,
        tags=["ClosedFloor7", "CentralHistoricVolume"]
    )
    spawn_cube(
        "CentralSeventhCrownFront", (0.0, -1355.0, SEVENTH_BASE_Z + 175.0),
        (2400.0, 30.0, SEVENTH_HEIGHT), MATERIALS["facade"], FOLDER_EXTERIOR,
        tags=["ClosedFloor7", "CentralHistoricVolume"]
    )
    spawn_cube(
        "CentralSeventhCrownRoof", (0.0, -420.0, MAIN_ROOF_Z),
        (2400.0, 1900.0, 24.0), MATERIALS["roof"], FOLDER_ROOF,
        tags=["ClosedFloor7"]
    )

    # Lobby shell: a true 24 x 22 m visible interior rather than a solid central box.
    spawn_cube(
        "LobbyFloor", (0.0, -700.0, 10.0), (2400.0, 2200.0, 20.0),
        MATERIALS["paving"], FOLDER_ENTRANCE, tags=["Lobby", "24x22m"]
    )
    spawn_cube(
        "LobbyCeiling", (0.0, -700.0, 535.0), (2400.0, 2200.0, 30.0),
        MATERIALS["facade_dark"], FOLDER_ENTRANCE, tags=["Lobby"]
    )
    spawn_cube(
        "LobbyLeftWall", (-1185.0, -700.0, 275.0), (30.0, 2200.0, 550.0),
        MATERIALS["facade_light"], FOLDER_ENTRANCE, tags=["Lobby"]
    )
    spawn_cube(
        "LobbyRightWall", (1185.0, -700.0, 275.0), (30.0, 2200.0, 550.0),
        MATERIALS["facade_light"], FOLDER_ENTRANCE, tags=["Lobby"]
    )
    # The rear wall leaves an 8 m opening into the adjacent back office.
    spawn_cube(
        "LobbyRearWallLeft", (-800.0, 390.0, 275.0), (800.0, 30.0, 550.0),
        MATERIALS["facade_light"], FOLDER_ENTRANCE, tags=["Lobby"]
    )
    spawn_cube(
        "LobbyRearWallRight", (800.0, 390.0, 275.0), (800.0, 30.0, 550.0),
        MATERIALS["facade_light"], FOLDER_ENTRANCE, tags=["Lobby"]
    )

    # Plinth stops at the lobby so the entrance has no 1.1 m collision barrier.
    for label, x, width in (
        ("Left", LEFT_WING_CENTER_X, LEFT_WING_WIDTH),
        ("Right", RIGHT_WING_CENTER_X, RIGHT_WING_WIDTH),
    ):
        spawn_cube(
            "PlinthFront_" + label, (x, FRONT_Y - 22.0, 55.0), (width, 44.0, 110.0),
            MATERIALS["facade_dark"], FOLDER_EXTERIOR, tags=["Plinth"]
        )


def build_facade_modules():
    # Floor belts make the reference's strong horizontal rhythm and keep the glass recessed.
    belt_levels = [LOBBY_HEIGHT] + [LOBBY_HEIGHT + i * GUEST_FLOOR_HEIGHT for i in range(1, 6)]
    for index, z in enumerate(belt_levels):
        for label, x, width in (
            ("A", LEFT_WING_CENTER_X, LEFT_WING_WIDTH),
            ("B", RIGHT_WING_CENTER_X, RIGHT_WING_WIDTH),
        ):
            spawn_cube(
                "FrontBelt_{}_{}".format(label, index), (x, FRONT_Y - 34.0, z),
                (width, 68.0, 24.0), MATERIALS["metal"], FOLDER_EXTERIOR,
                collision=False, tags=["FacadeBelt"]
            )
            spawn_cube(
                "RearBelt_{}_{}".format(label, index), (x, REAR_Y + 34.0, z),
                (width, 68.0, 24.0), MATERIALS["metal"], FOLDER_EXTERIOR,
                collision=False, tags=["FacadeBelt"]
            )

    # Central projecting floor ledges recall the illuminated terraces in the reference image.
    for floor_number in ACTIVE_GUEST_FLOORS:
        base = LOBBY_HEIGHT + (floor_number - 2) * GUEST_FLOOR_HEIGHT
        spawn_cube(
            "CentralBalconySlab_F{}".format(floor_number), (0.0, FRONT_Y - 72.0, base + 62.0),
            (2050.0, 150.0, 24.0), MATERIALS["facade_light"], FOLDER_EXTERIOR,
            tags=["CentralBalcony"]
        )
        spawn_cube(
            "CentralBalconyRail_F{}".format(floor_number), (0.0, FRONT_Y - 136.0, base + 105.0),
            (2050.0, 18.0, 78.0), MATERIALS["glass"], FOLDER_EXTERIOR,
            collision=False, tags=["CentralBalcony"]
        )

    # Wing B's apartment balconies are wider and fewer than Wing A's room bays.
    for floor_number in ACTIVE_GUEST_FLOORS:
        base = LOBBY_HEIGHT + (floor_number - 2) * GUEST_FLOOR_HEIGHT
        spawn_cube(
            "WingB_BalconySlab_F{}".format(floor_number),
            (RIGHT_WING_CENTER_X - 100.0, FRONT_Y - 62.0, base + 58.0),
            (2700.0, 128.0, 22.0), MATERIALS["facade_light"], FOLDER_EXTERIOR,
            tags=["WingB", "ApartmentBalcony"]
        )
        spawn_cube(
            "WingB_BalconyRail_F{}".format(floor_number),
            (RIGHT_WING_CENTER_X - 100.0, FRONT_Y - 115.0, base + 102.0),
            (2700.0, 16.0, 72.0), MATERIALS["glass"], FOLDER_EXTERIOR,
            collision=False, tags=["WingB", "ApartmentBalcony"]
        )

    # Strong bronze/charcoal verticals, with denser spacing on Wing A.
    left_pilons = [-4720.0, -4140.0, -3560.0, -2980.0, -2400.0, -1820.0, -1240.0]
    right_pilons = [1220.0, 1900.0, 2580.0, 3260.0, 3940.0, 4580.0]
    for index, x in enumerate(left_pilons):
        spawn_cube(
            "FrontPylon_A_{:02d}".format(index), (x, FRONT_Y - 48.0, 1430.0),
            (62.0, 96.0, 2860.0), MATERIALS["metal"], FOLDER_EXTERIOR,
            tags=["WingA", "VerticalPylon"]
        )
    for index, x in enumerate(right_pilons):
        spawn_cube(
            "FrontPylon_B_{:02d}".format(index), (x, FRONT_Y - 49.0, 1460.0),
            (72.0, 98.0, 2920.0), MATERIALS["metal"], FOLDER_EXTERIOR,
            tags=["WingB", "VerticalPylon"]
        )

    # Side corner quoins and rear vertical accents give the block depth from oblique views.
    for side_name, x in (("West", -5018.0), ("East", 4618.0)):
        for y in (-1420.0, -650.0, 120.0, 890.0, 1660.0, 2430.0):
            spawn_cube(
                "SidePylon_{}_{}".format(side_name, int(y)), (x, y, 1430.0),
                (76.0, 70.0, 2860.0), MATERIALS["metal"], FOLDER_EXTERIOR,
                tags=["VerticalPylon"]
            )

    # Central frame and flanking stone towers make the entrance a clear focal point.
    for x in (-1120.0, 1120.0):
        spawn_cube(
            "CentralTower_{:+.0f}".format(x), (x, FRONT_Y - 58.0, 1435.0),
            (180.0, 116.0, 2870.0), MATERIALS["facade_light"], FOLDER_EXTERIOR,
            tags=["CentralFrame"]
        )
    spawn_cube(
        "CentralUpperEntablature", (0.0, FRONT_Y - 62.0, 2260.0),
        (2400.0, 124.0, 95.0), MATERIALS["facade_light"], FOLDER_EXTERIOR,
        tags=["UpperArchitecturalBand"]
    )


def frame_opening(label, location, width, height, thickness, folder):
    x, y, z = location
    for side, dx in (("L", -(width - thickness) * 0.5),
                     ("R", (width - thickness) * 0.5)):
        spawn_cube(label + side, (x + dx, y, z),
                   (thickness, 22.0, height), MATERIALS["metal"], folder)
    for side, dz in (("Top", (height - thickness) * 0.5),
                     ("Bottom", -(height - thickness) * 0.5)):
        spawn_cube(label + side, (x, y, z + dz),
                   (width - thickness * 2.0, 22.0, thickness),
                   MATERIALS["metal"], folder)


def spawn_guest_window(label, location, dimensions, tags):
    return spawn_cube(
        label, location, dimensions, MATERIALS["glass"], FOLDER_WINDOWS,
        collision=False, tags=tags + ["GuestWindow"]
    )


def build_windows():
    # Exactly 60 active room-window markers per floor: Wing A 40, Wing B 20.
    # Wing A: 12 front + 12 rear + 8 outside + 8 courtyard = 40.
    # Wing B: 6 front + 6 rear + 4 outside + 4 courtyard = 20.
    for floor_number in ACTIVE_GUEST_FLOORS:
        z = guest_window_z(floor_number)

        slot = 1
        for x in evenly_spaced(-4630.0, -1570.0, 12):
            spawn_guest_window(
                "Window_F{}_A_{:02d}_Front".format(floor_number, slot),
                (x, FRONT_Y - 18.0, z), (175.0, 34.0, 190.0),
                ["WingA", "Floor{}".format(floor_number), "RoomSlot{:02d}".format(slot)]
            )
            slot += 1
        for x in evenly_spaced(-4630.0, -1570.0, 12):
            spawn_guest_window(
                "Window_F{}_A_{:02d}_Rear".format(floor_number, slot),
                (x, REAR_Y + 18.0, z), (175.0, 34.0, 190.0),
                ["WingA", "Floor{}".format(floor_number), "RoomSlot{:02d}".format(slot)]
            )
            slot += 1
        for y in evenly_spaced(-1260.0, 2260.0, 8):
            spawn_guest_window(
                "Window_F{}_A_{:02d}_Outer".format(floor_number, slot),
                (-5018.0, y, z), (34.0, 175.0, 190.0),
                ["WingA", "Floor{}".format(floor_number), "RoomSlot{:02d}".format(slot)]
            )
            slot += 1
        for y in evenly_spaced(720.0, 2440.0, 8):
            spawn_guest_window(
                "Window_F{}_A_{:02d}_Courtyard".format(floor_number, slot),
                (-1182.0, y, z), (34.0, 165.0, 190.0),
                ["WingA", "Floor{}".format(floor_number), "RoomSlot{:02d}".format(slot)]
            )
            slot += 1

        slot = 1
        for x in evenly_spaced(1450.0, 4210.0, 6):
            spawn_guest_window(
                "Window_F{}_B_{:02d}_Front".format(floor_number, slot),
                (x, FRONT_Y - 19.0, z), (260.0, 36.0, 205.0),
                ["WingB", "Floor{}".format(floor_number), "RoomSlot{:02d}".format(slot)]
            )
            slot += 1
        for x in evenly_spaced(1450.0, 4210.0, 6):
            spawn_guest_window(
                "Window_F{}_B_{:02d}_Rear".format(floor_number, slot),
                (x, REAR_Y + 19.0, z), (260.0, 36.0, 205.0),
                ["WingB", "Floor{}".format(floor_number), "RoomSlot{:02d}".format(slot)]
            )
            slot += 1
        for y in evenly_spaced(-1120.0, 2260.0, 4):
            spawn_guest_window(
                "Window_F{}_B_{:02d}_Outer".format(floor_number, slot),
                (4618.0, y, z), (36.0, 260.0, 205.0),
                ["WingB", "Floor{}".format(floor_number), "RoomSlot{:02d}".format(slot)]
            )
            slot += 1
        for y in evenly_spaced(800.0, 2380.0, 4):
            spawn_guest_window(
                "Window_F{}_B_{:02d}_Courtyard".format(floor_number, slot),
                (1182.0, y, z), (36.0, 250.0, 205.0),
                ["WingB", "Floor{}".format(floor_number), "RoomSlot{:02d}".format(slot)]
            )
            slot += 1

    # Central bays are public/lounge glazing, narrower and vertically aligned.
    for floor_number in ACTIVE_GUEST_FLOORS:
        z = guest_window_z(floor_number)
        for index, x in enumerate((-820.0, -410.0, 0.0, 410.0, 820.0)):
            spawn_cube(
                "CentralWindow_F{}_{:02d}".format(floor_number, index + 1),
                (x, FRONT_Y - 16.0, z), (270.0, 32.0, 205.0),
                MATERIALS["glass_warm"], FOLDER_WINDOWS, collision=False,
                tags=["CentralPublicBay", "Floor{}".format(floor_number)]
            )

    # The physical, intact seventh floor has sixteen rooms; room 713 is explicit.
    seventh_z = SEVENTH_BASE_Z + 190.0
    room_number = 701
    for x in evenly_spaced(-4550.0, -1650.0, 8):
        spawn_guest_window(
            "Room{}_Window".format(room_number), (x, -1608.0, seventh_z),
            (180.0, 34.0, 175.0),
            ["ClosedFloor7", "Room{}".format(room_number), "WingA"]
        )
        room_number += 1
    for x in evenly_spaced(1500.0, 4300.0, 8):
        extra_tags = ["ClosedFloor7", "Room{}".format(room_number), "WingB"]
        if room_number == 713:
            extra_tags.append("Room713Exists")
        spawn_guest_window(
            "Room{}_Window".format(room_number), (x, -1608.0, seventh_z),
            (210.0, 34.0, 185.0), extra_tags
        )
        room_number += 1

    # Ground-floor public glazing in the two side pavilions.
    for side, x_values in (
        ("A", (-4440.0, -3900.0, -3360.0, -2820.0, -2280.0, -1740.0)),
        ("B", (1580.0, 2180.0, 2780.0, 3380.0, 3980.0)),
    ):
        for index, x in enumerate(x_values):
            spawn_cube(
                "GroundPublicGlass_{}_{:02d}".format(side, index + 1),
                (x, FRONT_Y - 18.0, 305.0), (360.0, 34.0, 340.0),
                MATERIALS["glass_warm"], FOLDER_WINDOWS, collision=False,
                tags=["GroundFloor", "PublicArea", "Wing" + side]
            )


def build_entrance():
    # Double-height lobby curtain wall.
    spawn_cube(
        "LobbyCurtainWall", (0.0, FRONT_Y - 10.0, 285.0), (2220.0, 20.0, 470.0),
        MATERIALS["glass_warm"], FOLDER_ENTRANCE, collision=False,
        tags=["Lobby", "CurtainWall"]
    )
    for index, x in enumerate(evenly_spaced(-1080.0, 1080.0, 9)):
        spawn_cube(
            "LobbyMullionV_{:02d}".format(index), (x, FRONT_Y - 38.0, 285.0),
            (24.0, 56.0, 480.0), MATERIALS["metal"], FOLDER_ENTRANCE,
            collision=False, tags=["LobbyFrame"]
        )
    for index, z in enumerate((270.0, 520.0)):
        spawn_cube(
            "LobbyMullionH_{:02d}".format(index), (0.0, FRONT_Y - 38.0, z),
            (2240.0, 56.0, 24.0), MATERIALS["metal"], FOLDER_ENTRANCE,
            collision=False, tags=["LobbyFrame"]
        )

    # Four framed transparent leaves; runtime interaction belongs to Blueprints.
    for index, x in enumerate((-270.0, -90.0, 90.0, 270.0)):
        spawn_cube(
            "EntranceDoorGlass_{:02d}".format(index + 1),
            (x, FRONT_Y - 72.0, 130.0), (156.0, 8.0, 220.0),
            MATERIALS["glass"], FOLDER_ENTRANCE, collision=False,
            tags=["MainEntranceDoor", "DoorInteractionBlueprintRequired"]
        )
        frame_opening("EntranceDoorFrame_{:02d}".format(index + 1),
                      (x, FRONT_Y - 72.0, 130.0), 174.0, 240.0, 12.0,
                      FOLDER_ENTRANCE)

    # Porte-cochere: deep slab, dark sign fascia, and paired stone/metal supports.
    spawn_cube(
        "PorteCochereCanopy", (0.0, -2390.0, 430.0), (2600.0, 1180.0, 48.0),
        MATERIALS["roof"], FOLDER_ENTRANCE, tags=["PorteCochere"]
    )
    spawn_cube(
        "PorteCochereWarmSoffit", (0.0, -2390.0, 401.0), (2500.0, 1080.0, 18.0),
        MATERIALS["interior"], FOLDER_ENTRANCE, collision=False, tags=["PorteCochere"]
    )
    spawn_cube(
        "PorteCochereFrontFascia", (0.0, -2980.0, 437.0), (2620.0, 54.0, 128.0),
        MATERIALS["facade_dark"], FOLDER_ENTRANCE, tags=["HotelSignBacking"]
    )
    for index, (x, y) in enumerate(((-1080.0, -2840.0), (1080.0, -2840.0),
                                    (-1080.0, -1990.0), (1080.0, -1990.0))):
        spawn_cube(
            "CanopyColumn_{:02d}".format(index + 1), (x, y, 215.0), (58.0, 58.0, 430.0),
            MATERIALS["facade_light"], FOLDER_ENTRANCE, tags=["PorteCochereColumn"]
        )
        spawn_cube(
            "CanopyColumnBase_{:02d}".format(index + 1), (x, y, 35.0), (92.0, 92.0, 70.0),
            MATERIALS["facade_dark"], FOLDER_ENTRANCE, tags=["PorteCochereColumn"]
        )

    # HOTEL placeholder sign; no real-world brand is used.
    text_actor = ACTOR_SUBSYSTEM.spawn_actor_from_class(
        unreal.TextRenderActor,
        unreal.Vector(-285.0, -3012.0, 445.0),
        unreal.Rotator(pitch=0.0, yaw=-90.0, roll=0.0),
    )
    if text_actor:
        set_actor_identity(text_actor, "HotelPlaceholderSign", FOLDER_ENTRANCE, ["HOTEL", "PlaceholderSign"])
        text_component = text_actor.get_component_by_class(unreal.TextRenderComponent)
        text_component.set_text("HOTEL")
        text_component.set_world_size(118.0)
        text_component.set_text_render_color(unreal.Color(218, 178, 104, 255))

    # Front desk (8 m), back office (8 x 6 m), and visible lobby furniture.
    spawn_cube(
        "FrontDeskBody", (0.0, -40.0, 62.0), (800.0, 95.0, 112.0),
        MATERIALS["wood"], FOLDER_ENTRANCE, tags=["FrontOffice", "FrontDesk8m"]
    )
    spawn_cube(
        "FrontDeskTop", (0.0, -40.0, 124.0), (830.0, 115.0, 14.0),
        MATERIALS["gold"], FOLDER_ENTRANCE, tags=["FrontOffice"]
    )
    spawn_cube(
        "BackOfficeFloor", (0.0, 700.0, 10.0), (800.0, 600.0, 20.0),
        MATERIALS["concrete"], FOLDER_ENTRANCE, tags=["BackOffice", "8x6m"]
    )
    spawn_cube(
        "BackOfficeRearWall", (0.0, 990.0, 160.0), (800.0, 24.0, 320.0),
        MATERIALS["facade_light"], FOLDER_ENTRANCE, tags=["BackOffice", "8x6m"]
    )
    for x in (-400.0, 400.0):
        spawn_cube(
            "BackOfficeSide_{:+.0f}".format(x), (x, 700.0, 160.0), (24.0, 600.0, 320.0),
            MATERIALS["facade_light"], FOLDER_ENTRANCE, tags=["BackOffice", "8x6m"]
        )
    # Two short return walls preserve a central staff doorway from the lobby.
    spawn_cube(
        "BackOfficeFrontReturnLeft", (-300.0, 410.0, 160.0), (200.0, 24.0, 320.0),
        MATERIALS["facade_light"], FOLDER_ENTRANCE, tags=["BackOffice", "8x6m"]
    )
    spawn_cube(
        "BackOfficeFrontReturnRight", (300.0, 410.0, 160.0), (200.0, 24.0, 320.0),
        MATERIALS["facade_light"], FOLDER_ENTRANCE, tags=["BackOffice", "8x6m"]
    )
    spawn_cylinder(
        "LobbyCentralPlanter", (0.0, -820.0, 42.0), (300.0, 300.0, 84.0),
        MATERIALS["facade_dark"], FOLDER_ENTRANCE, tags=["Lobby"]
    )
    spawn_sphere(
        "LobbyCentralPlant", (0.0, -820.0, 138.0), 215.0,
        MATERIALS["green"], FOLDER_ENTRANCE, collision=False, tags=["Lobby"]
    )
    for index, (x, y) in enumerate(((-430.0, -1080.0), (430.0, -1080.0),
                                    (-430.0, -610.0), (430.0, -610.0))):
        spawn_cube(
            "LobbyBench_{:02d}".format(index + 1), (x, y, 42.0), (250.0, 78.0, 84.0),
            MATERIALS["wood"], FOLDER_ENTRANCE, tags=["LobbyFurniture"]
        )


def build_closed_seventh_interior():
    # Sixteen actual enclosed spaces, with doors aligned with their room windows.
    # The central slab connects both wing corridors; no solid seventh-floor mass.
    base = SEVENTH_BASE_Z
    wall_height = SEVENTH_HEIGHT - 24.0
    z = base + 24.0 + wall_height * 0.5
    for wing, xs, first_room, center, width in (
        ("A", evenly_spaced(-4550.0, -1650.0, 8), 701,
         LEFT_WING_CENTER_X, LEFT_SEVENTH_WIDTH),
        ("B", evenly_spaced(1500.0, 4300.0, 8), 709,
         RIGHT_WING_CENTER_X, RIGHT_SEVENTH_WIDTH),
    ):
        spawn_cube("Floor7_Slab_" + wing, (center, 535.0, base + 12.0),
                   (width, SEVENTH_DEPTH, 24.0), MATERIALS["concrete"],
                   FOLDER_SERVICE, tags=["ClosedFloor7", "Wing" + wing])
        spawn_cube("Floor7_RearWall_" + wing, (center, 2620.0, z),
                   (width, 30.0, wall_height), MATERIALS["facade_dark"], FOLDER_EXTERIOR)
        boundaries = [xs[0] - (xs[1] - xs[0]) * 0.5]
        boundaries.extend((a + b) * 0.5 for a, b in zip(xs, xs[1:]))
        boundaries.append(xs[-1] + (xs[-1] - xs[-2]) * 0.5)
        for index, x in enumerate(boundaries):
            spawn_cube("Floor7_Partition_{}_{:02d}".format(wing, index),
                       (x, -1150.0, z), (18.0, 860.0, wall_height),
                       MATERIALS["interior"], FOLDER_SERVICE,
                       tags=["ClosedFloor7", "RoomPartition"])
        for index, x in enumerate(xs):
            room = first_room + index
            tags = ["ClosedFloor7", "Room{}".format(room), "Wing" + wing]
            if room == 713:
                tags.append("Room713Exists")
            room_width = boundaries[index + 1] - boundaries[index]
            # The exterior wall has a real opening around the separate glass pane.
            window_width = 180.0 if wing == "A" else 210.0
            window_height = 175.0 if wing == "A" else 185.0
            sill = 190.0 - window_height * 0.5
            top = 190.0 + window_height * 0.5
            spawn_cube("Room{}_SillWall".format(room),
                       (x, -1584.0, base + (24.0 + sill) * 0.5),
                       (room_width, 30.0, sill - 24.0), MATERIALS["facade_dark"], FOLDER_EXTERIOR)
            spawn_cube("Room{}_HeadWall".format(room),
                       (x, -1584.0, base + (top + SEVENTH_HEIGHT) * 0.5),
                       (room_width, 30.0, SEVENTH_HEIGHT - top),
                       MATERIALS["facade_dark"], FOLDER_EXTERIOR)
            for side in (-1, 1):
                pier_width = (room_width - window_width) * 0.5
                spawn_cube("Room{}_WindowPier_{:+d}".format(room, side),
                           (x + side * (window_width + pier_width) * 0.5, -1584.0,
                            base + 190.0), (pier_width, 30.0, window_height),
                           MATERIALS["facade_dark"], FOLDER_EXTERIOR)
                return_width = (room_width - 112.0) * 0.5
                spawn_cube("Room{}_DoorReturn_{:+d}".format(room, side),
                           (x + side * (112.0 + return_width) * 0.5, -720.0, z),
                           (return_width, 18.0, wall_height), MATERIALS["interior"],
                           FOLDER_SERVICE, tags=tags)
            spawn_cube("Room{}_DoorHeader".format(room),
                       (x, -720.0, base + 24.0 + 220.0 + (wall_height - 220.0) * 0.5),
                       (112.0, 18.0, wall_height - 220.0), MATERIALS["interior"], FOLDER_SERVICE)
            spawn_cube("Room{}_Door".format(room), (x, -720.0, base + 134.0),
                       (106.0, 12.0, 220.0), MATERIALS["wood"], FOLDER_SERVICE,
                       tags=tags + ["ClosedStaffAccess", "DoorInteractionBlueprintRequired"])


def build_roof():
    # Roof decks and parapets follow the stepped historic silhouette in the reference.
    for label, x, width in (
        ("A", LEFT_WING_CENTER_X, LEFT_SEVENTH_WIDTH),
        ("B", RIGHT_WING_CENTER_X, RIGHT_SEVENTH_WIDTH),
    ):
        spawn_cube(
            "RoofDeck_" + label, (x, SEVENTH_CENTER_Y + 35.0, MAIN_ROOF_Z + 12.0),
            (width, SEVENTH_DEPTH, 24.0), MATERIALS["roof"], FOLDER_ROOF,
            tags=["RoofDeck"]
        )
        spawn_cube(
            "ParapetFront_" + label, (x, -1575.0, MAIN_ROOF_Z + 60.0),
            (width, 34.0, 120.0), MATERIALS["facade_dark"], FOLDER_ROOF,
            tags=["Parapet"]
        )
        spawn_cube(
            "ParapetRear_" + label, (x, 2675.0, MAIN_ROOF_Z + 60.0),
            (width, 34.0, 120.0), MATERIALS["facade_dark"], FOLDER_ROOF,
            tags=["Parapet"]
        )

    for label, x, y_len in (
        ("A_West", -4868.0, SEVENTH_DEPTH),
        ("A_East", -1332.0, SEVENTH_DEPTH),
        ("B_West", 1332.0, SEVENTH_DEPTH),
        ("B_East", 4468.0, SEVENTH_DEPTH),
    ):
        spawn_cube(
            "ParapetSide_" + label, (x, SEVENTH_CENTER_Y + 35.0, MAIN_ROOF_Z + 60.0),
            (34.0, y_len, 120.0), MATERIALS["facade_dark"], FOLDER_ROOF,
            tags=["Parapet"]
        )

    # Stepped approximation of the reference's shallow arched crown.
    crown_xs = evenly_spaced(-900.0, 900.0, 9)
    for index, x in enumerate(crown_xs):
        normalized = abs(x) / 900.0
        extra_height = 70.0 + 170.0 * (1.0 - normalized * normalized)
        spawn_cube(
            "CentralArchCrown_{:02d}".format(index),
            (x, -1455.0, MAIN_ROOF_Z + extra_height * 0.5),
            (225.0, 48.0, extra_height), MATERIALS["metal"], FOLDER_ROOF,
            tags=["ReferenceArchCrown"]
        )
    spawn_cube(
        "CentralCrownTopRail", (0.0, -1484.0, MAIN_ROOF_Z + 242.0),
        (1900.0, 26.0, 24.0), MATERIALS["gold"], FOLDER_ROOF,
        collision=False, tags=["ReferenceArchCrown"]
    )

    # Rooftop service cores: only S2 and Stair C continue above the closed floor.
    spawn_cube(
        "ServiceElevatorS2_RoofOverrun", (3480.0, 1820.0, MAIN_ROOF_Z + 225.0),
        (430.0, 430.0, 450.0), MATERIALS["facade_dark"], FOLDER_ROOF,
        tags=["ServiceElevatorS2", "ReachesFloor7"]
    )
    spawn_cube(
        "StaffStairC_RoofHead", (-4100.0, 1820.0, MAIN_ROOF_Z + 190.0),
        (520.0, 620.0, 380.0), MATERIALS["facade_dark"], FOLDER_ROOF,
        tags=["StaffStairC", "ReachesFloor7"]
    )

    # Mechanical plant is low, ordered, and hidden behind parapets from street level.
    mechanical_positions = (
        (-3800.0, 1300.0), (-3000.0, 1500.0), (-2200.0, 1300.0),
        (2050.0, 1450.0), (2800.0, 1250.0), (3600.0, 1450.0),
    )
    for index, (x, y) in enumerate(mechanical_positions):
        spawn_cube(
            "HVAC_{:02d}".format(index + 1), (x, y, MAIN_ROOF_Z + 72.0),
            (420.0, 260.0, 120.0), MATERIALS["metal"], FOLDER_ROOF,
            tags=["RoofMechanical"]
        )
        for grille in (-120.0, 0.0, 120.0):
            spawn_cube(
                "HVAC_{:02d}_Grille_{:+.0f}".format(index + 1, grille),
                (x + grille, y - 136.0, MAIN_ROOF_Z + 72.0),
                (8.0, 12.0, 82.0), MATERIALS["facade_dark"], FOLDER_ROOF,
                collision=False, tags=["RoofMechanical"]
            )
    for index, (x, y) in enumerate(((-2600.0, 2050.0), (2450.0, 2050.0), (3300.0, 2100.0))):
        spawn_cylinder(
            "RoofVent_{:02d}".format(index + 1), (x, y, MAIN_ROOF_Z + 95.0),
            (70.0, 70.0, 190.0), MATERIALS["metal"], FOLDER_ROOF,
            tags=["RoofMechanical"]
        )


def build_service():
    # Physical vertical cores. They are mostly embedded in the building mass but remain selectable.
    spawn_cube(
        "GuestElevatorCore", (800.0, 680.0, SEVENTH_BASE_Z * 0.5),
        (340.0, 360.0, SEVENTH_BASE_Z), MATERIALS["concrete"], FOLDER_SERVICE,
        tags=["GuestElevators", "StopsAtFloor6", "DoesNotReachFloor7"]
    )
    spawn_cube(
        "ServiceElevatorS2_Shaft", (3480.0, 1820.0, MAIN_ROOF_Z * 0.5),
        (400.0, 400.0, MAIN_ROOF_Z), MATERIALS["concrete"], FOLDER_SERVICE,
        tags=["ServiceElevatorS2", "ReachesFloor7"]
    )
    spawn_cube(
        "StaffStairC_Core", (-4100.0, 1820.0, MAIN_ROOF_Z * 0.5),
        (490.0, 590.0, MAIN_ROOF_Z), MATERIALS["concrete"], FOLDER_SERVICE,
        tags=["StaffStairC", "ReachesFloor7"]
    )

    build_closed_seventh_interior()

    # Rear loading/service court, doors and protective canopy.
    spawn_cube(
        "ServiceYard", (3150.0, 3650.0, -4.0), (3900.0, 1500.0, 16.0),
        MATERIALS["asphalt"], FOLDER_SERVICE, tags=["ServiceYard"]
    )
    spawn_cube(
        "LoadingDock", (3150.0, 2915.0, 55.0), (2200.0, 250.0, 110.0),
        MATERIALS["concrete"], FOLDER_SERVICE, tags=["LoadingDock"]
    )
    for index, x in enumerate((2500.0, 3150.0, 3800.0)):
        spawn_cube(
            "LoadingDoor_{:02d}".format(index + 1), (x, REAR_Y + 18.0, 165.0),
            (420.0, 34.0, 330.0), MATERIALS["metal"], FOLDER_SERVICE,
            tags=["ServiceDoor"]
        )
        for strip in (-120.0, -40.0, 40.0, 120.0):
            spawn_cube(
                "LoadingDoor_{:02d}_Slat_{:+.0f}".format(index + 1, strip),
                (x, REAR_Y + 38.0, 165.0 + strip), (390.0, 10.0, 10.0),
                MATERIALS["facade_dark"], FOLDER_SERVICE, collision=False,
                tags=["ServiceDoor"]
            )
    spawn_cube(
        "LoadingCanopy", (3150.0, 3150.0, 385.0), (2400.0, 700.0, 34.0),
        MATERIALS["roof"], FOLDER_SERVICE, tags=["ServiceCanopy"]
    )


def build_tree(index, x, y, size=1.0):
    spawn_cylinder(
        "Tree_{:02d}_Trunk".format(index), (x, y, 150.0 * size),
        (42.0 * size, 42.0 * size, 300.0 * size), MATERIALS["wood"], FOLDER_SITE,
        tags=["LandscapeTree"]
    )
    spawn_sphere(
        "Tree_{:02d}_CanopyA".format(index), (x, y, 365.0 * size),
        330.0 * size, MATERIALS["green"], FOLDER_SITE, collision=False,
        tags=["LandscapeTree"]
    )
    spawn_sphere(
        "Tree_{:02d}_CanopyB".format(index), (x + 90.0 * size, y - 30.0 * size, 395.0 * size),
        250.0 * size, MATERIALS["green"], FOLDER_SITE, collision=False,
        tags=["LandscapeTree"]
    )


def build_site():
    # Broad but compact urban parcel; the hotel remains the dominant object.
    spawn_cube(
        "SiteBase", (0.0, 0.0, -35.0), (13000.0, 10500.0, 50.0),
        MATERIALS["concrete"], FOLDER_SITE, tags=["SiteBase"]
    )
    spawn_cube(
        "PublicRoad", (0.0, -5350.0, -3.0), (13200.0, 1700.0, 18.0),
        MATERIALS["asphalt"], FOLDER_SITE, tags=["PublicRoad"]
    )
    spawn_cube(
        "DropOffLane", (0.0, -3560.0, 2.0), (8200.0, 1350.0, 22.0),
        MATERIALS["asphalt"], FOLDER_SITE, tags=["DropOff", "VehicleLane"]
    )
    spawn_cube(
        "DropOffPaving", (0.0, -2520.0, 7.0), (4200.0, 1100.0, 26.0),
        MATERIALS["paving"], FOLDER_SITE, tags=["DropOff", "Pedestrian"]
    )
    spawn_cube(
        "MainWalk", (0.0, -4300.0, 8.0), (1250.0, 2500.0, 28.0),
        MATERIALS["paving"], FOLDER_SITE, tags=["MainEntranceWalk"]
    )
    spawn_cube(
        "EastServiceRoad", (5350.0, 550.0, -1.0), (850.0, 7200.0, 18.0),
        MATERIALS["asphalt"], FOLDER_SITE, tags=["ServiceAccess"]
    )

    # Curbs define the loop and porte-cochere landing zone.
    curb_specs = (
        ("DropOffNorth", 0.0, -2965.0, 8200.0, 26.0),
        ("DropOffSouth", 0.0, -4245.0, 8200.0, 26.0),
        ("WalkWest", -645.0, -4300.0, 26.0, 2500.0),
        ("WalkEast", 645.0, -4300.0, 26.0, 2500.0),
        ("ServiceWest", 4920.0, 550.0, 26.0, 7200.0),
        ("ServiceEast", 5780.0, 550.0, 26.0, 7200.0),
    )
    for label, x, y, width, depth in curb_specs:
        spawn_cube(
            "Curb_" + label, (x, y, 21.0), (width, depth, 30.0),
            MATERIALS["facade_light"], FOLDER_SITE, tags=["Curb"]
        )

    # Symmetrical planted beds echo the reference forecourt landscaping.
    planter_specs = (
        (-3650.0, -2570.0, 2200.0, 560.0),
        (3650.0, -2570.0, 2200.0, 560.0),
        (-4550.0, -900.0, 650.0, 2200.0),
        (4550.0, -900.0, 650.0, 2200.0),
        (-1850.0, -1880.0, 1050.0, 360.0),
        (1850.0, -1880.0, 1050.0, 360.0),
    )
    for index, (x, y, width, depth) in enumerate(planter_specs):
        spawn_cube(
            "Planter_{:02d}_Edge".format(index + 1), (x, y, 32.0),
            (width + 36.0, depth + 36.0, 54.0), MATERIALS["facade_dark"], FOLDER_SITE,
            tags=["LandscapeBed"]
        )
        spawn_cube(
            "Planter_{:02d}_Green".format(index + 1), (x, y, 61.0),
            (width, depth, 24.0), MATERIALS["green"], FOLDER_SITE,
            collision=False, tags=["LandscapeBed"]
        )

    tree_positions = (
        (-4400.0, -2550.0, 0.90), (-3500.0, -2550.0, 1.05),
        (3500.0, -2550.0, 1.05), (4400.0, -2550.0, 0.90),
        (-4700.0, -900.0, 1.10), (-4700.0, 650.0, 1.00),
        (4700.0, -900.0, 1.10), (4700.0, 650.0, 1.00),
        (-5600.0, 2200.0, 1.15), (5600.0, 2200.0, 1.15),
    )
    for index, (x, y, scale) in enumerate(tree_positions):
        build_tree(index + 1, x, y, scale)

    # Low bollards around the guest landing area.
    for index, x in enumerate(evenly_spaced(-1500.0, 1500.0, 9)):
        spawn_cylinder(
            "Bollard_{:02d}".format(index + 1), (x, -3070.0, 45.0),
            (18.0, 18.0, 90.0), MATERIALS["metal"], FOLDER_SITE,
            tags=["DropOffBollard"]
        )


def build_preview_lighting():
    # Movable-only helper lights; existing sun, skylight and atmosphere are untouched.
    light_specs = (
        ("EntrancePreviewLight_L", (-650.0, -2320.0, 350.0), 2600.0, 1550.0),
        ("EntrancePreviewLight_R", (650.0, -2320.0, 350.0), 2600.0, 1550.0),
        ("LobbyPreviewLight", (0.0, -650.0, 420.0), 1900.0, 1250.0),
    )
    for label, location, intensity, radius in light_specs:
        actor = ACTOR_SUBSYSTEM.spawn_actor_from_class(
            unreal.PointLight,
            unreal.Vector(float(location[0]), float(location[1]), float(location[2])),
            unreal.Rotator(pitch=0.0, yaw=0.0, roll=0.0),
        )
        if actor is None:
            raise RuntimeError("Unable to spawn preview light: " + label)
        if actor:
            set_actor_identity(actor, label, FOLDER_ENTRANCE, ["PreviewLighting", "MovableOnly"])
            actor.set_editor_property("is_editor_only_actor", True)
            component = actor.get_component_by_class(unreal.PointLightComponent)
            component.set_mobility(unreal.ComponentMobility.MOVABLE)
            component.set_intensity_units(unreal.LightUnits.LUMENS)
            component.set_intensity(float(intensity))
            component.set_attenuation_radius(float(radius))
            component.set_light_color(
                unreal.LinearColor(1.0, 0.59, 0.29, 1.0),
                False,
            )
            component.set_editor_property("cast_shadows", True)


def validate_generated_hotel():
    labels = [actor.get_actor_label() for actor in CREATED_ACTORS]
    if len(labels) != len(set(labels)):
        raise RuntimeError("Duplicate generated actor labels.")
    if any(not label.startswith(ACTOR_PREFIX) for label in labels):
        raise RuntimeError("Generated actor is missing its required prefix.")
    if any(actor.get_level() != TARGET_LEVEL for actor in CREATED_ACTORS):
        raise RuntimeError("An actor was spawned outside L_PrototypeEntry.")
    for floor in ACTIVE_GUEST_FLOORS:
        for wing, count in (("A", 40), ("B", 20)):
            prefix = ACTOR_PREFIX + "Window_F{}_{}_".format(floor, wing)
            if sum(label.startswith(prefix) for label in labels) != count:
                raise RuntimeError("Incorrect guest window count: " + prefix)
    for room in range(701, 717):
        if ACTOR_PREFIX + "Room{}_Door".format(room) not in labels:
            raise RuntimeError("Missing closed-floor door: " + str(room))
    for actor in CREATED_ACTORS:
        light = actor.get_component_by_class(unreal.PointLightComponent)
        if light and light.get_editor_property("mobility") != unreal.ComponentMobility.MOVABLE:
            raise RuntimeError("Generated preview light must be MOVABLE.")


def initialise_resources():
    global ACTOR_SUBSYSTEM, ASSET_TOOLS, CUBE_MESH, CYLINDER_MESH, SPHERE_MESH, MATERIALS
    ACTOR_SUBSYSTEM = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    ASSET_TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
    CUBE_MESH = unreal.EditorAssetLibrary.load_asset(CUBE_PATH)
    CYLINDER_MESH = unreal.EditorAssetLibrary.load_asset(CYLINDER_PATH)
    SPHERE_MESH = unreal.EditorAssetLibrary.load_asset(SPHERE_PATH)
    if not ACTOR_SUBSYSTEM:
        raise RuntimeError("EditorActorSubsystem is unavailable.")
    if not CUBE_MESH or not CYLINDER_MESH or not SPHERE_MESH:
        raise RuntimeError("One or more built-in BasicShapes could not be loaded.")
    MATERIALS = create_materials()


def build_hotel():
    global TARGET_LEVEL
    try:
        validate_api()
        TARGET_LEVEL = require_target_level()
    except RuntimeError as exc:
        unreal.log_error("ReferenceHotel aborted: " + str(exc))
        return

    CREATED_ACTORS.clear()
    initialise_resources()

    with unreal.ScopedEditorTransaction("Build Reference Hotel"):
        delete_previous_generated_actors()
        try:
            build_main_mass()
            build_facade_modules()
            build_windows()
            build_entrance()
            build_roof()
            build_service()
            build_site()
            build_preview_lighting()
            validate_generated_hotel()
        except Exception:
            # A failed build never reports success; Ctrl+Z restores the previous
            # generation through this editor transaction. No map is auto-saved.
            unreal.log_error("ReferenceHotel failed. Use Undo to restore the previous generation.")
            raise

    unreal.log(
        "ReferenceHotel complete: {} actors created in {}. "
        "Active room-window markers: 300; closed seventh-floor rooms: 701-716; Room 713 present.".format(
            len(CREATED_ACTORS), REQUIRED_LEVEL
        )
    )


build_hotel()
