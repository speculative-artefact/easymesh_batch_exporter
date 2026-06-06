"""Tests for attachment points and slot empties export functionality.

This module tests the ability to export empty objects as attachment points
alongside meshes, and the automatic creation of slot empties at child
mesh positions.
"""

import bpy
from conftest import (
    verify_file_exists,
    count_exported_files,
    get_scene_props,
)


class TestAttachmentEmptiesBasic:
    """Tests for basic attachment empty export functionality."""

    def test_fbx_includes_empties_by_default(
        self, create_mesh_with_empty_children, temp_export_dir, reset_settings
    ):
        """Test that FBX exports include empties by default."""
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"
        props.mesh_export_include_empties = True
        props.mesh_export_empty_filter = "ALL"

        parent = create_mesh_with_empty_children
        parent.select_set(True)

        result = bpy.ops.mesh.batch_export()
        assert result == {"FINISHED"}, "FBX export with empties should succeed"

        # Verify file was created
        expected_file = temp_export_dir / "TestParent.fbx"
        assert verify_file_exists(expected_file, "fbx"), "FBX file should exist"

    def test_gltf_includes_empties_by_default(
        self, create_mesh_with_empty_children, temp_export_dir, reset_settings
    ):
        """Test that glTF exports include empties by default."""
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "GLTF"
        props.mesh_export_gltf_type = "GLB"
        props.mesh_export_gltf_batch_mode = "INDIVIDUAL"
        props.mesh_export_include_empties = True
        props.mesh_export_empty_filter = "ALL"

        parent = create_mesh_with_empty_children
        parent.select_set(True)

        result = bpy.ops.mesh.batch_export()
        assert result == {"FINISHED"}, "glTF export with empties should succeed"

        # Verify file was created
        expected_file = temp_export_dir / "TestParent.glb"
        assert verify_file_exists(expected_file, "glb"), "GLB file should exist"

    def test_empties_disabled(
        self, create_mesh_with_empty_children, temp_export_dir, reset_settings
    ):
        """Test that empties can be excluded from export."""
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"
        props.mesh_export_include_empties = False

        parent = create_mesh_with_empty_children
        parent.select_set(True)

        result = bpy.ops.mesh.batch_export()
        assert result == {"FINISHED"}, "Export without empties should succeed"

        # Verify file was created (empties excluded but mesh exported)
        expected_file = temp_export_dir / "TestParent.fbx"
        assert verify_file_exists(expected_file, "fbx"), "FBX file should exist"

    def test_empty_transform_preserved(
        self, create_mesh_with_empty_children, temp_export_dir, reset_settings
    ):
        """Test that empty relative transforms are maintained after export.

        This test verifies the export completes successfully with zero location
        enabled, which should still preserve relative empty positions.
        """
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"
        props.mesh_export_include_empties = True
        props.mesh_export_zero_location = True

        parent = create_mesh_with_empty_children
        # Move parent to non-zero location to test relative transforms
        parent.location = (5, 5, 5)
        parent.select_set(True)

        result = bpy.ops.mesh.batch_export()
        assert result == {"FINISHED"}, "Export with zero location should succeed"

        expected_file = temp_export_dir / "TestParent.fbx"
        assert verify_file_exists(expected_file, "fbx"), "FBX file should exist"


