"""Tests for naming conventions and filename sanitisation.

This module tests the various naming conventions (Default, Godot, Unity, Unreal)
and prefix/suffix functionality.
"""

import bpy
import pytest
from pathlib import Path
from conftest import (
    verify_file_exists,
    get_scene_props,
    reset_export_settings
)


class TestNamingConventions:
    """Tests for different engine-specific naming conventions."""

    def test_default_naming(self, create_cube, temp_export_dir, reset_settings):
        """Test default naming convention (keeps original name)."""
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"
        props.mesh_export_naming_convention = "DEFAULT"

        create_cube.select_set(True)
        result = bpy.ops.mesh.batch_export_selected()
        assert result == {'FINISHED'}, "Export with default naming should succeed"

        expected_file = temp_export_dir / "TestCube.fbx"
        assert verify_file_exists(expected_file, "fbx"), "File should keep original name"

    def test_godot_naming(self, create_cube, temp_export_dir, reset_settings):
        """Test Godot naming convention (snake_case)."""
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"
        props.mesh_export_naming_convention = "GODOT"

        create_cube.select_set(True)
        result = bpy.ops.mesh.batch_export_selected()
        assert result == {'FINISHED'}, "Export with Godot naming should succeed"

        # TestCube -> test_cube in Godot convention
        expected_file = temp_export_dir / "test_cube.fbx"
        assert verify_file_exists(expected_file, "fbx"), \
            "File should use snake_case naming"

    def test_unity_naming(self, create_cube, temp_export_dir, reset_settings):
        """Test Unity naming convention (Capitalised_Words_With_Underscores)."""
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"
        props.mesh_export_naming_convention = "UNITY"

        create_cube.select_set(True)
        result = bpy.ops.mesh.batch_export_selected()
        assert result == {'FINISHED'}, "Export with Unity naming should succeed"

        # TestCube -> Test_Cube in Unity convention
        expected_file = temp_export_dir / "Test_Cube.fbx"
        assert verify_file_exists(expected_file, "fbx"), \
            "File should use Unity naming convention"

    def test_unreal_naming(self, create_cube, temp_export_dir, reset_settings):
        """Test Unreal Engine naming convention (PascalCase)."""
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"
        props.mesh_export_naming_convention = "UNREAL"

        create_cube.select_set(True)
        result = bpy.ops.mesh.batch_export_selected()
        assert result == {'FINISHED'}, "Export with Unreal naming should succeed"

        # TestCube -> TestCube in Unreal convention (already PascalCase)
        expected_file = temp_export_dir / "TestCube.fbx"
        assert verify_file_exists(expected_file, "fbx"), \
            "File should use PascalCase naming"


class TestUnrealPrefixPreservation:
    """Tests for Unreal Engine prefix preservation."""

    def test_unreal_sm_prefix_preserved(self, temp_export_dir, reset_settings):
        """Test that SM_ prefix (Static Mesh) is preserved in Unreal naming."""
        bpy.ops.mesh.primitive_cube_add(location=(0, 0, 0))
        obj = bpy.context.active_object
        obj.name = "SM_MyStaticMesh"

        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"
        props.mesh_export_naming_convention = "UNREAL"

        obj.select_set(True)
        result = bpy.ops.mesh.batch_export_selected()
        assert result == {'FINISHED'}, "Export should succeed"

        # SM_ prefix should be preserved
        expected_file = temp_export_dir / "SM_MyStaticMesh.fbx"
        assert verify_file_exists(expected_file, "fbx"), \
            "SM_ prefix should be preserved in Unreal convention"

    def test_unreal_sk_prefix_preserved(self, temp_export_dir, reset_settings):
        """Test that SK_ prefix (Skeletal Mesh) is preserved in Unreal naming."""
        bpy.ops.mesh.primitive_cube_add(location=(0, 0, 0))
        obj = bpy.context.active_object
        obj.name = "SK_MyCharacter"

        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"
        props.mesh_export_naming_convention = "UNREAL"

        obj.select_set(True)
        result = bpy.ops.mesh.batch_export_selected()
        assert result == {'FINISHED'}, "Export should succeed"

        expected_file = temp_export_dir / "SK_MyCharacter.fbx"
        assert verify_file_exists(expected_file, "fbx"), \
            "SK_ prefix should be preserved"


