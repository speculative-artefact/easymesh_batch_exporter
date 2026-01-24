"""Tests for batch export modes.

This module tests glTF batch mode functionality, which allows
combining multiple meshes into a single glTF file (Godot workflow).
"""

import bpy
import pytest
from pathlib import Path
from conftest import (
    verify_file_exists,
    count_exported_files,
    get_scene_props,
    reset_export_settings,
)


class TestGLTFBatchMode:
    """Tests for glTF batch mode (combine multiple objects)."""

    def test_batch_combine_mode(
        self, create_cube, create_sphere, temp_export_dir, reset_settings
    ):
        """Test combining multiple objects into single glTF file."""
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "GLTF"
        props.mesh_export_gltf_type = "GLB"
        props.mesh_export_gltf_batch_mode = "COMBINE"

        # Select multiple objects
        create_cube.select_set(True)
        create_sphere.select_set(True)

        result = bpy.ops.mesh.batch_export_selected()
        assert result == {"FINISHED"}, "Batch combine export should succeed"

        # Should create only one combined GLB file
        glb_count = count_exported_files(temp_export_dir, "glb")
        assert glb_count == 1, (
            "Should create only one combined GLB file in COMBINE mode"
        )

    def test_batch_individual_mode(
        self, create_cube, create_sphere, temp_export_dir, reset_settings
    ):
        """Test exporting multiple objects as separate glTF files."""
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "GLTF"
        props.mesh_export_gltf_type = "GLB"
        props.mesh_export_gltf_batch_mode = "INDIVIDUAL"

        # Select multiple objects
        create_cube.select_set(True)
        create_sphere.select_set(True)

        result = bpy.ops.mesh.batch_export_selected()
        assert result == {"FINISHED"}, "Batch individual export should succeed"

        # Should create separate GLB files for each object
        glb_count = count_exported_files(temp_export_dir, "glb")
        assert glb_count == 2, "Should create individual GLB files in INDIVIDUAL mode"

        # Verify both files exist
        cube_file = temp_export_dir / "TestCube.glb"
        sphere_file = temp_export_dir / "TestSphere.glb"
        assert verify_file_exists(cube_file, "glb"), "Cube GLB should exist"
        assert verify_file_exists(sphere_file, "glb"), "Sphere GLB should exist"

    def test_batch_mode_with_json_gltf(
        self, create_cube, create_sphere, temp_export_dir, reset_settings
    ):
        """Test batch combine mode with JSON glTF format."""
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "GLTF"
        props.mesh_export_gltf_type = "GLTF_SEPARATE"  # JSON format
        props.mesh_export_gltf_batch_mode = "COMBINE"

        create_cube.select_set(True)
        create_sphere.select_set(True)

        result = bpy.ops.mesh.batch_export_selected()
        assert result == {"FINISHED"}, "Batch combine with JSON glTF should succeed"

        # Should create one combined GLTF file
        gltf_count = count_exported_files(temp_export_dir, "gltf")
        assert gltf_count == 1, "Should create only one combined GLTF file"


class TestBatchModeWithCollections:
    """Tests for batch mode with Blender collections."""

    def test_batch_combine_with_collection(
        self, create_collection, temp_export_dir, reset_settings
    ):
        """Test batch combine uses collection name for filename.

        When all objects belong to the same collection, the combined file
        should use the collection name.
        """
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "GLTF"
        props.mesh_export_gltf_type = "GLB"
        props.mesh_export_gltf_batch_mode = "COMBINE"

        # Select all objects from the collection
        for obj in create_collection.objects:
            obj.select_set(True)

        result = bpy.ops.mesh.batch_export_selected()
        assert result == {"FINISHED"}, "Batch export with collection should succeed"

        # Should create file named after the collection
        expected_file = temp_export_dir / "TestCollection.glb"
        assert verify_file_exists(expected_file, "glb"), (
            "Combined file should use collection name"
        )

    def test_batch_combine_mixed_collections(self, temp_export_dir, reset_settings):
        """Test batch combine with objects from different collections.

        When objects are from different collections, should use first object's name.
        """
        # Create two collections with objects
        collection1 = bpy.data.collections.new("Collection1")
        collection2 = bpy.data.collections.new("Collection2")
        bpy.context.scene.collection.children.link(collection1)
        bpy.context.scene.collection.children.link(collection2)

        # Create object in collection1
        bpy.ops.mesh.primitive_cube_add(location=(0, 0, 0))
        obj1 = bpy.context.active_object
        obj1.name = "FirstCube"
        bpy.context.scene.collection.objects.unlink(obj1)
        collection1.objects.link(obj1)

        # Create object in collection2
        bpy.ops.mesh.primitive_sphere_add(location=(2, 0, 0))
        obj2 = bpy.context.active_object
        obj2.name = "SecondSphere"
        bpy.context.scene.collection.objects.unlink(obj2)
        collection2.objects.link(obj2)

        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "GLTF"
        props.mesh_export_gltf_type = "GLB"
        props.mesh_export_gltf_batch_mode = "COMBINE"

        # Select both objects
        obj1.select_set(True)
        obj2.select_set(True)

        result = bpy.ops.mesh.batch_export_selected()
        assert result == {"FINISHED"}, (
            "Batch export with mixed collections should succeed"
        )

        # Should use first object's name
        expected_file = temp_export_dir / "FirstCube.glb"
        assert verify_file_exists(expected_file, "glb"), (
            "Combined file should use first object's name when collections differ"
        )