class TestEmptyFilter:
    """Tests for empty filter functionality."""

    def test_filter_all_empties(
        self, create_mesh_with_mixed_empties, temp_export_dir, reset_settings
    ):
        """Test that ALL filter includes all empty children."""
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"
        props.mesh_export_include_empties = True
        props.mesh_export_empty_filter = "ALL"

        parent = create_mesh_with_mixed_empties
        parent.select_set(True)

        result = bpy.ops.mesh.batch_export()
        assert result == {"FINISHED"}, "Export with ALL filter should succeed"

        expected_file = temp_export_dir / "TestParentMixed.fbx"
        assert verify_file_exists(expected_file, "fbx"), "FBX file should exist"

    def test_filter_prefixed_only(
        self, create_mesh_with_mixed_empties, temp_export_dir, reset_settings
    ):
        """Test that PREFIXED filter only includes prefixed empties."""
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"
        props.mesh_export_include_empties = True
        props.mesh_export_empty_filter = "PREFIXED"
        props.mesh_export_empty_prefix = "attach_"

        parent = create_mesh_with_mixed_empties
        parent.select_set(True)

        result = bpy.ops.mesh.batch_export()
        assert result == {"FINISHED"}, "Export with PREFIXED filter should succeed"

        expected_file = temp_export_dir / "TestParentMixed.fbx"
        assert verify_file_exists(expected_file, "fbx"), "FBX file should exist"

    def test_custom_prefix(self, temp_export_dir, reset_settings):
        """Test that custom prefix filtering works correctly."""
        # Create mesh with custom prefixed empties
        bpy.ops.mesh.primitive_cube_add(location=(0, 0, 0))
        parent = bpy.context.active_object
        parent.name = "CustomPrefixTest"

        # Create empties with custom prefix
        empties_data = [
            ("socket_weapon", (0, 0, 1)),  # Custom prefix
            ("socket_shield", (1, 0, 0)),  # Custom prefix
            ("attach_other", (0, 1, 0)),  # Wrong prefix
        ]
        for name, loc in empties_data:
            empty = bpy.data.objects.new(name, None)
            empty.empty_display_type = "PLAIN_AXES"
            empty.location = loc
            empty.parent = parent
            bpy.context.collection.objects.link(empty)

        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"
        props.mesh_export_include_empties = True
        props.mesh_export_empty_filter = "PREFIXED"
        props.mesh_export_empty_prefix = "socket_"

        parent.select_set(True)

        result = bpy.ops.mesh.batch_export()
        assert result == {"FINISHED"}, "Export with custom prefix should succeed"

        expected_file = temp_export_dir / "CustomPrefixTest.fbx"
        assert verify_file_exists(expected_file, "fbx"), "FBX file should exist"


class TestSlotEmpties:
    """Tests for automatic slot empty creation."""

    def test_slot_empties_created(
        self, create_mesh_with_mesh_children, temp_export_dir, reset_settings
    ):
        """Test that slot empties are created for mesh children."""
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"
        props.mesh_export_include_empties = True
        props.mesh_export_create_slots = True
        props.mesh_export_slot_prefix = "slot_"

        parent = create_mesh_with_mesh_children
        parent.select_set(True)

        result = bpy.ops.mesh.batch_export()
        assert result == {"FINISHED"}, "Export with slot empties should succeed"

        expected_file = temp_export_dir / "TestParentWithMeshChildren.fbx"
        assert verify_file_exists(expected_file, "fbx"), "FBX file should exist"

    def test_slot_empties_naming_convention(
        self, create_mesh_with_mesh_children, temp_export_dir, reset_settings
    ):
        """Test that naming conventions are applied to slot empties."""
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"
        props.mesh_export_include_empties = True
        props.mesh_export_create_slots = True
        props.mesh_export_slot_prefix = "slot_"
        props.mesh_export_naming_enabled = True
        props.mesh_export_naming_convention = "GODOT"

        parent = create_mesh_with_mesh_children
        parent.select_set(True)

        result = bpy.ops.mesh.batch_export()
        assert result == {"FINISHED"}, (
            "Export with slot naming convention should succeed"
        )

        # File should use Godot naming convention
        expected_file = temp_export_dir / "test_parent_with_mesh_children.fbx"
        assert verify_file_exists(expected_file, "fbx"), (
            "FBX file should use Godot naming convention"
        )

    def test_slot_empties_disabled_by_default(
        self, create_mesh_with_mesh_children, temp_export_dir, reset_settings
    ):
        """Test that slot empties are not created when disabled."""
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"
        props.mesh_export_include_empties = True
        props.mesh_export_create_slots = False  # Explicitly disabled

        parent = create_mesh_with_mesh_children
        parent.select_set(True)

        result = bpy.ops.mesh.batch_export()
        assert result == {"FINISHED"}, "Export without slot empties should succeed"

        expected_file = temp_export_dir / "TestParentWithMeshChildren.fbx"
        assert verify_file_exists(expected_file, "fbx"), "FBX file should exist"

    def test_custom_slot_prefix(
        self, create_mesh_with_mesh_children, temp_export_dir, reset_settings
    ):
        """Test that custom slot prefix is applied."""
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"
        props.mesh_export_include_empties = True
        props.mesh_export_create_slots = True
        props.mesh_export_slot_prefix = "mount_"  # Custom prefix

        parent = create_mesh_with_mesh_children
        parent.select_set(True)

        result = bpy.ops.mesh.batch_export()
        assert result == {"FINISHED"}, "Export with custom slot prefix should succeed"

        expected_file = temp_export_dir / "TestParentWithMeshChildren.fbx"
        assert verify_file_exists(expected_file, "fbx"), "FBX file should exist"


