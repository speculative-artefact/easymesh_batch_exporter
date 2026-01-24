"""Tests for different object type handling.

This module tests that the addon correctly handles and exports different
Blender object types: meshes, curves, and metaballs.
"""

import bpy
import pytest
from pathlib import Path
from conftest import verify_file_exists, get_scene_props, reset_export_settings


class TestMeshObjects:
    """Tests for standard mesh object export."""

    def test_cube_export(self, create_cube, temp_export_dir, reset_settings):
        """Test exporting a cube primitive."""
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"

        create_cube.select_set(True)
        result = bpy.ops.mesh.batch_export()
        assert result == {"FINISHED"}, "Cube export should succeed"

        expected_file = temp_export_dir / "TestCube.fbx"
        assert verify_file_exists(expected_file, "fbx"), "Cube FBX should exist"

    def test_sphere_export(self, create_sphere, temp_export_dir, reset_settings):
        """Test exporting a sphere primitive."""
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"

        create_sphere.select_set(True)
        result = bpy.ops.mesh.batch_export()
        assert result == {"FINISHED"}, "Sphere export should succeed"

        expected_file = temp_export_dir / "TestSphere.fbx"
        assert verify_file_exists(expected_file, "fbx"), "Sphere FBX should exist"

    def test_cylinder_export(self, temp_export_dir, reset_settings):
        """Test exporting a cylinder primitive."""
        bpy.ops.mesh.primitive_cylinder_add(location=(0, 0, 0))
        obj = bpy.context.active_object
        obj.name = "TestCylinder"

        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"

        obj.select_set(True)
        result = bpy.ops.mesh.batch_export()
        assert result == {"FINISHED"}, "Cylinder export should succeed"

        expected_file = temp_export_dir / "TestCylinder.fbx"
        assert verify_file_exists(expected_file, "fbx"), "Cylinder FBX should exist"

    def test_torus_export(self, temp_export_dir, reset_settings):
        """Test exporting a torus primitive."""
        bpy.ops.mesh.primitive_torus_add(location=(0, 0, 0))
        obj = bpy.context.active_object
        obj.name = "TestTorus"

        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"

        obj.select_set(True)
        result = bpy.ops.mesh.batch_export()
        assert result == {"FINISHED"}, "Torus export should succeed"

        expected_file = temp_export_dir / "TestTorus.fbx"
        assert verify_file_exists(expected_file, "fbx"), "Torus FBX should exist"


class TestCurveObjects:
    """Tests for curve object export and conversion."""

    def test_bezier_curve_export(self, create_curve, temp_export_dir, reset_settings):
        """Test exporting a bezier curve (should convert to mesh)."""
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"

        create_curve.select_set(True)
        result = bpy.ops.mesh.batch_export()
        assert result == {"FINISHED"}, "Bezier curve export should succeed"

        expected_file = temp_export_dir / "TestCurve.fbx"
        assert verify_file_exists(expected_file, "fbx"), (
            "Converted curve FBX should exist"
        )

    def test_nurbs_curve_export(self, temp_export_dir, reset_settings):
        """Test exporting a NURBS curve (should convert to mesh)."""
        bpy.ops.curve.primitive_nurbs_circle_add(location=(0, 0, 0))
        obj = bpy.context.active_object
        obj.name = "TestNURBSCurve"

        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"

        obj.select_set(True)
        result = bpy.ops.mesh.batch_export()
        assert result == {"FINISHED"}, "NURBS curve export should succeed"

        expected_file = temp_export_dir / "TestNURBSCurve.fbx"
        assert verify_file_exists(expected_file, "fbx"), (
            "Converted NURBS curve FBX should exist"
        )

    def test_curve_with_bevel(self, temp_export_dir, reset_settings):
        """Test exporting a curve with bevel depth (creates 3D geometry)."""
        bpy.ops.curve.primitive_bezier_circle_add(location=(0, 0, 0))
        obj = bpy.context.active_object
        obj.name = "TestBeveledCurve"

        # Add bevel to create 3D geometry
        obj.data.bevel_depth = 0.1

        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"

        obj.select_set(True)
        result = bpy.ops.mesh.batch_export()
        assert result == {"FINISHED"}, "Beveled curve export should succeed"

        expected_file = temp_export_dir / "TestBeveledCurve.fbx"
        assert verify_file_exists(expected_file, "fbx"), (
            "Beveled curve FBX should exist"
        )


