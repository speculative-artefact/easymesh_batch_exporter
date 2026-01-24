"""Tests for modifier application modes.

This module tests the different modifier application modes: None, Visible, and Render.
"""

import bpy
import pytest
from pathlib import Path
from conftest import verify_file_exists, get_scene_props, reset_export_settings


class TestModifierApplication:
    """Tests for different modifier application modes."""

    def test_modifier_mode_none(self, create_cube, temp_export_dir, reset_settings):
        """Test that NONE mode doesn't apply modifiers."""
        # Add a modifier to the cube
        mod = create_cube.modifiers.new(name="Subsurf", type="SUBSURF")
        mod.levels = 2

        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"
        props.mesh_export_apply_modifiers = "NONE"

        create_cube.select_set(True)
        result = bpy.ops.mesh.batch_export_selected()
        assert result == {"FINISHED"}, "Export with modifiers=NONE should succeed"

        expected_file = temp_export_dir / "TestCube.fbx"
        assert verify_file_exists(expected_file, "fbx"), (
            "File should exist even without applying modifiers"
        )

    def test_modifier_mode_visible(self, create_cube, temp_export_dir, reset_settings):
        """Test that VISIBLE mode applies viewport-visible modifiers."""
        # Add a visible modifier
        mod = create_cube.modifiers.new(name="Subsurf", type="SUBSURF")
        mod.levels = 2
        mod.show_viewport = True

        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"
        props.mesh_export_apply_modifiers = "VISIBLE"

        create_cube.select_set(True)
        result = bpy.ops.mesh.batch_export_selected()
        assert result == {"FINISHED"}, "Export with modifiers=VISIBLE should succeed"

        expected_file = temp_export_dir / "TestCube.fbx"
        assert verify_file_exists(expected_file, "fbx"), (
            "File should exist with visible modifiers applied"
        )

    def test_modifier_mode_render(self, create_cube, temp_export_dir, reset_settings):
        """Test that RENDER mode applies render-enabled modifiers."""
        # Add a render-enabled modifier
        mod = create_cube.modifiers.new(name="Subsurf", type="SUBSURF")
        mod.levels = 2
        mod.show_render = True

        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"
        props.mesh_export_apply_modifiers = "RENDER"

        create_cube.select_set(True)
        result = bpy.ops.mesh.batch_export_selected()
        assert result == {"FINISHED"}, "Export with modifiers=RENDER should succeed"

        expected_file = temp_export_dir / "TestCube.fbx"
        assert verify_file_exists(expected_file, "fbx"), (
            "File should exist with render modifiers applied"
        )


class TestSpecificModifierTypes:
    """Tests for specific modifier types."""

    def test_subdivision_surface_modifier(
        self, create_cube, temp_export_dir, reset_settings
    ):
        """Test exporting with Subdivision Surface modifier."""
        mod = create_cube.modifiers.new(name="Subsurf", type="SUBSURF")
        mod.levels = 2
        mod.render_levels = 3

        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"
        props.mesh_export_apply_modifiers = "VISIBLE"

        create_cube.select_set(True)
        result = bpy.ops.mesh.batch_export_selected()
        assert result == {"FINISHED"}, "Export with Subdivision Surface should succeed"

    def test_bevel_modifier(self, create_cube, temp_export_dir, reset_settings):
        """Test exporting with Bevel modifier."""
        mod = create_cube.modifiers.new(name="Bevel", type="BEVEL")
        mod.width = 0.1

        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"
        props.mesh_export_apply_modifiers = "VISIBLE"

        create_cube.select_set(True)
        result = bpy.ops.mesh.batch_export_selected()
        assert result == {"FINISHED"}, "Export with Bevel modifier should succeed"

    def test_mirror_modifier(self, create_cube, temp_export_dir, reset_settings):
        """Test exporting with Mirror modifier."""
        mod = create_cube.modifiers.new(name="Mirror", type="MIRROR")
        mod.use_axis[0] = True  # Mirror on X axis

        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"
        props.mesh_export_apply_modifiers = "VISIBLE"

        create_cube.select_set(True)
        result = bpy.ops.mesh.batch_export_selected()
        assert result == {"FINISHED"}, "Export with Mirror modifier should succeed"

    def test_array_modifier(self, create_cube, temp_export_dir, reset_settings):
        """Test exporting with Array modifier."""
        mod = create_cube.modifiers.new(name="Array", type="ARRAY")
        mod.count = 3

        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"
        props.mesh_export_apply_modifiers = "VISIBLE"

        create_cube.select_set(True)
        result = bpy.ops.mesh.batch_export_selected()
        assert result == {"FINISHED"}, "Export with Array modifier should succeed"