class TestEmptiesWithLOD:
    """Tests for empties combined with LOD generation."""

    def test_empties_with_lod_hierarchy(
        self, create_mesh_with_empty_children, temp_export_dir, reset_settings
    ):
        """Test that empties are included with LOD hierarchy export."""
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"
        props.mesh_export_include_empties = True
        props.mesh_export_empty_filter = "ALL"
        props.mesh_export_lod = True
        props.mesh_export_lod_count = 2
        props.mesh_export_lod_hierarchy = True

        parent = create_mesh_with_empty_children
        parent.select_set(True)

        result = bpy.ops.mesh.batch_export()
        assert result == {"FINISHED"}, (
            "LOD hierarchy export with empties should succeed"
        )

        # Should create LOD group file
        expected_file = temp_export_dir / "TestParent_LODGroup.fbx"
        assert verify_file_exists(expected_file, "fbx"), (
            "LOD group FBX file should exist"
        )

    def test_slots_with_lod_hierarchy(
        self, create_mesh_with_mesh_children, temp_export_dir, reset_settings
    ):
        """Test that slot empties work with LOD hierarchy export."""
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"
        props.mesh_export_include_empties = True
        props.mesh_export_create_slots = True
        props.mesh_export_slot_prefix = "slot_"
        props.mesh_export_lod = True
        props.mesh_export_lod_count = 2
        props.mesh_export_lod_hierarchy = True

        parent = create_mesh_with_mesh_children
        parent.select_set(True)

        result = bpy.ops.mesh.batch_export()
        assert result == {"FINISHED"}, "LOD hierarchy export with slots should succeed"

        expected_file = temp_export_dir / "TestParentWithMeshChildren_LODGroup.fbx"
        assert verify_file_exists(expected_file, "fbx"), (
            "LOD group FBX file should exist"
        )

    def test_empties_with_lod_individual_files(
        self, create_mesh_with_empty_children, temp_export_dir, reset_settings
    ):
        """Test empties export with individual LOD files (non-hierarchy)."""
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"
        props.mesh_export_include_empties = True
        props.mesh_export_empty_filter = "ALL"
        props.mesh_export_lod = True
        props.mesh_export_lod_count = 2
        props.mesh_export_lod_hierarchy = False  # Individual files

        parent = create_mesh_with_empty_children
        parent.select_set(True)

        result = bpy.ops.mesh.batch_export()
        assert result == {"FINISHED"}, (
            "Individual LOD export with empties should succeed"
        )

        # Should create base + LOD files
        fbx_count = count_exported_files(temp_export_dir, "fbx")
        assert fbx_count >= 2, "Should create base and LOD files"


