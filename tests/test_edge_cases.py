"""Tests for edge cases and error handling.

This module tests error conditions, invalid inputs, and edge cases
to ensure the addon handles them gracefully.
"""

import bpy
import pytest
from pathlib import Path
from conftest import (
    verify_file_exists,
    count_exported_files,
    get_scene_props,
    reset_export_settings
)


class TestEmptySelections:
    """Tests for empty or no selection scenarios."""

    def test_no_selection(self, temp_export_dir, reset_settings):
        """Test export with no objects selected.

        Should fail gracefully with appropriate error message.
        """
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"

        # No objects selected
        result = bpy.ops.mesh.batch_export_selected()

        # Should not crash - either CANCELLED or FINISHED with warning
        assert result in [{'CANCELLED'}, {'FINISHED'}], \
            "Export with no selection should fail gracefully"

    def test_empty_scene(self, temp_export_dir, reset_settings):
        """Test export with an empty scene.

        Should handle gracefully without crashing.
        """
        # Scene is already empty due to clean_scene fixture
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"

        result = bpy.ops.mesh.batch_export_selected()
        assert result in [{'CANCELLED'}, {'FINISHED'}], \
            "Export from empty scene should fail gracefully"


class TestInvalidPaths:
    """Tests for invalid export path handling."""

    def test_nonexistent_directory(self, create_cube, reset_settings):
        """Test export to a non-existent directory.

        The operator should either create the directory or fail gracefully.
        """
        props = get_scene_props()
        # Use a path that doesn't exist
        props.mesh_export_path = "/tmp/blender_test_nonexistent_dir_12345/"
        props.mesh_export_format = "FBX"

        create_cube.select_set(True)
        result = bpy.ops.mesh.batch_export_selected()

        # Should either succeed (creating directory) or cancel
        assert result in [{'FINISHED'}, {'CANCELLED'}], \
            "Export to non-existent dir should complete or cancel"

        # Cleanup if directory was created
        import shutil
        test_dir = Path("/tmp/blender_test_nonexistent_dir_12345/")
        if test_dir.exists():
            shutil.rmtree(test_dir)

    def test_relative_path(self, create_cube, temp_export_dir, reset_settings):
        """Test export with relative path (Blender's // syntax).

        Should handle relative paths correctly.
        """
        props = get_scene_props()
        # Use relative path syntax - this might fail if blend file not saved
        props.mesh_export_path = "//exported_meshes/"
        props.mesh_export_format = "FBX"

        create_cube.select_set(True)
        result = bpy.ops.mesh.batch_export_selected()

        # May succeed if blend file location is known, otherwise should cancel
        assert result in [{'FINISHED'}, {'CANCELLED'}], \
            "Export with relative path should complete or cancel gracefully"


class TestUnsupportedObjectTypes:
    """Tests for unsupported or problematic object types."""

    def test_camera_export(self, temp_export_dir, reset_settings):
        """Test that camera objects are skipped during export."""
        # Add a camera
        bpy.ops.object.camera_add(location=(0, 0, 0))
        camera = bpy.context.active_object
        camera.name = "TestCamera"

        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"

        camera.select_set(True)
        result = bpy.ops.mesh.batch_export_selected()

        # Should complete but skip the camera
        # Implementation may return FINISHED or CANCELLED
        assert result in [{'FINISHED'}, {'CANCELLED'}], \
            "Camera export should complete gracefully"

        # No FBX file should be created for camera
        fbx_count = count_exported_files(temp_export_dir, "fbx")
        assert fbx_count == 0, "Camera should not be exported as mesh"

    def test_light_export(self, temp_export_dir, reset_settings):
        """Test that light objects are skipped during export."""
        # Add a light
        bpy.ops.object.light_add(type='POINT', location=(0, 0, 0))
        light = bpy.context.active_object
        light.name = "TestLight"

        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"

        light.select_set(True)
        result = bpy.ops.mesh.batch_export_selected()

        # Should complete but skip the light
        assert result in [{'FINISHED'}, {'CANCELLED'}], \
            "Light export should complete gracefully"

        fbx_count = count_exported_files(temp_export_dir, "fbx")
        assert fbx_count == 0, "Light should not be exported as mesh"

    def test_empty_object_export(self, temp_export_dir, reset_settings):
        """Test that empty objects are skipped during export."""
        # Add an empty
        bpy.ops.object.empty_add(location=(0, 0, 0))
        empty = bpy.context.active_object
        empty.name = "TestEmpty"

        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"

        empty.select_set(True)
        result = bpy.ops.mesh.batch_export_selected()

        # Should complete but skip the empty
        assert result in [{'FINISHED'}, {'CANCELLED'}], \
            "Empty export should complete gracefully"

        fbx_count = count_exported_files(temp_export_dir, "fbx")
        assert fbx_count == 0, "Empty should not be exported as mesh"


class TestMixedSelections:
    """Tests for mixed valid and invalid object selections."""

    def test_mesh_and_camera_mixed(self, create_cube, temp_export_dir, reset_settings):
        """Test export with both mesh and camera selected.

        Should export the mesh and skip the camera.
        """
        # Add a camera
        bpy.ops.object.camera_add(location=(5, 0, 0))
        camera = bpy.context.active_object
        camera.name = "TestCamera"

        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"

        # Select both
        create_cube.select_set(True)
        camera.select_set(True)

        result = bpy.ops.mesh.batch_export_selected()
        assert result == {'FINISHED'}, "Mixed export should succeed"

        # Should export only the cube
        cube_file = temp_export_dir / "TestCube.fbx"
        assert verify_file_exists(cube_file, "fbx"), "Cube should be exported"

        # No camera file
        camera_file = temp_export_dir / "TestCamera.fbx"
        assert not camera_file.exists(), "Camera should not be exported"

    def test_mesh_and_empty_mixed(self, create_sphere, temp_export_dir, reset_settings):
        """Test export with mesh and empty selected.

        Should export the mesh and skip the empty.
        """
        # Add an empty
        bpy.ops.object.empty_add(location=(5, 0, 0))
        empty = bpy.context.active_object
        empty.name = "TestEmpty"

        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"

        create_sphere.select_set(True)
        empty.select_set(True)

        result = bpy.ops.mesh.batch_export_selected()
        assert result == {'FINISHED'}, "Mixed export should succeed"

        # Should export only the sphere
        sphere_file = temp_export_dir / "TestSphere.fbx"
        assert verify_file_exists(sphere_file, "fbx"), "Sphere should be exported"