class TestMetaballObjects:
    """Tests for metaball object export and conversion."""

    def test_single_metaball_export(self, temp_export_dir, reset_settings):
        """Test exporting a single metaball (should convert to mesh)."""
        bpy.ops.object.metaball_add(type="BALL", location=(0, 0, 0))
        obj = bpy.context.active_object
        obj.name = "TestMetaBall"

        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"

        obj.select_set(True)
        result = bpy.ops.mesh.batch_export()
        assert result == {"FINISHED"}, "Metaball export should succeed"

        expected_file = temp_export_dir / "TestMetaBall.fbx"
        assert verify_file_exists(expected_file, "fbx"), (
            "Converted metaball FBX should exist"
        )

    def test_metaball_capsule_export(self, temp_export_dir, reset_settings):
        """Test exporting a capsule metaball."""
        bpy.ops.object.metaball_add(type="CAPSULE", location=(0, 0, 0))
        obj = bpy.context.active_object
        obj.name = "TestMetaCapsule"

        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"

        obj.select_set(True)
        result = bpy.ops.mesh.batch_export()
        assert result == {"FINISHED"}, "Metaball capsule export should succeed"

        expected_file = temp_export_dir / "TestMetaCapsule.fbx"
        assert verify_file_exists(expected_file, "fbx"), (
            "Metaball capsule FBX should exist"
        )

    def test_metaball_with_smoothing(self, temp_export_dir, reset_settings):
        """Test that metaballs get proper smooth shading applied.

        Metaballs are inherently smooth objects and should receive
        proper smoothing during export.
        """
        bpy.ops.object.metaball_add(type="BALL", location=(0, 0, 0))
        obj = bpy.context.active_object
        obj.name = "TestSmoothMetaBall"

        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"
        props.mesh_export_smoothing = "FACE"

        obj.select_set(True)
        result = bpy.ops.mesh.batch_export()
        assert result == {"FINISHED"}, "Smooth metaball export should succeed"

        expected_file = temp_export_dir / "TestSmoothMetaBall.fbx"
        assert verify_file_exists(expected_file, "fbx"), (
            "Smooth metaball FBX should exist"
        )


class TestMixedObjectTypes:
    """Tests for exporting mixed object type selections."""

    def test_mesh_and_curve_export(
        self, create_cube, create_curve, temp_export_dir, reset_settings
    ):
        """Test exporting both meshes and curves together."""
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"

        # Select both objects
        create_cube.select_set(True)
        create_curve.select_set(True)

        result = bpy.ops.mesh.batch_export()
        assert result == {"FINISHED"}, "Mixed mesh/curve export should succeed"

        # Verify both were exported
        cube_file = temp_export_dir / "TestCube.fbx"
        curve_file = temp_export_dir / "TestCurve.fbx"
        assert verify_file_exists(cube_file, "fbx"), "Cube FBX should exist"
        assert verify_file_exists(curve_file, "fbx"), "Curve FBX should exist"

    def test_all_object_types_export(
        self, create_cube, create_curve, temp_export_dir, reset_settings
    ):
        """Test exporting meshes, curves, and metaballs together."""
        # Add a metaball
        bpy.ops.object.metaball_add(type="BALL", location=(3, 0, 0))
        metaball = bpy.context.active_object
        metaball.name = "TestMetaBall"

        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"

        # Select all objects
        create_cube.select_set(True)
        create_curve.select_set(True)
        metaball.select_set(True)

        result = bpy.ops.mesh.batch_export()
        assert result == {"FINISHED"}, "Mixed object types export should succeed"

        # Verify all were exported
        cube_file = temp_export_dir / "TestCube.fbx"
        curve_file = temp_export_dir / "TestCurve.fbx"
        metaball_file = temp_export_dir / "TestMetaBall.fbx"

        assert verify_file_exists(cube_file, "fbx"), "Cube FBX should exist"
        assert verify_file_exists(curve_file, "fbx"), "Curve FBX should exist"
        assert verify_file_exists(metaball_file, "fbx"), "Metaball FBX should exist"


class TestObjectTransforms:
    """Tests for object transformations during export."""

    def test_zero_location_enabled(self, create_cube, temp_export_dir, reset_settings):
        """Test that zero location properly resets object origin."""
        # Move the cube away from origin
        create_cube.location = (5, 5, 5)

        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"
        props.mesh_export_zero_location = True

        create_cube.select_set(True)
        result = bpy.ops.mesh.batch_export()
        assert result == {"FINISHED"}, "Export with zero location should succeed"

        expected_file = temp_export_dir / "TestCube.fbx"
        assert verify_file_exists(expected_file, "fbx"), "Zeroed cube FBX should exist"

    def test_zero_location_disabled(self, create_cube, temp_export_dir, reset_settings):
        """Test exporting with original object location preserved."""
        # Move the cube away from origin
        create_cube.location = (5, 5, 5)

        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"
        props.mesh_export_zero_location = False

        create_cube.select_set(True)
        result = bpy.ops.mesh.batch_export()
        assert result == {"FINISHED"}, "Export without zero location should succeed"

        expected_file = temp_export_dir / "TestCube.fbx"
        assert verify_file_exists(expected_file, "fbx"), (
            "Non-zeroed cube FBX should exist"
        )

    def test_rotated_object_export(self, create_cube, temp_export_dir, reset_settings):
        """Test exporting a rotated object."""
        import math

        # Rotate the cube
        create_cube.rotation_euler = (
            math.radians(45),
            math.radians(30),
            math.radians(60),
        )

        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"

        create_cube.select_set(True)
        result = bpy.ops.mesh.batch_export()
        assert result == {"FINISHED"}, "Rotated object export should succeed"

        expected_file = temp_export_dir / "TestCube.fbx"
        assert verify_file_exists(expected_file, "fbx"), "Rotated cube FBX should exist"

    def test_scaled_object_export(self, create_cube, temp_export_dir, reset_settings):
        """Test exporting a scaled object."""
        # Scale the cube
        create_cube.scale = (2.0, 3.0, 1.5)

        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"

        create_cube.select_set(True)
        result = bpy.ops.mesh.batch_export()
        assert result == {"FINISHED"}, "Scaled object export should succeed"

        expected_file = temp_export_dir / "TestCube.fbx"
        assert verify_file_exists(expected_file, "fbx"), "Scaled cube FBX should exist"