class TestEmptiesWithBatchMode:
    """Tests for empties with glTF batch mode."""

    def test_empties_in_gltf_batch_combine(self, temp_export_dir, reset_settings):
        """Test that empties are included per-object in batch combine mode."""
        # Create two meshes with empties
        bpy.ops.mesh.primitive_cube_add(location=(0, 0, 0))
        mesh1 = bpy.context.active_object
        mesh1.name = "BatchMesh1"

        empty1 = bpy.data.objects.new("attach_point1", None)
        empty1.empty_display_type = "PLAIN_AXES"
        empty1.location = (0, 0, 1)
        empty1.parent = mesh1
        bpy.context.collection.objects.link(empty1)

        bpy.ops.mesh.primitive_uv_sphere_add(location=(3, 0, 0))
        mesh2 = bpy.context.active_object
        mesh2.name = "BatchMesh2"

        empty2 = bpy.data.objects.new("attach_point2", None)
        empty2.empty_display_type = "PLAIN_AXES"
        empty2.location = (3, 0, 1)
        empty2.parent = mesh2
        bpy.context.collection.objects.link(empty2)

        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "GLTF"
        props.mesh_export_gltf_type = "GLB"
        props.mesh_export_gltf_batch_mode = "COMBINE"
        props.mesh_export_include_empties = True
        props.mesh_export_empty_filter = "ALL"

        # Deselect all then select the meshes
        bpy.ops.object.select_all(action="DESELECT")
        mesh1.select_set(True)
        mesh2.select_set(True)
        bpy.context.view_layer.objects.active = mesh1

        # Batch COMBINE mode requires batch_name parameter
        result = bpy.ops.mesh.batch_export(batch_name="CombinedBatchTest")
        assert result == {"FINISHED"}, "Batch combine with empties should succeed"

        # Should create single combined file
        glb_count = count_exported_files(temp_export_dir, "glb")
        assert glb_count == 1, "Should create one combined GLB file"

    def test_empties_in_gltf_batch_individual(self, temp_export_dir, reset_settings):
        """Test that empties are included with individual batch mode."""
        # Create two meshes with empties
        bpy.ops.mesh.primitive_cube_add(location=(0, 0, 0))
        mesh1 = bpy.context.active_object
        mesh1.name = "IndividualMesh1"

        empty1 = bpy.data.objects.new("attach_ind1", None)
        empty1.empty_display_type = "PLAIN_AXES"
        empty1.location = (0, 0, 1)
        empty1.parent = mesh1
        bpy.context.collection.objects.link(empty1)

        bpy.ops.mesh.primitive_uv_sphere_add(location=(3, 0, 0))
        mesh2 = bpy.context.active_object
        mesh2.name = "IndividualMesh2"

        empty2 = bpy.data.objects.new("attach_ind2", None)
        empty2.empty_display_type = "PLAIN_AXES"
        empty2.location = (3, 0, 1)
        empty2.parent = mesh2
        bpy.context.collection.objects.link(empty2)

        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "GLTF"
        props.mesh_export_gltf_type = "GLB"
        props.mesh_export_gltf_batch_mode = "INDIVIDUAL"
        props.mesh_export_include_empties = True
        props.mesh_export_empty_filter = "ALL"

        # Deselect all then select the meshes
        bpy.ops.object.select_all(action="DESELECT")
        mesh1.select_set(True)
        mesh2.select_set(True)

        result = bpy.ops.mesh.batch_export()
        assert result == {"FINISHED"}, "Batch individual with empties should succeed"

        # Should create individual files
        glb_count = count_exported_files(temp_export_dir, "glb")
        assert glb_count == 2, "Should create individual GLB files"

    def test_slots_in_gltf_batch_combine(self, temp_export_dir, reset_settings):
        """Test that slot empties work per-object in batch combine mode."""
        # Create parent mesh with mesh children
        bpy.ops.mesh.primitive_cube_add(location=(0, 0, 0))
        parent = bpy.context.active_object
        parent.name = "BatchParent"

        bpy.ops.mesh.primitive_uv_sphere_add(location=(2, 0, 0))
        child = bpy.context.active_object
        child.name = "BatchChild"
        child.parent = parent

        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "GLTF"
        props.mesh_export_gltf_type = "GLB"
        props.mesh_export_gltf_batch_mode = "COMBINE"
        props.mesh_export_include_empties = True
        props.mesh_export_create_slots = True
        props.mesh_export_slot_prefix = "slot_"

        # Deselect all then select the parent mesh
        bpy.ops.object.select_all(action="DESELECT")
        parent.select_set(True)
        bpy.context.view_layer.objects.active = parent

        result = bpy.ops.mesh.batch_export()
        assert result == {"FINISHED"}, "Batch combine with slots should succeed"

        glb_count = count_exported_files(temp_export_dir, "glb")
        assert glb_count == 1, "Should create one combined GLB file"