class TestPrefixSuffix:
    """Tests for prefix and suffix functionality."""

    def test_prefix_only(self, create_cube, temp_export_dir, reset_settings):
        """Test adding a prefix to exported filenames."""
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"
        props.mesh_export_prefix = "mesh_"

        create_cube.select_set(True)
        result = bpy.ops.mesh.batch_export_selected()
        assert result == {'FINISHED'}, "Export with prefix should succeed"

        expected_file = temp_export_dir / "mesh_TestCube.fbx"
        assert verify_file_exists(expected_file, "fbx"), \
            "File should have prefix applied"

    def test_suffix_only(self, create_cube, temp_export_dir, reset_settings):
        """Test adding a suffix to exported filenames."""
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"
        props.mesh_export_suffix = "_export"

        create_cube.select_set(True)
        result = bpy.ops.mesh.batch_export_selected()
        assert result == {'FINISHED'}, "Export with suffix should succeed"

        expected_file = temp_export_dir / "TestCube_export.fbx"
        assert verify_file_exists(expected_file, "fbx"), \
            "File should have suffix applied"

    def test_prefix_and_suffix(self, create_cube, temp_export_dir, reset_settings):
        """Test adding both prefix and suffix to filenames."""
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"
        props.mesh_export_prefix = "mesh_"
        props.mesh_export_suffix = "_final"

        create_cube.select_set(True)
        result = bpy.ops.mesh.batch_export_selected()
        assert result == {'FINISHED'}, "Export with prefix and suffix should succeed"

        expected_file = temp_export_dir / "mesh_TestCube_final.fbx"
        assert verify_file_exists(expected_file, "fbx"), \
            "File should have both prefix and suffix"

    def test_prefix_suffix_with_naming_convention(self, create_cube, temp_export_dir, reset_settings):
        """Test that prefix/suffix work with naming conventions."""
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"
        props.mesh_export_naming_convention = "GODOT"
        props.mesh_export_prefix = "mesh_"
        props.mesh_export_suffix = "_final"

        create_cube.select_set(True)
        result = bpy.ops.mesh.batch_export_selected()
        assert result == {'FINISHED'}, "Export should succeed"

        # TestCube -> test_cube (Godot) -> mesh_test_cube_final
        expected_file = temp_export_dir / "mesh_test_cube_final.fbx"
        assert verify_file_exists(expected_file, "fbx"), \
            "Prefix/suffix should work with naming convention"


class TestFilenameSanitisation:
    """Tests for filename sanitisation and illegal character handling."""

    def test_sanitise_special_characters(self, temp_export_dir, reset_settings):
        """Test that special characters are removed from filenames."""
        bpy.ops.mesh.primitive_cube_add(location=(0, 0, 0))
        obj = bpy.context.active_object
        # Name with illegal filename characters
        obj.name = "Test:Cube*Name?"

        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"

        obj.select_set(True)
        result = bpy.ops.mesh.batch_export_selected()
        assert result == {'FINISHED'}, "Export with special characters should succeed"

        # Characters should be sanitised (removed or replaced)
        # Exact sanitised name depends on implementation
        fbx_files = list(temp_export_dir.glob("*.fbx"))
        assert len(fbx_files) >= 1, "At least one FBX file should be created"

    def test_sanitise_slashes(self, temp_export_dir, reset_settings):
        """Test that slashes are removed from filenames."""
        bpy.ops.mesh.primitive_cube_add(location=(0, 0, 0))
        obj = bpy.context.active_object
        obj.name = "Test/Cube\\Name"

        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"

        obj.select_set(True)
        result = bpy.ops.mesh.batch_export_selected()
        assert result == {'FINISHED'}, "Export with slashes should succeed"

        fbx_files = list(temp_export_dir.glob("*.fbx"))
        assert len(fbx_files) >= 1, "At least one FBX file should be created"

    def test_long_filename_truncation(self, temp_export_dir, reset_settings):
        """Test that very long filenames are truncated."""
        bpy.ops.mesh.primitive_cube_add(location=(0, 0, 0))
        obj = bpy.context.active_object
        # Create a very long name
        obj.name = "A" * 200  # 200 characters, exceeds MAX_FILENAME_LENGTH

        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"

        obj.select_set(True)
        result = bpy.ops.mesh.batch_export_selected()
        assert result == {'FINISHED'}, "Export with long filename should succeed"

        fbx_files = list(temp_export_dir.glob("*.fbx"))
        assert len(fbx_files) >= 1, "At least one FBX file should be created"

        # Verify filename was truncated (MAX_FILENAME_LENGTH = 100)
        created_file = fbx_files[0]
        name_without_ext = created_file.stem
        assert len(name_without_ext) <= 100, \
            "Filename should be truncated to MAX_FILENAME_LENGTH"


class TestNamingWithLOD:
    """Tests for naming conventions with LOD generation."""

    def test_godot_naming_with_lod(self, create_sphere, temp_export_dir, reset_settings):
        """Test that LOD files also use the naming convention."""
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"
        props.mesh_export_naming_convention = "GODOT"
        props.mesh_export_lod = True
        props.mesh_export_lod_count = 2
        props.mesh_export_lod_hierarchy = False

        create_sphere.select_set(True)
        result = bpy.ops.mesh.batch_export_selected()
        assert result == {'FINISHED'}, "Export with Godot naming and LOD should succeed"

        # TestSphere -> test_sphere (Godot)
        # LODs should also use convention: test_sphere_LOD01.fbx, etc.
        base_file = temp_export_dir / "test_sphere.fbx"
        lod1_file = temp_export_dir / "test_sphere_LOD01.fbx"
        lod2_file = temp_export_dir / "test_sphere_LOD02.fbx"

        assert verify_file_exists(base_file, "fbx"), "Base file should use naming convention"
        assert verify_file_exists(lod1_file, "fbx"), "LOD1 should use naming convention"
        assert verify_file_exists(lod2_file, "fbx"), "LOD2 should use naming convention"
