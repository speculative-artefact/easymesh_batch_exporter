"""Pytest configuration and fixtures for EasyMesh Batch Exporter tests.

This module provides shared fixtures and utilities for testing the addon,
including addon enablement, temporary directories, and verification helpers.
"""

import bpy
import pytest
import shutil
import tempfile
from pathlib import Path
from typing import List


# --- Addon Management Fixtures ---


@pytest.fixture(scope="session", autouse=True)
def enable_addon():
    """Enable the mesh exporter addon for all tests.

    This fixture runs once at the start of the test session and ensures
    the addon is enabled. It handles both legacy addons and Blender 4.2+
    extension-style addons.
    """
    # Possible addon names (legacy and extension formats)
    addon_names = [
        "easymesh_batch_exporter",
        "bl_ext.vscode_development.mesh_exporter",
        "bl_ext.user_default.easymesh_batch_exporter",
    ]

    # Check if addon is already enabled under any name
    addon_enabled = False

    for addon_name in addon_names:
        if addon_name in bpy.context.preferences.addons:
            addon_enabled = True
            print(f"Addon already enabled: {addon_name}")
            break

    # Also check if mesh_exporter property exists (addon registered)
    if not addon_enabled and hasattr(bpy.context.scene, "mesh_exporter"):
        addon_enabled = True
        print("Addon detected via mesh_exporter property")

    # Try to enable if not already enabled
    if not addon_enabled:
        for addon_name in addon_names:
            try:
                bpy.ops.preferences.addon_enable(module=addon_name)
                print(f"Enabled addon: {addon_name}")
                addon_enabled = True
                break
            except Exception:
                continue

    # Final verification - check if the mesh_exporter property is available
    if not hasattr(bpy.context.scene, "mesh_exporter"):
        pytest.fail("Addon mesh_exporter properties not found. Is the addon enabled?")

    yield

    # Cleanup: Optionally disable addon after all tests
    # Uncomment if you want to disable after tests
    # for addon_name in addon_names:
    #     if addon_name in bpy.context.preferences.addons:
    #         bpy.ops.preferences.addon_disable(module=addon_name)


# --- Scene Management Fixtures ---


@pytest.fixture(autouse=True)
def clean_scene():
    """Clean the scene before each test.

    Removes all objects, collections, and materials to ensure a clean state.
    Runs automatically before every test.
    """
    # Switch to object mode
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")

    # Select and delete all objects
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()

    # Remove all collections except the default Scene Collection
    for collection in bpy.data.collections:
        bpy.data.collections.remove(collection)

    # Clear all materials
    for material in bpy.data.materials:
        bpy.data.materials.remove(material)

    # Clear all meshes
    for mesh in bpy.data.meshes:
        bpy.data.meshes.remove(mesh)

    yield

    # Cleanup after test (same as before)
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()


@pytest.fixture
def temp_export_dir():
    """Create a temporary directory for export tests.

    Yields:
        Path: Path to the temporary export directory

    The directory and all its contents are automatically cleaned up after the test.
    """
    temp_dir = tempfile.mkdtemp(prefix="blender_export_test_")
    temp_path = Path(temp_dir)

    yield temp_path

    # Cleanup: Remove the temporary directory
    if temp_path.exists():
        shutil.rmtree(temp_path)


# --- Test Object Creation Fixtures ---


@pytest.fixture
def create_cube():
    """Create a simple cube mesh for testing.

    Returns:
        bpy.types.Object: The created cube object
    """
    bpy.ops.mesh.primitive_cube_add(location=(0, 0, 0))
    obj = bpy.context.active_object
    obj.name = "TestCube"
    return obj


@pytest.fixture
def create_sphere():
    """Create a UV sphere mesh for testing.

    Returns:
        bpy.types.Object: The created sphere object
    """
    bpy.ops.mesh.primitive_uv_sphere_add(location=(0, 0, 0))
    obj = bpy.context.active_object
    obj.name = "TestSphere"
    return obj


@pytest.fixture
def create_curve():
    """Create a bezier curve for testing.

    Returns:
        bpy.types.Object: The created curve object
    """
    bpy.ops.curve.primitive_bezier_circle_add(location=(0, 0, 0))
    obj = bpy.context.active_object
    obj.name = "TestCurve"
    return obj


@pytest.fixture
def create_large_mesh():
    """Create a large mesh with 500K+ polygons for memory testing.

    Returns:
        bpy.types.Object: The created large mesh object

    Note:
        This uses a subdivided UV sphere to quickly generate many polygons.
    """
    bpy.ops.mesh.primitive_uv_sphere_add(location=(0, 0, 0))
    obj = bpy.context.active_object
    obj.name = "TestLargeMesh"

    # Add subdivision modifier to increase polygon count
    mod = obj.modifiers.new(name="Subsurf", type="SUBSURF")
    mod.levels = 6  # This creates ~500K+ polygons
    mod.render_levels = 6

    return obj