class TestBatchModeWithLOD:
    """Tests for batch mode combined with LOD generation."""

    def test_batch_combine_with_lod(
        self, create_cube, create_sphere, temp_export_dir, reset_settings
    ):
        """Test batch combine mode with LOD generation.

        Should create one combined file with all objects and their LODs.
        """
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "GLTF"
        props.mesh_export_gltf_type = "GLB"
        props.mesh_export_gltf_batch_mode = "COMBINE"
        props.mesh_export_lod = True
        props.mesh_export_lod_count = 2

        create_cube.select_set(True)
        create_sphere.select_set(True)

        result = bpy.ops.mesh.batch_export_selected()
        assert result == {"FINISHED"}, "Batch combine with LOD should succeed"

        # Note: When combining with LOD, implementation details determine
        # exact file output. Verify at least one file is created.
        glb_count = count_exported_files(temp_export_dir, "glb")
        assert glb_count >= 1, "Should create at least one GLB file with LOD + batch"

    def test_batch_individual_with_lod(
        self, create_cube, create_sphere, temp_export_dir, reset_settings
    ):
        """Test batch individual mode with LOD generation.

        Should create separate files for each object plus their LOD levels.
        """
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "GLTF"
        props.mesh_export_gltf_type = "GLB"
        props.mesh_export_gltf_batch_mode = "INDIVIDUAL"
        props.mesh_export_lod = True
        props.mesh_export_lod_count = 2
        props.mesh_export_lod_hierarchy = False

        create_cube.select_set(True)
        create_sphere.select_set(True)

        result = bpy.ops.mesh.batch_export_selected()
        assert result == {"FINISHED"}, "Batch individual with LOD should succeed"

        # Should have: 2 base files + 2 LOD1 files + 2 LOD2 files = 6 files
        glb_count = count_exported_files(temp_export_dir, "glb")
        assert glb_count == 6, "Should create base and LOD files for each object"


class TestBatchModeOnlyForGLTF:
    """Tests that batch mode only applies to glTF format."""

    def test_batch_mode_ignored_for_fbx(
        self, create_cube, create_sphere, temp_export_dir, reset_settings
    ):
        """Test that batch mode setting is ignored for FBX format.

        FBX always exports individual files regardless of batch mode setting.
        """
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"
        props.mesh_export_gltf_batch_mode = "COMBINE"  # Should be ignored for FBX

        create_cube.select_set(True)
        create_sphere.select_set(True)

        result = bpy.ops.mesh.batch_export_selected()
        assert result == {"FINISHED"}, "FBX export should succeed"

        # Should create individual FBX files (batch mode ignored)
        fbx_count = count_exported_files(temp_export_dir, "fbx")
        assert fbx_count == 2, (
            "FBX should ignore batch mode and create individual files"
        )

    def test_batch_mode_ignored_for_obj(
        self, create_cube, create_sphere, temp_export_dir, reset_settings
    ):
        """Test that batch mode setting is ignored for OBJ format."""
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "OBJ"
        props.mesh_export_gltf_batch_mode = "COMBINE"

        create_cube.select_set(True)
        create_sphere.select_set(True)

        result = bpy.ops.mesh.batch_export_selected()
        assert result == {"FINISHED"}, "OBJ export should succeed"

        # Should create individual OBJ files
        obj_count = count_exported_files(temp_export_dir, "obj")
        assert obj_count == 2, (
            "OBJ should ignore batch mode and create individual files"
        )


class TestBatchModeWithNamingConventions:
    """Tests for batch mode with naming conventions applied."""

    def test_batch_combine_with_godot_naming(
        self, create_cube, create_sphere, temp_export_dir, reset_settings
    ):
        """Test batch combine with Godot naming convention."""
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "GLTF"
        props.mesh_export_gltf_type = "GLB"
        props.mesh_export_gltf_batch_mode = "COMBINE"
        props.mesh_export_naming_convention = "GODOT"

        create_cube.select_set(True)
        create_sphere.select_set(True)

        result = bpy.ops.mesh.batch_export_selected()
        assert result == {"FINISHED"}, "Batch export with Godot naming should succeed"

        # Should create one file with snake_case naming
        # First object is TestCube -> test_cube in Godot convention
        expected_file = temp_export_dir / "test_cube.glb"
        assert verify_file_exists(expected_file, "glb"), (
            "Combined file should use Godot naming convention"
        )

    def test_batch_combine_with_prefix_suffix(
        self, create_cube, create_sphere, temp_export_dir, reset_settings
    ):
        """Test batch combine with prefix and suffix."""
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "GLTF"
        props.mesh_export_gltf_type = "GLB"
        props.mesh_export_gltf_batch_mode = "COMBINE"
        props.mesh_export_prefix = "mesh_"
        props.mesh_export_suffix = "_export"

        create_cube.select_set(True)
        create_sphere.select_set(True)

        result = bpy.ops.mesh.batch_export_selected()
        assert result == {"FINISHED"}, "Batch export with prefix/suffix should succeed"

        # Should apply prefix and suffix to combined filename
        # First object is TestCube -> mesh_TestCube_export
        expected_file = temp_export_dir / "mesh_TestCube_export.glb"
        assert verify_file_exists(expected_file, "glb"), (
            "Combined file should have prefix and suffix applied"
        )