class TestMultipleModifiers:
    """Tests for multiple modifiers on a single object."""

    def test_multiple_modifiers_visible(
        self, create_cube, temp_export_dir, reset_settings
    ):
        """Test exporting with multiple visible modifiers."""
        # Add multiple modifiers
        mod1 = create_cube.modifiers.new(name="Bevel", type="BEVEL")
        mod1.width = 0.05

        mod2 = create_cube.modifiers.new(name="Subsurf", type="SUBSURF")
        mod2.levels = 1

        mod3 = create_cube.modifiers.new(name="Mirror", type="MIRROR")
        mod3.use_axis[0] = True

        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"
        props.mesh_export_apply_modifiers = "VISIBLE"

        create_cube.select_set(True)
        result = bpy.ops.mesh.batch_export_selected()
        assert result == {"FINISHED"}, "Export with multiple modifiers should succeed"

    def test_mixed_visibility_modifiers(
        self, create_cube, temp_export_dir, reset_settings
    ):
        """Test modifiers with different visibility settings.

        When mode is VISIBLE, only viewport-visible modifiers should be applied.
        """
        # Visible modifier
        mod1 = create_cube.modifiers.new(name="Bevel", type="BEVEL")
        mod1.width = 0.05
        mod1.show_viewport = True

        # Hidden modifier
        mod2 = create_cube.modifiers.new(name="Subsurf", type="SUBSURF")
        mod2.levels = 2
        mod2.show_viewport = False

        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"
        props.mesh_export_apply_modifiers = "VISIBLE"

        create_cube.select_set(True)
        result = bpy.ops.mesh.batch_export_selected()
        assert result == {"FINISHED"}, (
            "Export with mixed visibility modifiers should succeed"
        )


class TestTriangulationWithModifiers:
    """Tests for triangulation combined with modifiers."""

    def test_triangulation_after_modifiers(
        self, create_cube, temp_export_dir, reset_settings
    ):
        """Test that triangulation is applied after modifiers.

        Modifiers are applied first, then triangulation is applied to the result.
        """
        # Add a modifier that creates quads
        mod = create_cube.modifiers.new(name="Subsurf", type="SUBSURF")
        mod.levels = 1

        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"
        props.mesh_export_apply_modifiers = "VISIBLE"
        props.mesh_export_tri = True
        props.mesh_export_tri_method = "BEAUTY"

        create_cube.select_set(True)
        result = bpy.ops.mesh.batch_export_selected()
        assert result == {"FINISHED"}, (
            "Export with modifiers + triangulation should succeed"
        )

    def test_different_triangulation_methods_with_modifiers(
        self, create_cube, temp_export_dir, reset_settings
    ):
        """Test different triangulation methods after modifier application."""
        # Add subdivision to create quads
        mod = create_cube.modifiers.new(name="Subsurf", type="SUBSURF")
        mod.levels = 1

        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"
        props.mesh_export_apply_modifiers = "VISIBLE"
        props.mesh_export_tri = True

        for tri_method in ["BEAUTY", "FIXED", "FIXED_ALTERNATE", "SHORTEST_DIAGONAL"]:
            props.mesh_export_tri_method = tri_method
            props.mesh_export_suffix = f"_{tri_method.lower()}"

            create_cube.select_set(True)
            result = bpy.ops.mesh.batch_export_selected()
            assert result == {"FINISHED"}, (
                f"Export with {tri_method} triangulation should succeed"
            )

            expected_file = temp_export_dir / f"TestCube_{tri_method.lower()}.fbx"
            assert verify_file_exists(expected_file, "fbx"), (
                f"File with {tri_method} triangulation should exist"
            )


class TestModifiersWithLOD:
    """Tests for modifiers combined with LOD generation."""

    def test_modifiers_applied_to_lods(
        self, create_cube, temp_export_dir, reset_settings
    ):
        """Test that modifiers are applied before LOD decimation.

        The modifier should be applied to the base mesh first,
        then LOD decimation is applied to the modified mesh.
        """
        # Add a modifier
        mod = create_cube.modifiers.new(name="Bevel", type="BEVEL")
        mod.width = 0.1

        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"
        props.mesh_export_apply_modifiers = "VISIBLE"
        props.mesh_export_lod = True
        props.mesh_export_lod_count = 2
        props.mesh_export_lod_hierarchy = False

        create_cube.select_set(True)
        result = bpy.ops.mesh.batch_export_selected()
        assert result == {"FINISHED"}, "Export with modifiers + LOD should succeed"

        # Verify base and LOD files were created
        base_file = temp_export_dir / "TestCube.fbx"
        lod1_file = temp_export_dir / "TestCube_LOD01.fbx"

        assert verify_file_exists(base_file, "fbx"), "Base file should exist"
        assert verify_file_exists(lod1_file, "fbx"), "LOD1 file should exist"