@pytest.fixture
def create_very_large_mesh():
    """Create a very large mesh with 2M+ polygons for aggressive memory testing.

    Returns:
        bpy.types.Object: The created very large mesh object

    Note:
        This uses a highly subdivided mesh. May take several seconds to create.
    """
    bpy.ops.mesh.primitive_uv_sphere_add(location=(0, 0, 0))
    obj = bpy.context.active_object
    obj.name = "TestVeryLargeMesh"

    # Add subdivision modifier to increase polygon count significantly
    mod = obj.modifiers.new(name="Subsurf", type="SUBSURF")
    mod.levels = 7  # This creates ~2M+ polygons
    mod.render_levels = 7

    return obj


# --- Utility Functions ---


def verify_file_exists(file_path: Path, file_format: str = None) -> bool:
    """Verify that an exported file exists.

    Args:
        file_path: Path to the exported file
        file_format: Optional file format extension to verify (e.g., 'fbx', 'obj')

    Returns:
        bool: True if file exists and matches format, False otherwise
    """
    if not file_path.exists():
        return False

    if file_format:
        return file_path.suffix.lower() == f".{file_format.lower()}"

    return True


def verify_exported_files(
    export_dir: Path, expected_files: List[str], file_format: str
) -> bool:
    """Verify that expected files were exported.

    Args:
        export_dir: Directory containing exported files
        expected_files: List of expected base filenames (without extension)
        file_format: Expected file format extension (e.g., 'fbx', 'obj')

    Returns:
        bool: True if all expected files exist, False otherwise
    """
    for base_name in expected_files:
        file_path = export_dir / f"{base_name}.{file_format}"
        if not verify_file_exists(file_path, file_format):
            print(f"Missing expected file: {file_path}")
            return False
    return True


def count_exported_files(export_dir: Path, file_format: str) -> int:
    """Count the number of exported files in a directory.

    Args:
        export_dir: Directory containing exported files
        file_format: File format extension to count (e.g., 'fbx', 'obj')

    Returns:
        int: Number of files with the specified format
    """
    pattern = f"*.{file_format}"
    return len(list(export_dir.glob(pattern)))


def get_scene_props():
    """Get the mesh exporter property group from the current scene.

    Returns:
        MeshExporterSettings: The property group instance

    Raises:
        AttributeError: If the addon is not properly enabled
    """
    if not hasattr(bpy.context.scene, "mesh_exporter"):
        raise AttributeError(
            "mesh_exporter properties not found. Is the addon enabled?"
        )
    return bpy.context.scene.mesh_exporter


def reset_export_settings():
    """Reset all export settings to their defaults.

    This is useful for ensuring tests start with a known state.
    """
    props = get_scene_props()

    # Reset to default values
    props.mesh_export_path = "//exported_meshes/"
    props.mesh_export_format = "FBX"
    props.mesh_export_scale = 1.0
    props.mesh_export_units = "METERS"
    props.mesh_export_coord_up = "Z"
    props.mesh_export_coord_forward = "X"
    props.mesh_export_smoothing = "FACE"
    props.mesh_export_zero_location = True
    props.mesh_export_tri = True
    props.mesh_export_tri_method = "BEAUTY"
    props.mesh_export_keep_normals = True
    props.mesh_export_apply_modifiers = "VISIBLE"
    # Baseline with naming disabled so the broad suite expects original
    # (sanitised) filenames; convention tests opt in explicitly.
    props.mesh_export_naming_enabled = False
    props.mesh_export_prefix = ""
    props.mesh_export_suffix = ""
    props.mesh_export_naming_convention = "GODOT"
    props.mesh_export_lod = False
    props.mesh_export_lod_count = 4
    props.mesh_export_lod_hierarchy = True
    props.mesh_export_gltf_batch_mode = "COMBINE"
    props.mesh_export_embed_textures = True

    # Attachment points and slot empties
    props.mesh_export_include_empties = True
    props.mesh_export_empty_filter = "ALL"
    props.mesh_export_empty_prefix = "attach_"
    props.mesh_export_create_slots = False
    props.mesh_export_slot_prefix = "slot_"

    # Collision meshes (disabled by default so other tests are unaffected)
    props.mesh_export_include_collisions = False
    props.mesh_export_collision_filter = "PREFIXED"
    props.mesh_export_collision_profile = "NONE"
    props.mesh_export_collision_godot_visual = False
    props.mesh_export_collision_custom_prefix = "UCX_"
    props.mesh_export_collision_custom_suffix = ""


