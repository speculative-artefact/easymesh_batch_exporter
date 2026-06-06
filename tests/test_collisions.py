"""Tests for custom collision mesh export functionality.

These tests cover detecting collision mesh children, renaming them per the
target engine profile (Unreal/Godot/Custom), including them in the same output
file as their render mesh, and excluding them from standalone export.

Naming is verified by exporting glTF in JSON (GLTF_SEPARATE) form and inspecting
the node names, which is the most reliable way to confirm the engine convention
was applied.
"""

import json

import bpy
from conftest import (
    verify_file_exists,
    count_exported_files,
    get_scene_props,
)


def _gltf_node_names(gltf_path):
    """Return the list of node names from a JSON .gltf file."""
    with open(gltf_path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    return [node.get("name", "") for node in data.get("nodes", [])]


class TestCollisionDetection:
    """Tests for detecting and including collision meshes."""

    def test_fbx_includes_collisions(
        self, create_mesh_with_unreal_collisions, temp_export_dir, reset_settings
    ):
        """FBX export of a mesh with UCX_/UBX_ children should succeed."""
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"
        props.mesh_export_include_collisions = True
        props.mesh_export_collision_filter = "PREFIXED"
        props.mesh_export_collision_profile = "UNREAL"

        parent = create_mesh_with_unreal_collisions
        parent.select_set(True)

        result = bpy.ops.mesh.batch_export()
        assert result == {"FINISHED"}, "FBX export with collisions should succeed"

        # Only the parent's file should be written - collisions ride inside it.
        assert verify_file_exists(temp_export_dir / "CollisionParent.fbx", "fbx")
        assert count_exported_files(temp_export_dir, "fbx") == 1

    def test_collisions_disabled(
        self, create_mesh_with_unreal_collisions, temp_export_dir, reset_settings
    ):
        """With collisions disabled, only the render mesh is exported."""
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"
        props.mesh_export_include_collisions = False

        parent = create_mesh_with_unreal_collisions
        parent.select_set(True)

        result = bpy.ops.mesh.batch_export()
        assert result == {"FINISHED"}, "Export without collisions should succeed"
        assert verify_file_exists(temp_export_dir / "CollisionParent.fbx", "fbx")

    def test_filter_all_children(self, temp_export_dir, reset_settings):
        """ALL filter treats every mesh child as a convex collision."""
        bpy.ops.mesh.primitive_cube_add(location=(0, 0, 0))
        parent = bpy.context.active_object
        parent.name = "AllFilterParent"

        bpy.ops.mesh.primitive_cube_add(location=(0, 0, 0))
        child = bpy.context.active_object
        child.name = "PlainCollider"  # No prefix
        child.parent = parent

        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "GLTF"
        props.mesh_export_gltf_type = "GLTF_SEPARATE"
        props.mesh_export_gltf_batch_mode = "INDIVIDUAL"
        props.mesh_export_include_collisions = True
        props.mesh_export_collision_filter = "ALL"
        props.mesh_export_collision_profile = "GODOT"

        bpy.ops.object.select_all(action="DESELECT")
        parent.select_set(True)
        bpy.context.view_layer.objects.active = parent

        result = bpy.ops.mesh.batch_export()
        assert result == {"FINISHED"}, "ALL filter export should succeed"

        names = _gltf_node_names(temp_export_dir / "AllFilterParent.gltf")
        assert any(n.endswith("-convcolonly") for n in names), (
            f"Expected a Godot collision node, got {names}"
        )


class TestCollisionNaming:
    """Tests that engine profiles produce the right node names."""

    def test_unreal_naming(
        self, create_mesh_with_unreal_collisions, temp_export_dir, reset_settings
    ):
        """Unreal profile yields UCX_<Name>_NN / UBX_<Name>_NN nodes."""
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "GLTF"
        props.mesh_export_gltf_type = "GLTF_SEPARATE"
        props.mesh_export_gltf_batch_mode = "INDIVIDUAL"
        props.mesh_export_include_collisions = True
        props.mesh_export_collision_filter = "PREFIXED"
        props.mesh_export_collision_profile = "UNREAL"

        parent = create_mesh_with_unreal_collisions
        parent.select_set(True)

        result = bpy.ops.mesh.batch_export()
        assert result == {"FINISHED"}, "Unreal collision export should succeed"

        names = _gltf_node_names(temp_export_dir / "CollisionParent.gltf")
        # Index ordering may vary, so check by prefix + parent name.
        assert any(
            n.startswith("UCX_CollisionParent_") for n in names
        ), f"Expected UCX_ node, got {names}"
        assert any(
            n.startswith("UBX_CollisionParent_") for n in names
        ), f"Expected UBX_ node, got {names}"

    def test_godot_naming(
        self, create_mesh_with_unreal_collisions, temp_export_dir, reset_settings
    ):
        """Godot profile yields a -convcolonly suffix (primitives map to convex)."""
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "GLTF"
        props.mesh_export_gltf_type = "GLTF_SEPARATE"
        props.mesh_export_gltf_batch_mode = "INDIVIDUAL"
        props.mesh_export_include_collisions = True
        props.mesh_export_collision_filter = "PREFIXED"
        props.mesh_export_collision_profile = "GODOT"

        parent = create_mesh_with_unreal_collisions
        parent.select_set(True)

        result = bpy.ops.mesh.batch_export()
        assert result == {"FINISHED"}, "Godot collision export should succeed"

        names = _gltf_node_names(temp_export_dir / "CollisionParent.gltf")
        assert any(n == "CollisionParent-convcolonly" for n in names), (
            f"Expected -convcolonly node, got {names}"
        )

    def test_godot_visual_suffix(
        self, create_mesh_with_unreal_collisions, temp_export_dir, reset_settings
    ):
        """Godot 'render collision' option yields -convcol instead of -convcolonly."""
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "GLTF"
        props.mesh_export_gltf_type = "GLTF_SEPARATE"
        props.mesh_export_gltf_batch_mode = "INDIVIDUAL"
        props.mesh_export_include_collisions = True
        props.mesh_export_collision_profile = "GODOT"
        props.mesh_export_collision_godot_visual = True

        parent = create_mesh_with_unreal_collisions
        parent.select_set(True)

        result = bpy.ops.mesh.batch_export()
        assert result == {"FINISHED"}, "Godot visual collision export should succeed"

        names = _gltf_node_names(temp_export_dir / "CollisionParent.gltf")
        assert any(n == "CollisionParent-convcol" for n in names), (
            f"Expected -convcol node, got {names}"
        )
        assert not any(n.endswith("-convcolonly") for n in names)

    def test_custom_naming(self, temp_export_dir, reset_settings):
        """Custom profile wraps the render name with user prefix and suffix."""
        bpy.ops.mesh.primitive_cube_add(location=(0, 0, 0))
        parent = bpy.context.active_object
        parent.name = "CustomColl"

        bpy.ops.mesh.primitive_cube_add(location=(0, 0, 0))
        child = bpy.context.active_object
        child.name = "UCX_CustomColl"
        child.parent = parent

        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "GLTF"
        props.mesh_export_gltf_type = "GLTF_SEPARATE"
        props.mesh_export_gltf_batch_mode = "INDIVIDUAL"
        props.mesh_export_include_collisions = True
        props.mesh_export_collision_profile = "CUSTOM"
        props.mesh_export_collision_custom_prefix = "COL_"
        props.mesh_export_collision_custom_suffix = "_phys"

        bpy.ops.object.select_all(action="DESELECT")
        parent.select_set(True)
        bpy.context.view_layer.objects.active = parent

        result = bpy.ops.mesh.batch_export()
        assert result == {"FINISHED"}, "Custom collision export should succeed"

        names = _gltf_node_names(temp_export_dir / "CustomColl.gltf")
        assert "COL_CustomColl_phys" in names, (
            f"Expected custom-named node, got {names}"
        )

    def test_auto_profile_follows_convention(
        self, create_mesh_with_unreal_collisions, temp_export_dir, reset_settings
    ):
        """AUTO profile maps the Godot naming convention to Godot collisions."""
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "GLTF"
        props.mesh_export_gltf_type = "GLTF_SEPARATE"
        props.mesh_export_gltf_batch_mode = "INDIVIDUAL"
        props.mesh_export_include_collisions = True
        props.mesh_export_collision_profile = "AUTO"
        props.mesh_export_naming_convention = "GODOT"

        parent = create_mesh_with_unreal_collisions
        parent.select_set(True)

        result = bpy.ops.mesh.batch_export()
        assert result == {"FINISHED"}, "AUTO/Godot collision export should succeed"

        # File name follows Godot (snake_case) convention.
        names = _gltf_node_names(temp_export_dir / "collision_parent.gltf")
        assert any(n.endswith("-convcolonly") for n in names), (
            f"AUTO should resolve to Godot suffix, got {names}"
        )


class TestCollisionExclusion:
    """Tests that selected collision objects aren't exported standalone."""

    def test_selected_collision_not_standalone(
        self, create_mesh_with_unreal_collisions, temp_export_dir, reset_settings
    ):
        """Selecting render mesh + its collision child yields one file only."""
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"
        props.mesh_export_include_collisions = True
        props.mesh_export_collision_profile = "UNREAL"

        parent = create_mesh_with_unreal_collisions
        bpy.ops.object.select_all(action="DESELECT")
        parent.select_set(True)
        # Also select the collision children explicitly.
        for child in parent.children:
            child.select_set(True)
        bpy.context.view_layer.objects.active = parent

        result = bpy.ops.mesh.batch_export()
        assert result == {"FINISHED"}, "Export should succeed"

        # No standalone UCX_/UBX_ files - only the parent's file.
        assert count_exported_files(temp_export_dir, "fbx") == 1
        assert verify_file_exists(temp_export_dir / "CollisionParent.fbx", "fbx")

    def test_only_collision_selected_errors(
        self, create_mesh_with_unreal_collisions, temp_export_dir, reset_settings
    ):
        """Selecting only a collision child (no parent) is cancelled."""
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"
        props.mesh_export_include_collisions = True

        parent = create_mesh_with_unreal_collisions
        bpy.ops.object.select_all(action="DESELECT")
        collision = parent.children[0]
        collision.select_set(True)
        bpy.context.view_layer.objects.active = collision

        result = bpy.ops.mesh.batch_export()
        assert result == {"CANCELLED"}, (
            "Exporting only a collision child should be cancelled"
        )


class TestCollisionExportPaths:
    """Tests collisions across the batch and hierarchy export paths."""

    def test_collisions_in_gltf_batch_combine(self, temp_export_dir, reset_settings):
        """Collisions are combined into the single batch glTF file."""
        bpy.ops.mesh.primitive_cube_add(location=(0, 0, 0))
        mesh1 = bpy.context.active_object
        mesh1.name = "BatchColl1"
        bpy.ops.mesh.primitive_cube_add(location=(0, 0, 0))
        col1 = bpy.context.active_object
        col1.name = "UCX_BatchColl1"
        col1.parent = mesh1

        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "GLTF"
        props.mesh_export_gltf_type = "GLTF_SEPARATE"
        props.mesh_export_gltf_batch_mode = "COMBINE"
        props.mesh_export_include_collisions = True
        props.mesh_export_collision_profile = "GODOT"

        bpy.ops.object.select_all(action="DESELECT")
        mesh1.select_set(True)
        bpy.context.view_layer.objects.active = mesh1

        result = bpy.ops.mesh.batch_export()
        assert result == {"FINISHED"}, "Batch combine with collisions should succeed"

        # A single combined file is written; collisions ride inside it.
        assert count_exported_files(temp_export_dir, "gltf") == 1
        gltf_path = next(temp_export_dir.glob("*.gltf"))
        names = _gltf_node_names(gltf_path)
        assert any(n.endswith("-convcolonly") for n in names), (
            f"Expected collision node in batch file, got {names}"
        )

    def test_collisions_with_lod_hierarchy(
        self, create_mesh_with_unreal_collisions, temp_export_dir, reset_settings
    ):
        """Collisions are included in the LOD group FBX."""
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"
        props.mesh_export_include_collisions = True
        props.mesh_export_collision_profile = "UNREAL"
        props.mesh_export_lod = True
        props.mesh_export_lod_count = 2
        props.mesh_export_lod_hierarchy = True

        parent = create_mesh_with_unreal_collisions
        parent.select_set(True)

        result = bpy.ops.mesh.batch_export()
        assert result == {"FINISHED"}, (
            "LOD hierarchy export with collisions should succeed"
        )
        assert verify_file_exists(
            temp_export_dir / "CollisionParent_LODGroup.fbx", "fbx"
        )


class TestCollisionRegressions:
    """Regression coverage for behaviour fixed alongside this feature."""

    def test_single_mode_empties_included(self, temp_export_dir, reset_settings):
        """Attachment empties now survive single-object FBX/glTF export.

        Previously the single-object path's temp selection dropped empties; the
        collision work routes extras through export_object(extra_objects=...).
        """
        bpy.ops.mesh.primitive_cube_add(location=(0, 0, 0))
        parent = bpy.context.active_object
        parent.name = "EmptyRegression"

        empty = bpy.data.objects.new("attach_socket", None)
        empty.empty_display_type = "PLAIN_AXES"
        empty.location = (0, 0, 1)
        empty.parent = parent
        bpy.context.collection.objects.link(empty)

        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "GLTF"
        props.mesh_export_gltf_type = "GLTF_SEPARATE"
        props.mesh_export_gltf_batch_mode = "INDIVIDUAL"
        props.mesh_export_include_empties = True
        props.mesh_export_empty_filter = "ALL"

        bpy.ops.object.select_all(action="DESELECT")
        parent.select_set(True)
        bpy.context.view_layer.objects.active = parent

        result = bpy.ops.mesh.batch_export()
        assert result == {"FINISHED"}, "Single-mode export with empty should succeed"

        # The copy is auto-suffixed (.001) by Blender because the original empty
        # still exists in the scene; match by prefix.
        names = _gltf_node_names(temp_export_dir / "EmptyRegression.gltf")
        assert any(n.startswith("attach_socket") for n in names), (
            f"Attachment empty should be in single-mode export, got {names}"
        )


class TestCollisionProperties:
    """Tests that collision properties exist and are settable."""

    def test_collision_properties_exist(self, reset_settings):
        """All collision properties should be accessible and settable."""
        props = get_scene_props()

        assert hasattr(props, "mesh_export_include_collisions")
        assert hasattr(props, "mesh_export_collision_filter")
        assert hasattr(props, "mesh_export_collision_profile")
        assert hasattr(props, "mesh_export_collision_godot_visual")
        assert hasattr(props, "mesh_export_collision_custom_prefix")
        assert hasattr(props, "mesh_export_collision_custom_suffix")

        props.mesh_export_include_collisions = True
        props.mesh_export_collision_filter = "ALL"
        props.mesh_export_collision_profile = "CUSTOM"
        props.mesh_export_collision_custom_prefix = "C_"

        assert props.mesh_export_include_collisions is True
        assert props.mesh_export_collision_filter == "ALL"
        assert props.mesh_export_collision_profile == "CUSTOM"
        assert props.mesh_export_collision_custom_prefix == "C_"