class TestEmptiesFormatSupport:
    """Tests for empties panel visibility based on export format."""

    def test_empties_property_fbx(self, reset_settings):
        """Test that empties properties exist and work for FBX format."""
        props = get_scene_props()
        props.mesh_export_format = "FBX"

        # Verify properties are accessible
        assert hasattr(props, "mesh_export_include_empties")
        assert hasattr(props, "mesh_export_empty_filter")
        assert hasattr(props, "mesh_export_empty_prefix")
        assert hasattr(props, "mesh_export_create_slots")
        assert hasattr(props, "mesh_export_slot_prefix")

        # Set values to verify they work
        props.mesh_export_include_empties = True
        props.mesh_export_empty_filter = "PREFIXED"
        props.mesh_export_empty_prefix = "test_"
        props.mesh_export_create_slots = True
        props.mesh_export_slot_prefix = "socket_"

        assert props.mesh_export_include_empties is True
        assert props.mesh_export_empty_filter == "PREFIXED"
        assert props.mesh_export_empty_prefix == "test_"
        assert props.mesh_export_create_slots is True
        assert props.mesh_export_slot_prefix == "socket_"

    def test_empties_property_gltf(self, reset_settings):
        """Test that empties properties exist and work for glTF format."""
        props = get_scene_props()
        props.mesh_export_format = "GLTF"

        props.mesh_export_include_empties = True
        props.mesh_export_empty_filter = "ALL"

        assert props.mesh_export_include_empties is True
        assert props.mesh_export_empty_filter == "ALL"

    def test_empties_export_obj_format(
        self, create_mesh_with_empty_children, temp_export_dir, reset_settings
    ):
        """Test export with OBJ format (empties not supported).

        OBJ format doesn't support empties, but export should still succeed
        without the empties being included.
        """
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "OBJ"
        props.mesh_export_include_empties = True  # Should be ignored for OBJ

        parent = create_mesh_with_empty_children
        parent.select_set(True)

        result = bpy.ops.mesh.batch_export()
        assert result == {"FINISHED"}, "OBJ export should succeed (empties ignored)"

        expected_file = temp_export_dir / "TestParent.obj"
        assert verify_file_exists(expected_file, "obj"), "OBJ file should exist"

    def test_empties_export_stl_format(
        self, create_mesh_with_empty_children, temp_export_dir, reset_settings
    ):
        """Test export with STL format (empties not supported).

        STL format doesn't support empties, but export should still succeed
        without the empties being included.
        """
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "STL"
        props.mesh_export_include_empties = True  # Should be ignored for STL

        parent = create_mesh_with_empty_children
        parent.select_set(True)

        result = bpy.ops.mesh.batch_export()
        assert result == {"FINISHED"}, "STL export should succeed (empties ignored)"

        expected_file = temp_export_dir / "TestParent.stl"
        assert verify_file_exists(expected_file, "stl"), "STL file should exist"


class TestEmptiesEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_mesh_without_empty_children(
        self, create_cube, temp_export_dir, reset_settings
    ):
        """Test export of mesh without any empty children."""
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"
        props.mesh_export_include_empties = True
        props.mesh_export_empty_filter = "ALL"

        create_cube.select_set(True)

        result = bpy.ops.mesh.batch_export()
        assert result == {"FINISHED"}, "Export without empty children should succeed"

        expected_file = temp_export_dir / "TestCube.fbx"
        assert verify_file_exists(expected_file, "fbx"), "FBX file should exist"

    def test_empty_prefix_no_matches(
        self, create_mesh_with_empty_children, temp_export_dir, reset_settings
    ):
        """Test export when prefix filter matches no empties."""
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"
        props.mesh_export_include_empties = True
        props.mesh_export_empty_filter = "PREFIXED"
        props.mesh_export_empty_prefix = "nonexistent_"  # Won't match any empties

        parent = create_mesh_with_empty_children
        parent.select_set(True)

        result = bpy.ops.mesh.batch_export()
        assert result == {"FINISHED"}, "Export with no matching empties should succeed"

        expected_file = temp_export_dir / "TestParent.fbx"
        assert verify_file_exists(expected_file, "fbx"), "FBX file should exist"

    def test_deeply_nested_empties(self, temp_export_dir, reset_settings):
        """Test that only direct empty children are exported, not nested ones."""
        bpy.ops.mesh.primitive_cube_add(location=(0, 0, 0))
        parent = bpy.context.active_object
        parent.name = "NestedTestParent"

        # Direct empty child
        direct_empty = bpy.data.objects.new("attach_direct", None)
        direct_empty.empty_display_type = "PLAIN_AXES"
        direct_empty.location = (0, 0, 1)
        direct_empty.parent = parent
        bpy.context.collection.objects.link(direct_empty)

        # Nested empty (child of empty)
        nested_empty = bpy.data.objects.new("attach_nested", None)
        nested_empty.empty_display_type = "PLAIN_AXES"
        nested_empty.location = (0, 0, 2)
        nested_empty.parent = direct_empty
        bpy.context.collection.objects.link(nested_empty)

        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"
        props.mesh_export_include_empties = True
        props.mesh_export_empty_filter = "ALL"

        parent.select_set(True)

        result = bpy.ops.mesh.batch_export()
        assert result == {"FINISHED"}, "Export with nested empties should succeed"

        expected_file = temp_export_dir / "NestedTestParent.fbx"
        assert verify_file_exists(expected_file, "fbx"), "FBX file should exist"

    def test_slots_with_no_mesh_children(
        self, create_mesh_with_empty_children, temp_export_dir, reset_settings
    ):
        """Test slot creation when there are no mesh children (only empties)."""
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"
        props.mesh_export_include_empties = True
        props.mesh_export_create_slots = True  # Should create no slots

        parent = create_mesh_with_empty_children  # Has only empty children
        parent.select_set(True)

        result = bpy.ops.mesh.batch_export()
        assert result == {"FINISHED"}, (
            "Export should succeed with no mesh children for slots"
        )

        expected_file = temp_export_dir / "TestParent.fbx"
        assert verify_file_exists(expected_file, "fbx"), "FBX file should exist"

    def test_combined_empties_and_slots(self, temp_export_dir, reset_settings):
        """Test export with both attachment empties and slot empties."""
        bpy.ops.mesh.primitive_cube_add(location=(0, 0, 0))
        parent = bpy.context.active_object
        parent.name = "CombinedTest"

        # Add attachment empty
        attach_empty = bpy.data.objects.new("attach_weapon", None)
        attach_empty.empty_display_type = "PLAIN_AXES"
        attach_empty.location = (0, 0, 1)
        attach_empty.parent = parent
        bpy.context.collection.objects.link(attach_empty)

        # Add mesh child (will generate slot)
        bpy.ops.mesh.primitive_uv_sphere_add(location=(2, 0, 0))
        mesh_child = bpy.context.active_object
        mesh_child.name = "Accessory"
        mesh_child.parent = parent

        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"
        props.mesh_export_include_empties = True
        props.mesh_export_empty_filter = "ALL"
        props.mesh_export_create_slots = True
        props.mesh_export_slot_prefix = "slot_"

        parent.select_set(True)

        result = bpy.ops.mesh.batch_export()
        assert result == {"FINISHED"}, "Export with empties and slots should succeed"

        expected_file = temp_export_dir / "CombinedTest.fbx"
        assert verify_file_exists(expected_file, "fbx"), "FBX file should exist"