@pytest.fixture
def reset_settings():
    """Fixture to reset export settings before each test.

    Automatically resets all export settings to defaults before running each test.
    """
    reset_export_settings()
    yield
    # Optionally reset after test as well
    # reset_export_settings()


# --- Collection Fixtures ---


@pytest.fixture
def create_collection():
    """Create a test collection with multiple objects.

    Returns:
        bpy.types.Collection: The created collection with 3 cube objects
    """
    # Create a new collection
    collection = bpy.data.collections.new("TestCollection")
    bpy.context.scene.collection.children.link(collection)

    # Create multiple objects in the collection
    for i in range(3):
        bpy.ops.mesh.primitive_cube_add(location=(i * 2, 0, 0))
        obj = bpy.context.active_object
        obj.name = f"TestCube_{i}"

        # Unlink from scene collection and link to test collection
        bpy.context.scene.collection.objects.unlink(obj)
        collection.objects.link(obj)

    return collection


# --- Attachment Points Fixtures ---


@pytest.fixture
def create_mesh_with_empty_children():
    """Create a mesh with empty children (attachment points).

    Creates a parent cube with two empty children positioned at different
    locations, useful for testing attachment point export.

    Returns:
        bpy.types.Object: The parent mesh object with empty children
    """
    bpy.ops.mesh.primitive_cube_add(location=(0, 0, 0))
    parent = bpy.context.active_object
    parent.name = "TestParent"

    # Create empty children
    empties_data = [
        ("attach_hat", (0, 0, 1)),
        ("attach_hand", (1, 0, 0)),
    ]
    for name, loc in empties_data:
        empty = bpy.data.objects.new(name, None)
        empty.empty_display_type = "PLAIN_AXES"
        empty.location = loc
        empty.parent = parent
        bpy.context.collection.objects.link(empty)

    return parent


@pytest.fixture
def create_mesh_with_mixed_empties():
    """Create a mesh with both prefixed and non-prefixed empty children.

    Creates a parent cube with four empty children - two with 'attach_' prefix
    and two without, for testing the prefix filter functionality.

    Returns:
        bpy.types.Object: The parent mesh object with mixed empty children
    """
    bpy.ops.mesh.primitive_cube_add(location=(0, 0, 0))
    parent = bpy.context.active_object
    parent.name = "TestParentMixed"

    # Create empty children with and without prefix
    empties_data = [
        ("attach_socket1", (0, 0, 1)),  # Prefixed
        ("attach_socket2", (1, 0, 0)),  # Prefixed
        ("other_empty", (0, 1, 0)),  # Not prefixed
        ("helper_point", (-1, 0, 0)),  # Not prefixed
    ]
    for name, loc in empties_data:
        empty = bpy.data.objects.new(name, None)
        empty.empty_display_type = "PLAIN_AXES"
        empty.location = loc
        empty.parent = parent
        bpy.context.collection.objects.link(empty)

    return parent


@pytest.fixture
def create_mesh_with_unreal_collisions():
    """Create a render mesh with UCX_ and UBX_ collision children.

    The collision children follow Unreal's source-name convention so the
    collision filter can detect them and read their shape from the prefix.

    Returns:
        bpy.types.Object: The parent render mesh with collision children
    """
    bpy.ops.mesh.primitive_cube_add(location=(0, 0, 0))
    parent = bpy.context.active_object
    parent.name = "CollisionParent"

    # Convex hull and box collisions, named for their parent.
    collision_data = [
        ("UCX_CollisionParent", (0, 0, 0)),
        ("UBX_CollisionParent", (0, 0, 0)),
    ]
    for name, loc in collision_data:
        bpy.ops.mesh.primitive_cube_add(location=loc)
        child = bpy.context.active_object
        child.name = name
        child.parent = parent

    # Leave the parent active/selected as the entry point for export.
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = parent
    return parent


@pytest.fixture
def create_mesh_with_mesh_children():
    """Create a mesh with mesh children (for slot empties testing).

    Creates a parent cube with two child mesh spheres, useful for testing
    automatic slot empty generation at child positions.

    Returns:
        bpy.types.Object: The parent mesh object with mesh children
    """
    bpy.ops.mesh.primitive_cube_add(location=(0, 0, 0))
    parent = bpy.context.active_object
    parent.name = "TestParentWithMeshChildren"

    # Create mesh children
    child_data = [
        ("ChildMesh_A", (2, 0, 0)),
        ("ChildMesh_B", (0, 2, 0)),
    ]
    for name, loc in child_data:
        bpy.ops.mesh.primitive_uv_sphere_add(location=loc)
        child = bpy.context.active_object
        child.name = name
        child.parent = parent

    return parent