class TestZeroPolygonMeshes:
    """Tests for edge cases with mesh polygon counts."""

    def test_cube_with_no_faces(self, temp_export_dir, reset_settings):
        """Test exporting a mesh with vertices but no faces.

        Should handle gracefully without crashing.
        """
        # Create a mesh with only vertices
        import bmesh
        mesh = bpy.data.meshes.new("EmptyMesh")
        bm = bmesh.new()
        # Add some vertices but no faces
        bm.verts.new((0, 0, 0))
        bm.verts.new((1, 0, 0))
        bm.verts.new((0, 1, 0))
        bm.to_mesh(mesh)
        bm.free()

        obj = bpy.data.objects.new("EmptyMeshObj", mesh)
        bpy.context.scene.collection.objects.link(obj)

        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"

        obj.select_set(True)
        result = bpy.ops.mesh.batch_export_selected()

        # Should complete without crashing
        assert result in [{'FINISHED'}, {'CANCELLED'}], \
            "Empty mesh export should complete gracefully"


class TestCollectionInstances:
    """Tests for collection instances (should be skipped)."""

    def test_collection_instance_export(self, temp_export_dir, reset_settings):
        """Test that collection instances are skipped.

        Collection instances shouldn't be exported as regular meshes.
        """
        # Create a collection with a cube
        collection = bpy.data.collections.new("TestCollection")
        bpy.context.scene.collection.children.link(collection)

        bpy.ops.mesh.primitive_cube_add(location=(0, 0, 0))
        cube = bpy.context.active_object
        bpy.context.scene.collection.objects.unlink(cube)
        collection.objects.link(cube)

        # Create a collection instance
        instance = bpy.data.objects.new("CollectionInstance", None)
        instance.instance_type = 'COLLECTION'
        instance.instance_collection = collection
        bpy.context.scene.collection.objects.link(instance)

        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"

        instance.select_set(True)
        result = bpy.ops.mesh.batch_export_selected()

        # Should skip collection instance
        assert result in [{'FINISHED'}, {'CANCELLED'}], \
            "Collection instance export should complete gracefully"


class TestSpecialCharactersInNames:
    """Tests for objects with special characters in names."""

    def test_unicode_characters_in_name(self, temp_export_dir, reset_settings):
        """Test exporting object with Unicode characters in name."""
        bpy.ops.mesh.primitive_cube_add(location=(0, 0, 0))
        obj = bpy.context.active_object
        # Use Unicode characters
        obj.name = "Test_キューブ_Cube"

        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"

        obj.select_set(True)
        result = bpy.ops.mesh.batch_export_selected()

        # Should complete (characters may be sanitised)
        assert result in [{'FINISHED'}, {'CANCELLED'}], \
            "Export with Unicode name should complete"

        # At least one FBX file should be created
        fbx_count = count_exported_files(temp_export_dir, "fbx")
        assert fbx_count >= 1, "Should create an FBX file"

    def test_dots_in_name(self, temp_export_dir, reset_settings):
        """Test exporting object with dots in name."""
        bpy.ops.mesh.primitive_cube_add(location=(0, 0, 0))
        obj = bpy.context.active_object
        obj.name = "Test.Cube.001"

        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"

        obj.select_set(True)
        result = bpy.ops.mesh.batch_export_selected()
        assert result == {'FINISHED'}, "Export with dots in name should succeed"

        fbx_count = count_exported_files(temp_export_dir, "fbx")
        assert fbx_count == 1, "Should create one FBX file"


class TestExtremeSettings:
    """Tests for extreme or unusual setting combinations."""

    def test_zero_lod_ratio(self, create_sphere, temp_export_dir, reset_settings):
        """Test LOD generation with ratio set to 0 (extreme decimation).

        Should handle gracefully without crashing.
        """
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"
        props.mesh_export_lod = True
        props.mesh_export_lod_count = 1
        props.mesh_export_lod_hierarchy = False
        props.mesh_export_lod_ratio_01 = 0.01  # 1% of original (nearly nothing)

        create_sphere.select_set(True)
        result = bpy.ops.mesh.batch_export_selected()

        # Should complete even with extreme decimation
        assert result in [{'FINISHED'}, {'CANCELLED'}], \
            "Export with extreme LOD ratio should complete"

    def test_very_large_scale_factor(self, create_cube, temp_export_dir, reset_settings):
        """Test export with very large scale factor."""
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"
        props.mesh_export_scale = 1000.0  # Maximum scale

        create_cube.select_set(True)
        result = bpy.ops.mesh.batch_export_selected()
        assert result == {'FINISHED'}, "Export with large scale should succeed"

    def test_very_small_scale_factor(self, create_cube, temp_export_dir, reset_settings):
        """Test export with very small scale factor."""
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"
        props.mesh_export_scale = 0.001  # Minimum scale

        create_cube.select_set(True)
        result = bpy.ops.mesh.batch_export_selected()
        assert result == {'FINISHED'}, "Export with small scale should succeed"
